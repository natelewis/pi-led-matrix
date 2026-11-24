"""Shared font registry, caching, path-safe resolution, and built-in crisp 5x7 bitmap font.

Reusable by any built-in, custom, or AI-generated LED matrix effect.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover - stdlib-only web server environments
    Image = None  # type: ignore[assignment]
    ImageDraw = None  # type: ignore[assignment]
    ImageFont = None  # type: ignore[assignment]

REPO_ROOT = Path(__file__).resolve().parents[2]
FONTS_DIR = REPO_ROOT / "fonts"
UPLOADED_FONTS_DIR = FONTS_DIR / "_uploads"
FONT_EXTENSIONS = frozenset({".ttf", ".otf"})
BUILTIN_PIXEL_FONT_ID = "pixel_5x7"
DEFAULT_FONT_ID = "dosis.ttf"

_SAFE_FONT_NAME_RE = re.compile(r"^[a-zA-Z0-9._-]+$")


# Complete printable ASCII 5x7 bitmap glyphs (5 columns wide, 7 rows tall).
# Each entry is 7 strings of 5 chars ('#' = lit, '.' = off).
_PIXEL_5X7_GLYPHS: Dict[str, Tuple[str, ...]] = {
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    '"': (".#.#.", ".#.#.", ".#.#.", ".....", ".....", ".....", "....."),
    "#": (".#.#.", ".#.#.", "#####", ".#.#.", "#####", ".#.#.", ".#.#."),
    "$": ("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
    "%": ("##..#", "##.#.", "..#..", ".#...", ".#.##", "#..##", "....."),
    "&": (".##..", "#..#.", ".##..", ".#.#.", "#..#.", "#..#.", ".##.#"),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    "(": ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ")": (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    "*": (".....", "..#..", "#.#.#", ".###.", "#.#.#", "..#..", "....."),
    "+": (".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."),
    ",": (".....", ".....", ".....", ".....", "..##.", "..##.", ".#..."),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    "/": ("....#", "...#.", "...#.", "..#..", ".#...", ".#...", "#...."),
    "0": (".###.", "#..##", "#.#.#", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "..##.", ".#...", "#....", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    ":": (".....", "..#..", "..#..", ".....", "..#..", "..#..", "....."),
    ";": (".....", "..#..", "..#..", ".....", "..#..", "..#..", ".#..."),
    "<": ("...#.", "..#..", ".#...", "#....", ".#...", "..#..", "...#."),
    "=": (".....", ".....", "#####", ".....", "#####", ".....", "....."),
    ">": (".#...", "..#..", "...#.", "....#", "...#.", "..#..", ".#..."),
    "?": (".###.", "#...#", "....#", "..##.", "..#..", ".....", "..#.."),
    "@": (".###.", "#...#", "#.###", "#.#.#", "#.###", "#....", ".###."),
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".###.", "#...#", "#....", "#..##", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": (".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "[": (".###.", ".#...", ".#...", ".#...", ".#...", ".#...", ".###."),
    "\\": ("#....", ".#...", ".#...", "..#..", "...#.", "...#.", "....#"),
    "]": (".###.", "...#.", "...#.", "...#.", "...#.", "...#.", ".###."),
    "^": ("..#..", ".#.#.", "#...#", ".....", ".....", ".....", "....."),
    "_": (".....", ".....", ".....", ".....", ".....", ".....", "#####"),
    "`": (".#...", "..#..", ".....", ".....", ".....", ".....", "....."),
    "a": (".....", ".....", ".###.", "....#", ".####", "#...#", ".####"),
    "b": ("#....", "#....", "####.", "#...#", "#...#", "#...#", "####."),
    "c": (".....", ".....", ".###.", "#...#", "#....", "#...#", ".###."),
    "d": ("....#", "....#", ".####", "#...#", "#...#", "#...#", ".####"),
    "e": (".....", ".....", ".###.", "#...#", "#####", "#....", ".###."),
    "f": ("..##.", ".#..#", ".#...", "###..", ".#...", ".#...", ".#..."),
    "g": (".....", ".####", "#...#", "#...#", ".####", "....#", ".###."),
    "h": ("#....", "#....", "#.##.", "##..#", "#...#", "#...#", "#...#"),
    "i": ("..#..", ".....", ".##..", "..#..", "..#..", "..#..", ".###."),
    "j": ("...#.", ".....", "..##.", "...#.", "...#.", "#..#.", ".##.."),
    "k": ("#....", "#....", "#..#.", "#.#..", "##...", "#.#..", "#..#."),
    "l": (".##..", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "m": (".....", ".....", "##.#.", "#.#.#", "#.#.#", "#.#.#", "#...#"),
    "n": (".....", ".....", "####.", "#...#", "#...#", "#...#", "#...#"),
    "o": (".....", ".....", ".###.", "#...#", "#...#", "#...#", ".###."),
    "p": (".....", "####.", "#...#", "#...#", "####.", "#....", "#...."),
    "q": (".....", ".####", "#...#", "#...#", ".####", "....#", "....#"),
    "r": (".....", ".....", "#.##.", "##..#", "#....", "#....", "#...."),
    "s": (".....", ".....", ".####", "#....", ".###.", "....#", "####."),
    "t": (".#...", ".#...", "####.", ".#...", ".#...", ".#..#", "..##."),
    "u": (".....", ".....", "#...#", "#...#", "#...#", "#...#", ".####"),
    "v": (".....", ".....", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "w": (".....", ".....", "#...#", "#...#", "#.#.#", "#.#.#", ".#.#."),
    "x": (".....", ".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#"),
    "y": (".....", "#...#", "#...#", "#...#", ".####", "....#", ".###."),
    "z": (".....", ".....", "#####", "...#.", "..#..", ".#...", "#####"),
    "{": ("..##.", ".#...", ".#...", "#....", ".#...", ".#...", "..##."),
    "|": ("..#..", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "}": (".##..", "...#.", "...#.", "....#", "...#.", "...#.", ".##.."),
    "~": (".#.#.", "#.#.#", ".....", ".....", ".....", ".....", "....."),
    "•": (".....", ".....", "..#..", ".###.", "..#..", ".....", "....."),
    "·": (".....", ".....", ".....", "..#..", ".....", ".....", "....."),
    "—": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    "–": (".....", ".....", ".....", ".###.", ".....", ".....", "....."),
    "°": (".##..", "#..#.", ".##..", ".....", ".....", ".....", "....."),
    "♥": (".....", ".#.#.", "#####", "#####", ".###.", "..#..", "....."),
    "★": ("..#..", "..#..", "#####", ".###.", ".#.#.", "#...#", "....."),
}


class Pixel5x7Font:
    """Crisp integer-scaled 5x7 bitmap font with a Pillow-compatible measurement API."""

    def __init__(self, size: int = 7) -> None:
        self.size = max(5, int(round(size)))
        self.scale = max(1, int(round(self.size / 7.0)))
        self.glyph_w = 5 * self.scale
        self.glyph_h = 7 * self.scale
        self.char_gap = max(1, self.scale)

    def getmetrics(self) -> Tuple[int, int]:
        return (self.glyph_h, 0)

    def measure(self, text: str, letter_spacing: int = 0) -> Tuple[int, int]:
        if not text:
            return (0, self.glyph_h)
        step = self.glyph_w + self.char_gap + int(letter_spacing)
        width = max(0, len(text) * step - (self.char_gap + int(letter_spacing)))
        return (width, self.glyph_h)

    def getbbox(self, text: str) -> Tuple[int, int, int, int]:
        w, h = self.measure(text)
        return (0, 0, w, h)

    def render_mask(self, text: str, letter_spacing: int = 0) -> Image.Image:
        w, h = self.measure(text, letter_spacing=letter_spacing)
        if w <= 0 or h <= 0:
            return Image.new("L", (1, max(1, self.glyph_h)), 0)
        mask = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask)
        cursor_x = 0
        s = self.scale
        gap = self.char_gap + int(letter_spacing)
        for ch in text:
            pattern = _PIXEL_5X7_GLYPHS.get(ch)
            if pattern is None:
                pattern = _PIXEL_5X7_GLYPHS.get(ch.upper(), _PIXEL_5X7_GLYPHS["?"])
            for row_idx, row in enumerate(pattern):
                for col_idx, cell in enumerate(row):
                    if cell == "#":
                        x0 = cursor_x + col_idx * s
                        y0 = row_idx * s
                        if s == 1:
                            draw.point((x0, y0), fill=255)
                        else:
                            draw.rectangle((x0, y0, x0 + s - 1, y0 + s - 1), fill=255)
            cursor_x += self.glyph_w + gap
        return mask


def is_safe_font_ref(font_ref: Any) -> bool:
    """Validate that a font identifier is safe (no directory traversal)."""
    if not isinstance(font_ref, str):
        return False
    cleaned = font_ref.strip()
    if not cleaned:
        return False
    if cleaned == BUILTIN_PIXEL_FONT_ID:
        return True
    if cleaned.startswith("/") or "\\" in cleaned:
        return False
    parts = Path(cleaned).parts
    if ".." in parts:
        return False
    if len(parts) == 1:
        name = parts[0]
    elif len(parts) == 2 and parts[0] == "_uploads":
        name = parts[1]
    else:
        return False
    if name.startswith(".") or not _SAFE_FONT_NAME_RE.match(name):
        return False
    return Path(name).suffix.lower() in FONT_EXTENSIONS


def resolve_font_path(font_ref: str, repo_root: Path = REPO_ROOT) -> Optional[Path]:
    """Safely resolve a font reference ('dosis.ttf' or '_uploads/my.ttf') inside fonts/."""
    if not is_safe_font_ref(font_ref) or font_ref == BUILTIN_PIXEL_FONT_ID:
        return None
    fonts_root = (repo_root / "fonts").resolve()
    candidate = (fonts_root / font_ref.strip()).resolve()
    try:
        candidate.relative_to(fonts_root)
    except ValueError:
        return None
    if candidate.is_file() and candidate.suffix.lower() in FONT_EXTENSIONS:
        return candidate
    return None


def _humanize_font_name(filename: str) -> str:
    stem = Path(filename).stem
    return " ".join(part.capitalize() for part in re.split(r"[_\-\s]+", stem) if part)


def _read_manifest(repo_root: Path = REPO_ROOT) -> Dict[str, Dict[str, Any]]:
    manifest_path = repo_root / "fonts" / "manifest.json"
    if not manifest_path.is_file():
        return {}
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    entries = data.get("fonts") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        return {}
    by_id: Dict[str, Dict[str, Any]] = {}
    for entry in entries:
        if isinstance(entry, dict) and isinstance(entry.get("id"), str):
            by_id[entry["id"]] = entry
    return by_id


def discover_font_catalog(repo_root: Path = REPO_ROOT) -> List[Dict[str, Any]]:
    """Return rich metadata for all built-in, bundled, and user-uploaded fonts."""
    fonts_root = repo_root / "fonts"
    manifest = _read_manifest(repo_root)
    catalog: List[Dict[str, Any]] = []
    seen: set[str] = set()

    # 1. Include entries in manifest order (built-in pixel_5x7 + bundled TTFs)
    for font_id, meta in manifest.items():
        is_builtin = bool(meta.get("builtin")) or font_id == BUILTIN_PIXEL_FONT_ID
        if not is_builtin:
            resolved = resolve_font_path(str(meta.get("file") or font_id), repo_root)
            if resolved is None:
                continue
            size_bytes = resolved.stat().st_size
            file_ref = str(meta.get("file") or font_id)
        else:
            size_bytes = 0
            file_ref = BUILTIN_PIXEL_FONT_ID

        seen.add(font_id)
        catalog.append(
            {
                "id": font_id,
                "file": file_ref,
                "name": str(meta.get("name") or _humanize_font_name(font_id)),
                "category": str(meta.get("category") or "sans"),
                "description": str(meta.get("description") or ""),
                "minHeight": int(meta.get("minHeight") or 10),
                "recommendedMinSize": int(meta.get("recommendedMinSize") or 12),
                "crispDefault": bool(meta.get("crispDefault", False)),
                "variation": meta.get("variation"),
                "cssWeight": int(meta.get("cssWeight") or 400),
                "builtin": is_builtin,
                "uploaded": False,
                "license": str(meta.get("license") or ""),
                "sizeBytes": size_bytes,
            }
        )

    # Ensure built-in pixel_5x7 is always available even if manifest is missing
    if BUILTIN_PIXEL_FONT_ID not in seen:
        seen.add(BUILTIN_PIXEL_FONT_ID)
        catalog.insert(
            0,
            {
                "id": BUILTIN_PIXEL_FONT_ID,
                "file": BUILTIN_PIXEL_FONT_ID,
                "name": "Pixel 5×7 (Built-in)",
                "category": "pixel",
                "description": "Razor-sharp 5×7 bitmap font for tiny displays.",
                "minHeight": 7,
                "recommendedMinSize": 7,
                "crispDefault": True,
                "variation": None,
                "cssWeight": 400,
                "builtin": True,
                "uploaded": False,
                "license": "Built-in",
                "sizeBytes": 0,
            },
        )

    # 2. Any extra .ttf/.otf dropped directly into fonts/
    if fonts_root.is_dir():
        for entry in sorted(fonts_root.iterdir(), key=lambda p: p.name.lower()):
            if (
                not entry.is_file()
                or entry.name.startswith(".")
                or entry.suffix.lower() not in FONT_EXTENSIONS
                or entry.name in seen
            ):
                continue
            seen.add(entry.name)
            catalog.append(
                {
                    "id": entry.name,
                    "file": entry.name,
                    "name": _humanize_font_name(entry.name),
                    "category": "custom",
                    "description": "Custom bundled font file.",
                    "minHeight": 10,
                    "recommendedMinSize": 12,
                    "crispDefault": False,
                    "variation": None,
                    "cssWeight": 400,
                    "builtin": False,
                    "uploaded": False,
                    "license": "",
                    "sizeBytes": entry.stat().st_size,
                }
            )

        # 3. User-uploaded fonts under fonts/_uploads/
        uploads_dir = fonts_root / "_uploads"
        if uploads_dir.is_dir():
            upload_entries: List[Tuple[float, Path]] = []
            for entry in uploads_dir.iterdir():
                if (
                    not entry.is_file()
                    or entry.name.startswith(".")
                    or entry.suffix.lower() not in FONT_EXTENSIONS
                ):
                    continue
                try:
                    upload_entries.append((entry.stat().st_mtime, entry))
                except OSError:
                    continue
            upload_entries.sort(key=lambda item: item[0], reverse=True)
            for _, entry in upload_entries:
                rel = f"_uploads/{entry.name}"
                if rel in seen:
                    continue
                seen.add(rel)
                catalog.append(
                    {
                        "id": rel,
                        "file": rel,
                        "name": _humanize_font_name(entry.name),
                        "category": "uploaded",
                        "description": "Uploaded custom font.",
                        "minHeight": 10,
                        "recommendedMinSize": 12,
                        "crispDefault": False,
                        "variation": None,
                        "cssWeight": 400,
                        "builtin": False,
                        "uploaded": True,
                        "license": "Custom",
                        "sizeBytes": entry.stat().st_size,
                    }
                )

    return catalog


def get_font_meta(font_ref: str, repo_root: Path = REPO_ROOT) -> Dict[str, Any]:
    """Look up font metadata by id/filename with graceful fallback."""
    cleaned = (font_ref or DEFAULT_FONT_ID).strip()
    catalog = discover_font_catalog(repo_root)
    for item in catalog:
        if item["id"] == cleaned or item["file"] == cleaned:
            return item
    return {
        "id": cleaned or DEFAULT_FONT_ID,
        "file": cleaned or DEFAULT_FONT_ID,
        "name": _humanize_font_name(cleaned or DEFAULT_FONT_ID),
        "category": "sans",
        "minHeight": 10,
        "recommendedMinSize": 12,
        "crispDefault": False,
        "variation": None,
        "cssWeight": 400,
        "builtin": cleaned == BUILTIN_PIXEL_FONT_ID,
        "uploaded": cleaned.startswith("_uploads/"),
    }


@lru_cache(maxsize=256)
def _load_cached_truetype(
    font_path_str: str, size: int, variation: Optional[str]
) -> Any:
    if ImageFont is None:
        raise RuntimeError("Pillow is required to load TrueType/OpenType fonts.")
    font = ImageFont.truetype(font_path_str, max(5, int(size)))
    if variation:
        try:
            font.set_variation_by_name(variation)
        except (OSError, ValueError, AttributeError):
            pass
    return font


def load_font(
    font_ref: str = DEFAULT_FONT_ID,
    size: int = 16,
    *,
    repo_root: Path = REPO_ROOT,
) -> Any:
    """Load a cached Pillow FreeTypeFont or built-in Pixel5x7Font safely with fallback."""
    clamped_size = max(5, min(256, int(round(size))))
    cleaned = (font_ref or DEFAULT_FONT_ID).strip()

    if cleaned == BUILTIN_PIXEL_FONT_ID:
        return Pixel5x7Font(clamped_size)

    meta = get_font_meta(cleaned, repo_root=repo_root)
    variation = meta.get("variation") if isinstance(meta.get("variation"), str) else None

    resolved = resolve_font_path(cleaned, repo_root=repo_root)
    if resolved is not None:
        try:
            return _load_cached_truetype(str(resolved), clamped_size, variation)
        except OSError:
            pass

    # Fallback to dosis.ttf if present, then Pixel5x7Font
    fallback_path = resolve_font_path(DEFAULT_FONT_ID, repo_root=repo_root)
    if fallback_path is not None:
        try:
            return _load_cached_truetype(str(fallback_path), clamped_size, None)
        except OSError:
            pass

    return Pixel5x7Font(clamped_size)


def clear_font_cache() -> None:
    """Clear the LRU font cache (useful after font uploads/deletions)."""
    _load_cached_truetype.cache_clear()
