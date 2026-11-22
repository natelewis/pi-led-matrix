"""Image upload, RGBA PNG encoding, and safe asset management for the image effect."""

from __future__ import annotations

import base64
import binascii
import json
import os
import re
import shutil
import struct
import subprocess
import tempfile
import zlib
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Tuple


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
UPLOADS_DIRNAME = "_uploads"
MAX_DIMENSION = 1024
MAX_VIDEO_UPLOAD_BYTES = 250 * 1024 * 1024  # 250 MiB


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)


def encode_rgba_png(width: int, height: int, rgba_bytes: bytes) -> bytes:
    """Encode raw 8-bit RGBA bytes into a spec-compliant 32-bit RGBA PNG (color_type=6).

    Guaranteed 4-channel RGBA output so `r, g, b, _ = image.split()` in
    `src/effects/image/effect.py` always succeeds.
    """
    expected = width * height * 4
    if len(rgba_bytes) != expected:
        raise ValueError(
            f"Expected {expected} RGBA bytes for {width}x{height}, got {len(rgba_bytes)}."
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)

    # Prepend filter byte 0 (None) to each scanline
    stride = width * 4
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        start = y * stride
        rows.extend(rgba_bytes[start : start + stride])

    compressed = zlib.compress(bytes(rows), level=6)
    return (
        PNG_SIGNATURE
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", compressed)
        + _png_chunk(b"IEND", b"")
    )


def inspect_png_header(data: bytes) -> Optional[Tuple[int, int, int]]:
    """Return (width, height, color_type) if bytes start with a valid PNG IHDR."""
    if len(data) < 26 or not data.startswith(PNG_SIGNATURE):
        return None
    chunk_len, chunk_type = struct.unpack(">I4s", data[8:16])
    if chunk_type != b"IHDR" or chunk_len != 13:
        return None
    width, height, _bit_depth, color_type = struct.unpack(">IIBB", data[16:26])
    return width, height, color_type


def sanitize_slug(filename: str) -> str:
    stem = Path(filename).stem.lower()
    # Strip any existing trailing _WxH suffix so re-uploads don't stack suffixes
    stem = re.sub(r"_\d+x\d+$", "", stem)
    slug = re.sub(r"[^a-z0-9_-]+", "_", stem).strip("_")
    return slug[:60] or "image"


class ImageMediaStore:
    """Manages images in src/effects/image/ and uploads in src/effects/image/_uploads/."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self.image_effect_dir = (self.repo_root / "src" / "effects" / "image").resolve()
        self.uploads_dir = (self.image_effect_dir / UPLOADS_DIRNAME).resolve()

    def list_images(self) -> List[Dict[str, Any]]:
        if not self.image_effect_dir.is_dir():
            return []

        items: List[Dict[str, Any]] = []

        def collect(directory: Path, prefix: str, uploaded: bool) -> None:
            if not directory.is_dir():
                return
            for entry in sorted(directory.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
                if not entry.is_file() or entry.suffix.lower() not in IMAGE_EXTENSIONS:
                    continue
                rel_name = f"{prefix}{entry.name}"
                stat = entry.stat()
                dims = None
                if entry.suffix.lower() == ".png":
                    try:
                        with entry.open("rb") as fh:
                            header = inspect_png_header(fh.read(32))
                        if header:
                            dims = {"width": header[0], "height": header[1]}
                    except OSError:
                        pass
                items.append(
                    {
                        "file": rel_name,
                        "name": entry.name,
                        "uploaded": uploaded,
                        "sizeBytes": stat.st_size,
                        "width": dims["width"] if dims else None,
                        "height": dims["height"] if dims else None,
                    }
                )

        collect(self.uploads_dir, f"{UPLOADS_DIRNAME}/", uploaded=True)
        collect(self.image_effect_dir, "", uploaded=False)
        return items

    def resolve_image_path(self, rel_file: str, *, uploads_only: bool = False) -> Path:
        cleaned = rel_file.strip().lstrip("/")
        if not cleaned or ".." in Path(cleaned).parts:
            raise ValueError("Invalid image path.")
        candidate = (self.image_effect_dir / cleaned).resolve()
        base_dir = self.uploads_dir if uploads_only else self.image_effect_dir
        try:
            candidate.relative_to(base_dir)
        except ValueError as exc:
            raise ValueError("Image path outside permitted directory.") from exc
        if candidate.suffix.lower() not in IMAGE_EXTENSIONS:
            raise ValueError("Unsupported image file extension.")
        return candidate

    def save_uploaded_rgba(
        self,
        *,
        filename: str,
        width: int,
        height: int,
        rgba_base64: str,
    ) -> Dict[str, Any]:
        if isinstance(width, bool) or not isinstance(width, int) or not (1 <= width <= MAX_DIMENSION):
            raise ValueError(f"width must be an integer between 1 and {MAX_DIMENSION}.")
        if isinstance(height, bool) or not isinstance(height, int) or not (1 <= height <= MAX_DIMENSION):
            raise ValueError(f"height must be an integer between 1 and {MAX_DIMENSION}.")

        try:
            rgba_bytes = base64.b64decode(rgba_base64, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ValueError("Invalid base64 RGBA image data.") from exc

        png_bytes = encode_rgba_png(width, height, rgba_bytes)

        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        slug = sanitize_slug(filename)
        base_name = f"{slug}_{width}x{height}.png"
        target = self.uploads_dir / base_name

        # Avoid clobbering a different file if same name already exists
        counter = 2
        while target.exists():
            target = self.uploads_dir / f"{slug}_{counter}_{width}x{height}.png"
            counter += 1

        tmp_path = target.with_suffix(".png.tmp")
        tmp_path.write_bytes(png_bytes)
        os.replace(tmp_path, target)

        rel_file = f"{UPLOADS_DIRNAME}/{target.name}"
        return {
            "file": rel_file,
            "name": target.name,
            "uploaded": True,
            "sizeBytes": len(png_bytes),
            "width": width,
            "height": height,
        }

    def delete_upload(self, rel_file: str) -> bool:
        target = self.resolve_image_path(rel_file, uploads_only=True)
        if not target.is_file():
            return False
        target.unlink()
        return True


def probe_video_metadata(video_path: Path) -> Dict[str, Optional[float]]:
    """Use ffprobe (if installed) to inspect width, height, and duration."""
    if not shutil.which("ffprobe"):
        return {"width": None, "height": None, "duration": None}
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height:format=duration",
                "-of",
                "json",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode != 0:
            return {"width": None, "height": None, "duration": None}
        payload = json.loads(result.stdout or "{}")
        streams = payload.get("streams") or []
        stream0 = streams[0] if streams else {}
        fmt = payload.get("format") or {}
        width = stream0.get("width")
        height = stream0.get("height")
        raw_dur = fmt.get("duration")
        duration = round(float(raw_dur), 2) if raw_dur is not None else None
        return {
            "width": int(width) if width is not None else None,
            "height": int(height) if height is not None else None,
            "duration": duration,
        }
    except (OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError):
        return {"width": None, "height": None, "duration": None}


class VideoMediaStore:
    """Manages videos in src/effects/video/ and uploads in src/effects/video/_uploads/."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self.video_effect_dir = (self.repo_root / "src" / "effects" / "video").resolve()
        self.uploads_dir = (self.video_effect_dir / UPLOADS_DIRNAME).resolve()

    def list_videos(self) -> List[Dict[str, Any]]:
        if not self.video_effect_dir.is_dir():
            return []

        items: List[Dict[str, Any]] = []

        def collect(directory: Path, prefix: str, uploaded: bool) -> None:
            if not directory.is_dir():
                return
            for entry in sorted(
                directory.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True
            ):
                if not entry.is_file() or entry.suffix.lower() not in VIDEO_EXTENSIONS:
                    continue
                stat = entry.stat()
                meta = probe_video_metadata(entry)
                items.append(
                    {
                        "file": f"{prefix}{entry.name}",
                        "name": entry.name,
                        "uploaded": uploaded,
                        "sizeBytes": stat.st_size,
                        "width": meta["width"],
                        "height": meta["height"],
                        "duration": meta["duration"],
                    }
                )

        collect(self.uploads_dir, f"{UPLOADS_DIRNAME}/", uploaded=True)
        collect(self.video_effect_dir, "", uploaded=False)
        return items

    def resolve_video_path(self, rel_file: str, *, uploads_only: bool = False) -> Path:
        cleaned = rel_file.strip().lstrip("/")
        if not cleaned or ".." in Path(cleaned).parts:
            raise ValueError("Invalid video path.")
        candidate = (self.video_effect_dir / cleaned).resolve()
        base_dir = self.uploads_dir if uploads_only else self.video_effect_dir
        try:
            candidate.relative_to(base_dir)
        except ValueError as exc:
            raise ValueError("Video path outside permitted directory.") from exc
        if candidate.suffix.lower() not in VIDEO_EXTENSIONS:
            raise ValueError("Unsupported video file extension.")
        return candidate

    def save_uploaded_stream(
        self,
        stream: BinaryIO,
        content_length: int,
        *,
        filename: str,
        width: int,
        height: int,
        fit_mode: str = "crop",
        crop_rect: Optional[Tuple[int, int, int, int]] = None,
        start_sec: Optional[float] = None,
        end_sec: Optional[float] = None,
    ) -> Dict[str, Any]:
        if not shutil.which("ffmpeg"):
            raise RuntimeError(
                "ffmpeg is required to resize uploaded videos. Install ffmpeg and try again."
            )
        if not (1 <= width <= MAX_DIMENSION) or not (1 <= height <= MAX_DIMENSION):
            raise ValueError(f"Dimensions must be between 1 and {MAX_DIMENSION}.")
        if content_length <= 0 or content_length > MAX_VIDEO_UPLOAD_BYTES:
            raise ValueError("Video file is empty or exceeds the 250 MiB upload limit.")
        if fit_mode not in {"crop", "contain", "stretch"}:
            raise ValueError("fitMode must be one of: crop, contain, stretch.")

        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        slug = sanitize_slug(filename)
        target = self.uploads_dir / f"{slug}_{width}x{height}.mp4"
        counter = 2
        while target.exists():
            target = self.uploads_dir / f"{slug}_{counter}_{width}x{height}.mp4"
            counter += 1

        src_ext = Path(filename).suffix.lower()
        if src_ext not in VIDEO_EXTENSIONS:
            src_ext = ".mp4"

        tmp_input_fd, tmp_input_str = tempfile.mkstemp(
            prefix="led_vid_in_", suffix=src_ext
        )
        tmp_input = Path(tmp_input_str)
        tmp_output = target.with_name(f".{target.stem}.tmp.mp4")

        try:
            # Stream request body directly to disk in 64 KiB chunks
            remaining = content_length
            with os.fdopen(tmp_input_fd, "wb") as out_f:
                while remaining > 0:
                    chunk = stream.read(min(65536, remaining))
                    if not chunk:
                        break
                    out_f.write(chunk)
                    remaining -= len(chunk)

            if fit_mode == "crop":
                if crop_rect is not None:
                    cx, cy, cw, ch = crop_rect
                    if cw <= 0 or ch <= 0 or cx < 0 or cy < 0:
                        raise ValueError("Invalid crop rectangle.")
                    vf = f"crop={cw}:{ch}:{cx}:{cy},scale={width}:{height}:flags=lanczos"
                else:
                    vf = (
                        f"scale={width}:{height}:force_original_aspect_ratio=increase:flags=lanczos,"
                        f"crop={width}:{height}"
                    )
            elif fit_mode == "contain":
                vf = (
                    f"scale={width}:{height}:force_original_aspect_ratio=decrease:flags=lanczos,"
                    f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black"
                )
            else:
                vf = f"scale={width}:{height}:flags=lanczos"

            pix_fmt = "yuv420p" if (width % 2 == 0 and height % 2 == 0) else "yuv444p"

            cmd: List[str] = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
            if start_sec is not None and start_sec > 0:
                cmd.extend(["-ss", f"{start_sec:.3f}"])
            cmd.extend(["-i", str(tmp_input)])
            if end_sec is not None and end_sec > 0:
                duration = end_sec - (start_sec or 0.0)
                if duration > 0.1:
                    cmd.extend(["-t", f"{duration:.3f}"])
            cmd.extend(
                [
                    "-vf",
                    vf,
                    "-an",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "fast",
                    "-crf",
                    "23",
                    "-pix_fmt",
                    pix_fmt,
                    "-movflags",
                    "+faststart",
                    str(tmp_output),
                ]
            )

            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
            if proc.returncode != 0 or not tmp_output.is_file():
                err_msg = (proc.stderr or "").strip() or "ffmpeg failed to process the video."
                raise RuntimeError(err_msg)

            os.replace(tmp_output, target)
            meta = probe_video_metadata(target)
            stat = target.stat()
            return {
                "file": f"{UPLOADS_DIRNAME}/{target.name}",
                "name": target.name,
                "uploaded": True,
                "sizeBytes": stat.st_size,
                "width": meta["width"] or width,
                "height": meta["height"] or height,
                "duration": meta["duration"],
            }
        finally:
            tmp_input.unlink(missing_ok=True)
            tmp_output.unlink(missing_ok=True)

    def delete_upload(self, rel_file: str) -> bool:
        target = self.resolve_video_path(rel_file, uploads_only=True)
        if not target.is_file():
            return False
        target.unlink()
        return True
