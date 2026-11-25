"""Font catalog, safe file resolution, and custom .ttf/.otf upload management."""

from __future__ import annotations

import base64
import io
import os
import re
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any, Dict, List

try:
    from PIL import ImageFont
except ImportError:  # pragma: no cover - stdlib-only server environments
    ImageFont = None  # type: ignore[assignment]

MAX_FONT_BYTES = 5 * 1024 * 1024  # 5 MiB
ALLOWED_FONT_EXTS = {".ttf", ".otf"}
_VALID_SFNT_MAGICS = (b"\x00\x01\x00\x00", b"OTTO", b"true", b"typ1", b"ttcf")
_SAFE_STEM_RE = re.compile(r"[^a-zA-Z0-9_-]+")


def _ensure_src_on_path(repo_root: Path) -> None:
    for candidate in (repo_root / "src", Path(__file__).resolve().parents[2] / "src"):
        resolved = str(candidate.resolve())
        if candidate.is_dir() and resolved not in sys.path:
            sys.path.insert(0, resolved)


class FontStore:
    """Manages bundled & uploaded LED matrix fonts under ``fonts/``."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self.fonts_dir = self.repo_root / "fonts"
        self.uploads_dir = self.fonts_dir / "_uploads"
        self._lock = threading.Lock()

    def list_fonts(self) -> List[Dict[str, Any]]:
        _ensure_src_on_path(self.repo_root)
        from lib import led_fonts  # pylint: disable=import-outside-toplevel

        return led_fonts.discover_font_catalog(self.repo_root)

    def resolve_font_path(self, font_ref: str) -> Path:
        _ensure_src_on_path(self.repo_root)
        from lib import led_fonts  # pylint: disable=import-outside-toplevel

        if not led_fonts.is_safe_font_ref(font_ref) or font_ref == led_fonts.BUILTIN_PIXEL_FONT_ID:
            raise ValueError("Invalid font filename.")
        resolved = led_fonts.resolve_font_path(font_ref, repo_root=self.repo_root)
        if resolved is None:
            raise FileNotFoundError(f"Font '{font_ref}' not found.")
        return resolved

    def save_uploaded_font(self, filename: str, data_base64: str) -> Dict[str, Any]:
        _ensure_src_on_path(self.repo_root)
        from lib import led_fonts  # pylint: disable=import-outside-toplevel

        raw_name = Path(str(filename or "custom.ttf")).name
        ext = Path(raw_name).suffix.lower()
        if ext not in ALLOWED_FONT_EXTS:
            raise ValueError("Only .ttf and .otf font files are supported.")

        try:
            raw_bytes = base64.b64decode(data_base64, validate=True)
        except Exception as exc:
            raise ValueError("Invalid base64 font payload.") from exc

        if not raw_bytes:
            raise ValueError("Font file is empty.")
        if len(raw_bytes) > MAX_FONT_BYTES:
            raise ValueError("Font file exceeds 5 MiB limit.")
        if len(raw_bytes) < 12 or raw_bytes[:4] not in _VALID_SFNT_MAGICS:
            raise ValueError("File does not have a valid TrueType/OpenType header.")

        # Verify Pillow/FreeType can genuinely parse this font when Pillow is available
        if ImageFont is not None:
            try:
                ImageFont.truetype(io.BytesIO(raw_bytes), 16)
            except OSError as exc:
                raise ValueError(f"Unreadable or corrupted font file: {exc}") from exc

        stem = _SAFE_STEM_RE.sub("_", Path(raw_name).stem).strip("_-")[:48] or "custom_font"
        with self._lock:
            self.uploads_dir.mkdir(parents=True, exist_ok=True)
            candidate = self.uploads_dir / f"{stem}{ext}"
            counter = 2
            while candidate.exists():
                candidate = self.uploads_dir / f"{stem}_{counter}{ext}"
                counter += 1

            fd, tmp_name = tempfile.mkstemp(
                dir=str(self.uploads_dir), prefix=".font.", suffix=ext
            )
            tmp_path = Path(tmp_name)
            try:
                with os.fdopen(fd, "wb") as handle:
                    handle.write(raw_bytes)
                os.replace(tmp_path, candidate)
            except Exception:
                tmp_path.unlink(missing_ok=True)
                raise

        led_fonts.clear_font_cache()
        rel_id = f"_uploads/{candidate.name}"
        catalog = self.list_fonts()
        saved = next((f for f in catalog if f["id"] == rel_id), None)
        return saved or led_fonts.get_font_meta(rel_id, repo_root=self.repo_root)

    def delete_uploaded_font(self, font_ref: str) -> bool:
        _ensure_src_on_path(self.repo_root)
        from lib import led_fonts  # pylint: disable=import-outside-toplevel

        cleaned = str(font_ref or "").strip()
        if not cleaned.startswith("_uploads/") or not led_fonts.is_safe_font_ref(cleaned):
            raise ValueError("Only user-uploaded fonts can be deleted.")
        target = led_fonts.resolve_font_path(cleaned, repo_root=self.repo_root)
        if target is None or not target.is_file():
            return False
        uploads_root = self.uploads_dir.resolve()
        try:
            target.relative_to(uploads_root)
        except ValueError as exc:
            raise ValueError("Invalid uploaded font path.") from exc
        target.unlink()
        led_fonts.clear_font_cache()
        return True
