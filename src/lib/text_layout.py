"""Reusable smart typography, optical layout, visual effects, and screen-intelligence engine.

Designed as a shared library in ``src/lib/`` so that ``marquee``, ``rgb_text``,
``announcement``, and any community or AI-generated effect (clocks, scoreboards,
tickers, specialty marquees) can share exact FreeType optical centering,
auto-sizing, crisp pixel rendering, visual effects, and screen-size advisories.
"""

from __future__ import annotations

import colorsys
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from lib.led_color import parse_color
from lib.led_fonts import (
    BUILTIN_PIXEL_FONT_ID,
    DEFAULT_FONT_ID,
    REPO_ROOT,
    Pixel5x7Font,
    get_font_meta,
    load_font,
)

_COUNTDOWN_RE = re.compile(r"\{countdown:([^}]+)\}", re.IGNORECASE)


def classify_screen(width: int, height: int) -> Dict[str, Any]:
    """Classify an LED matrix into a capability tier with typography heuristics."""
    w = max(8, int(width))
    h = max(8, int(height))

    if h <= 16 or w <= 32:
        tier = "micro"
        max_comfortable_lines = 1 if h < 15 else 2
        recommended_min_font = 7
        supports_glow = False
        supports_thick_outline = False
        default_padding = 0 if h <= 12 else 1
    elif h <= 36:
        tier = "compact"
        max_comfortable_lines = max(1, h // 10)
        recommended_min_font = 8
        supports_glow = h >= 28
        supports_thick_outline = False
        default_padding = 1
    elif h <= 80:
        tier = "standard"
        max_comfortable_lines = max(2, h // 13)
        recommended_min_font = 10
        supports_glow = True
        supports_thick_outline = True
        default_padding = 2
    else:
        tier = "large"
        max_comfortable_lines = max(3, h // 14)
        recommended_min_font = 12
        supports_glow = True
        supports_thick_outline = True
        default_padding = 3

    return {
        "tier": tier,
        "width": w,
        "height": h,
        "max_comfortable_lines": max_comfortable_lines,
        "recommended_min_font": recommended_min_font,
        "supports_glow": supports_glow,
        "supports_thick_outline": supports_thick_outline,
        "default_padding": default_padding,
    }


def expand_dynamic_tokens(text: str, now: Optional[datetime] = None) -> str:
    """Expand live tokens like ``{time}``, ``{time24}``, ``{date}``, ``{day}``, ``{countdown:...}``."""
    if not text or "{" not in text:
        return text

    dt = now or datetime.now()
    hour12 = dt.hour % 12 or 12
    ampm = "AM" if dt.hour < 12 else "PM"
    replacements = {
        "{time}": f"{hour12}:{dt.minute:02d} {ampm}",
        "{time24}": f"{dt.hour:02d}:{dt.minute:02d}",
        "{seconds}": f"{hour12}:{dt.minute:02d}:{dt.second:02d} {ampm}",
        "{date}": f"{dt.strftime('%b')} {dt.day}",
        "{day}": dt.strftime("%A"),
        "{year}": str(dt.year),
    }

    result = text
    for token, value in replacements.items():
        if token in result:
            result = result.replace(token, value)

    def _replace_countdown(match: re.Match[str]) -> str:
        raw = match.group(1).strip()
        target = None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                target = datetime.strptime(raw, fmt)
                break
            except ValueError:
                continue
        if target is None:
            return raw
        delta = int((target - dt).total_seconds())
        if delta <= 0:
            return "00:00:00"
        days, rem = divmod(delta, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, seconds = divmod(rem, 60)
        if days > 0:
            return f"{days}d {hours:02d}h {minutes:02d}m"
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    if "{countdown:" in result.lower():
        result = _COUNTDOWN_RE.sub(_replace_countdown, result)

    return result


def apply_text_transform(text: str, transform: str = "none") -> str:
    mode = (transform or "none").strip().lower()
    if mode == "uppercase":
        return text.upper()
    if mode == "lowercase":
        return text.lower()
    if mode == "title":
        return text.title()
    return text


def should_render_crisp(
    rendering: str,
    font_ref: str,
    font_size: int,
    screen_height: int,
    repo_root: Path = REPO_ROOT,
) -> bool:
    """Decide whether to threshold glyph alpha for razor-sharp pixel LED legibility."""
    mode = (rendering or "auto").strip().lower()
    if mode == "crisp":
        return True
    if mode == "smooth":
        return False
    if font_ref == BUILTIN_PIXEL_FONT_ID:
        return True
    meta = get_font_meta(font_ref, repo_root=repo_root)
    if meta.get("crispDefault"):
        return True
    if screen_height <= 16:
        return True
    if font_size <= 10:
        return True
    return False


def _measure_single_truetype_line(
    text: str, font: Any, letter_spacing: int = 0
) -> Tuple[int, int, int, int]:
    """Return ``(width, height, left_bearing, top_bearing)`` for a single line."""
    if not text:
        ascent, descent = font.getmetrics()
        return (0, max(1, ascent + descent), 0, 0)

    if isinstance(font, Pixel5x7Font):
        w, h = font.measure(text, letter_spacing=letter_spacing)
        return (w, h, 0, 0)

    if letter_spacing == 0:
        bbox = font.getbbox(text)
        return (
            max(0, bbox[2] - bbox[0]),
            max(1, bbox[3] - bbox[1]),
            bbox[0],
            bbox[1],
        )

    # Custom tracking: measure glyph-by-glyph with FreeType advance width
    cursor_x = 0.0
    min_x = 10**9
    max_x = -(10**9)
    min_y = 10**9
    max_y = -(10**9)
    for idx, ch in enumerate(text):
        cbbox = font.getbbox(ch)
        if cbbox is not None and cbbox[2] > cbbox[0]:
            min_x = min(min_x, int(round(cursor_x)) + cbbox[0])
            max_x = max(max_x, int(round(cursor_x)) + cbbox[2])
            min_y = min(min_y, cbbox[1])
            max_y = max(max_y, cbbox[3])
        adv = font.getlength(ch) if hasattr(font, "getlength") else (cbbox[2] - cbbox[0])
        cursor_x += adv
        if idx < len(text) - 1:
            cursor_x += letter_spacing

    if min_x > max_x:
        return (max(0, int(round(cursor_x))), max(1, font.size), 0, 0)
    return (
        max(1, max_x - min_x),
        max(1, max_y - min_y),
        min_x,
        min_y,
    )


def measure_text_line(
    text: str,
    font_ref: str,
    font_size: int,
    *,
    letter_spacing: int = 0,
    repo_root: Path = REPO_ROOT,
) -> Dict[str, int]:
    """Measure exact pixel ink width, ink height, ascent/descent, and bearings."""
    font = load_font(font_ref, font_size, repo_root=repo_root)
    ink_w, ink_h, bx, by = _measure_single_truetype_line(
        text, font, letter_spacing=letter_spacing
    )
    ascent, descent = font.getmetrics()
    # Reference cap height using 'Hg' so vertical spacing stays steady even for lowercase lines
    _, ref_h, _, ref_by = _measure_single_truetype_line("Hg", font, letter_spacing=0)
    return {
        "ink_w": ink_w,
        "ink_h": ink_h,
        "bearing_x": bx,
        "bearing_y": by,
        "ascent": ascent,
        "descent": descent,
        "line_h": max(ink_h, ref_h, 1),
        "ref_bearing_y": ref_by,
    }


def render_text_mask(
    text: str,
    font_ref: str,
    font_size: int,
    *,
    letter_spacing: int = 0,
    crisp: bool = False,
    repo_root: Path = REPO_ROOT,
) -> Tuple[Image.Image, Dict[str, int]]:
    """Render a tightly cropped grayscale alpha mask of a single text line."""
    font = load_font(font_ref, font_size, repo_root=repo_root)
    metrics = measure_text_line(
        text, font_ref, font_size, letter_spacing=letter_spacing, repo_root=repo_root
    )
    if not text.strip():
        return Image.new("L", (max(1, metrics["ink_w"]), max(1, metrics["line_h"])), 0), metrics

    if isinstance(font, Pixel5x7Font):
        mask = font.render_mask(text, letter_spacing=letter_spacing)
        return mask, metrics

    pad = 2
    w = max(1, min(8192, metrics["ink_w"] + pad * 2))
    h = max(1, min(1024, metrics["ink_h"] + pad * 2))
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    if crisp:
        draw.fontmode = "1"

    ox = pad - metrics["bearing_x"]
    oy = pad - metrics["bearing_y"]

    if letter_spacing == 0:
        draw.text((ox, oy), text, font=font, fill=255)
    else:
        cursor_x = float(ox)
        for idx, ch in enumerate(text):
            draw.text((int(round(cursor_x)), oy), ch, font=font, fill=255)
            adv = font.getlength(ch) if hasattr(font, "getlength") else font.size * 0.6
            cursor_x += adv
            if idx < len(text) - 1:
                cursor_x += letter_spacing

    if crisp:
        arr = np.array(mask, dtype=np.uint8)
        arr = np.where(arr >= 115, 255, 0).astype(np.uint8)
        mask = Image.fromarray(arr, mode="L")

    # Tight crop to exact ink bounds so optical centering is pixel-accurate
    bbox = mask.getbbox()
    if bbox is not None:
        mask = mask.crop(bbox)
        metrics["ink_w"] = mask.width
        metrics["ink_h"] = mask.height

    return mask, metrics


def fit_font_size(
    text: str,
    font_ref: str,
    max_w: Optional[int],
    max_h: int,
    *,
    min_size: int = 7,
    max_size: int = 128,
    letter_spacing: int = 0,
    repo_root: Path = REPO_ROOT,
) -> int:
    """Binary-search the largest font size whose rendered ink fits inside ``(max_w, max_h)``."""
    safe_min = max(5, int(min_size))
    safe_max = max(safe_min, min(int(max_size), max(int(max_h) * 2, safe_min)))
    target_h = max(5, int(max_h))
    target_w = max(4, int(max_w)) if max_w is not None else None
    sample = text if text.strip() else "Hg"

    if font_ref == BUILTIN_PIXEL_FONT_ID:
        # Pixel 5x7 scales in clean integer multiples of 7px
        best = 7
        for scale in range(1, max(2, target_h // 7 + 2)):
            size = scale * 7
            if size > safe_max:
                break
            m = measure_text_line(
                sample, font_ref, size, letter_spacing=letter_spacing, repo_root=repo_root
            )
            if m["ink_h"] <= target_h and (target_w is None or m["ink_w"] <= target_w):
                best = size
            else:
                break
        return best

    lo, hi = safe_min, safe_max
    best = safe_min
    while lo <= hi:
        mid = (lo + hi) // 2
        m = measure_text_line(
            sample, font_ref, mid, letter_spacing=letter_spacing, repo_root=repo_root
        )
        fits_h = m["ink_h"] <= target_h
        fits_w = target_w is None or m["ink_w"] <= target_w
        if fits_h and fits_w:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def wrap_text_to_width(
    text: str,
    font_ref: str,
    font_size: int,
    max_width: int,
    *,
    letter_spacing: int = 0,
    repo_root: Path = REPO_ROOT,
) -> List[str]:
    """Word-wrap text into lines that fit within ``max_width`` pixels."""
    if not text:
        return [""]
    limit = max(8, int(max_width))
    wrapped: List[str] = []

    for raw_para in text.splitlines() or [""]:
        words = raw_para.split()
        if not words:
            wrapped.append("")
            continue

        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            m = measure_text_line(
                candidate,
                font_ref,
                font_size,
                letter_spacing=letter_spacing,
                repo_root=repo_root,
            )
            if m["ink_w"] <= limit:
                current = candidate
            else:
                wrapped.append(current)
                current = word
        wrapped.append(current)

    return wrapped or [""]


def _dilate_mask(mask_arr: np.ndarray, radius: int) -> np.ndarray:
    """Fast morphological dilation of a 2D uint8 mask by ``radius`` pixels."""
    if radius <= 0:
        return mask_arr
    size = radius * 2 + 1
    img = Image.fromarray(mask_arr, mode="L").filter(ImageFilter.MaxFilter(size=size))
    return np.array(img, dtype=np.uint8)


def colorize_mask_rgba(
    mask: Image.Image,
    *,
    color: Tuple[int, int, int] = (255, 255, 255),
    color_mode: str = "solid",
    color2: Tuple[int, int, int] = (255, 64, 129),
    phase: float = 0.0,
    outline_width: int = 0,
    outline_color: Tuple[int, int, int] = (0, 0, 0),
    shadow_dx: int = 0,
    shadow_dy: int = 0,
    shadow_color: Tuple[int, int, int] = (0, 0, 0),
    glow: int = 0,
) -> Tuple[np.ndarray, int, int]:
    """Render a styled RGBA uint8 array from a glyph mask.

    Returns ``(rgba_array, pad_x, pad_y)`` where ``pad_x/pad_y`` is the extra
    margin added on the left/top by outline, shadow, or glow so callers can
    align ink bounds optically.
    """
    mask_arr = np.array(mask, dtype=np.uint8)
    h, w = mask_arr.shape
    ow = max(0, min(3, int(outline_width)))
    gw = max(0, min(3, int(glow)))
    sdx = max(-6, min(6, int(shadow_dx)))
    sdy = max(-6, min(6, int(shadow_dy)))

    pad_left = max(ow, gw * 2, max(0, -sdx))
    pad_right = max(ow, gw * 2, max(0, sdx))
    pad_top = max(ow, gw * 2, max(0, -sdy))
    pad_bottom = max(ow, gw * 2, max(0, sdy))

    out_w = w + pad_left + pad_right
    out_h = h + pad_top + pad_bottom
    canvas = np.zeros((out_h, out_w, 4), dtype=np.float32)

    # Place core mask in padded coordinates
    core_mask = np.zeros((out_h, out_w), dtype=np.uint8)
    core_mask[pad_top : pad_top + h, pad_left : pad_left + w] = mask_arr

    def _alpha_composite(dst: np.ndarray, src_rgb: np.ndarray, src_a: np.ndarray) -> None:
        a = src_a[:, :, np.newaxis]
        dst_a = dst[:, :, 3:4]
        out_a = a + dst_a * (1.0 - a)
        safe = np.where(out_a > 1e-6, out_a, 1.0)
        dst[:, :, :3] = (src_rgb * a + dst[:, :, :3] * dst_a * (1.0 - a)) / safe
        dst[:, :, 3:4] = out_a

    # 1. Optional neon glow halo behind text
    if gw > 0:
        glow_img = Image.fromarray(core_mask, mode="L").filter(
            ImageFilter.GaussianBlur(radius=gw * 1.15)
        )
        glow_a = (np.array(glow_img, dtype=np.float32) / 255.0) * 0.72
        glow_rgb = np.empty((out_h, out_w, 3), dtype=np.float32)
        glow_rgb[:, :, 0] = color[0]
        glow_rgb[:, :, 1] = color[1]
        glow_rgb[:, :, 2] = color[2]
        _alpha_composite(canvas, glow_rgb, glow_a)

    # 2. Optional drop shadow
    if sdx != 0 or sdy != 0:
        sh_mask = np.zeros((out_h, out_w), dtype=np.uint8)
        sy0 = pad_top + sdy
        sx0 = pad_left + sdx
        sh_mask[sy0 : sy0 + h, sx0 : sx0 + w] = mask_arr
        sh_a = (sh_mask.astype(np.float32) / 255.0) * 0.85
        sh_rgb = np.empty((out_h, out_w, 3), dtype=np.float32)
        sh_rgb[:, :, 0] = shadow_color[0]
        sh_rgb[:, :, 1] = shadow_color[1]
        sh_rgb[:, :, 2] = shadow_color[2]
        _alpha_composite(canvas, sh_rgb, sh_a)

    # 3. Optional outline / stroke
    if ow > 0:
        out_mask = _dilate_mask(core_mask, ow)
        out_a = out_mask.astype(np.float32) / 255.0
        out_rgb = np.empty((out_h, out_w, 3), dtype=np.float32)
        out_rgb[:, :, 0] = outline_color[0]
        out_rgb[:, :, 1] = outline_color[1]
        out_rgb[:, :, 2] = outline_color[2]
        _alpha_composite(canvas, out_rgb, out_a)

    # 4. Text fill (solid, horizontal/vertical gradient, rainbow wave, or neon pulse)
    fill_rgb = np.zeros((out_h, out_w, 3), dtype=np.float32)
    mode = (color_mode or "solid").strip().lower()
    c1 = np.array(color, dtype=np.float32)
    c2 = np.array(color2, dtype=np.float32)

    if mode == "gradient_x":
        xs = np.linspace(0.0, 1.0, max(1, w), dtype=np.float32)
        grad = c1[np.newaxis, :] * (1.0 - xs[:, np.newaxis]) + c2[np.newaxis, :] * xs[:, np.newaxis]
        fill_rgb[pad_top : pad_top + h, pad_left : pad_left + w] = grad[np.newaxis, :, :]
    elif mode == "gradient_y":
        ys = np.linspace(0.0, 1.0, max(1, h), dtype=np.float32)
        grad = c1[np.newaxis, :] * (1.0 - ys[:, np.newaxis]) + c2[np.newaxis, :] * ys[:, np.newaxis]
        fill_rgb[pad_top : pad_top + h, pad_left : pad_left + w] = grad[:, np.newaxis, :]
    elif mode == "rainbow":
        xs = np.arange(w, dtype=np.float32)
        wavelength = max(24.0, float(w) * 0.85)
        hues = ((xs / wavelength) - phase * 0.35) % 1.0
        row_rgb = np.zeros((w, 3), dtype=np.float32)
        for idx, hue in enumerate(hues):
            r, g, b = colorsys.hsv_to_rgb(float(hue), 0.92, 1.0)
            row_rgb[idx] = (r * 255.0, g * 255.0, b * 255.0)
        fill_rgb[pad_top : pad_top + h, pad_left : pad_left + w] = row_rgb[np.newaxis, :, :]
    elif mode == "pulse":
        gain = 0.58 + 0.42 * (0.5 + 0.5 * math.sin(phase * 3.2))
        fill_rgb[:, :, :] = np.clip(c1 * gain, 0.0, 255.0)
    else:
        fill_rgb[:, :, :] = c1

    core_a = core_mask.astype(np.float32) / 255.0
    _alpha_composite(canvas, fill_rgb, core_a)

    out_u8 = np.clip(np.round(canvas), 0, 255).astype(np.uint8)
    out_u8[:, :, 3] = np.clip(np.round(canvas[:, :, 3] * 255.0), 0, 255).astype(np.uint8)
    return out_u8, pad_left, pad_top


def render_background_rgb(
    width: int,
    height: int,
    *,
    bg_type: str = "solid",
    bg_color: Tuple[int, int, int] = (0, 0, 0),
    bg_color2: Tuple[int, int, int] = (10, 18, 42),
    elapsed: float = 0.0,
) -> np.ndarray:
    """Render an RGB uint8 background canvas of shape ``(height, width, 3)``."""
    w = max(1, int(width))
    h = max(1, int(height))
    kind = (bg_type or "solid").strip().lower()
    c1 = np.array(bg_color, dtype=np.float32)
    c2 = np.array(bg_color2, dtype=np.float32)

    if kind == "gradient_v":
        ys = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, np.newaxis, np.newaxis]
        col = c1[np.newaxis, np.newaxis, :] * (1.0 - ys) + c2[np.newaxis, np.newaxis, :] * ys
        frame = np.broadcast_to(col, (h, w, 3))
        return np.clip(np.round(frame), 0, 255).astype(np.uint8)

    if kind == "gradient_h":
        xs = np.linspace(0.0, 1.0, w, dtype=np.float32)[np.newaxis, :, np.newaxis]
        row = c1[np.newaxis, np.newaxis, :] * (1.0 - xs) + c2[np.newaxis, np.newaxis, :] * xs
        frame = np.broadcast_to(row, (h, w, 3))
        return np.clip(np.round(frame), 0, 255).astype(np.uint8)

    frame = np.full((h, w, 3), bg_color, dtype=np.uint8)

    if kind == "scanlines":
        frame[1::2] = np.clip(
            frame[1::2].astype(np.float32) * 0.45 + c2 * 0.25, 0, 255
        ).astype(np.uint8)
    elif kind == "starfield":
        count = max(8, min(42, (w * h) // 180))
        rng = np.random.default_rng(1337)
        xs = rng.integers(0, w, size=count)
        ys = rng.integers(0, h, size=count)
        phases = rng.uniform(0.0, 2.0 * math.pi, size=count)
        for i in range(count):
            twinkle = 0.5 + 0.5 * math.sin(elapsed * 3.5 + float(phases[i]))
            if twinkle > 0.35:
                v = int(60 + 160 * twinkle)
                star = (
                    min(255, int(c2[0] * 0.5 + v * 0.6)),
                    min(255, int(c2[1] * 0.5 + v * 0.7)),
                    min(255, int(c2[2] * 0.5 + v * 0.9)),
                )
                frame[int(ys[i]), int(xs[i])] = star

    return frame


def draw_border_rgb(
    frame: np.ndarray,
    *,
    border_style: str = "none",
    border_color: Tuple[int, int, int] = (0, 229, 255),
    elapsed: float = 0.0,
) -> None:
    """Draw an optional static or animated border directly onto ``frame`` in-place."""
    style = (border_style or "none").strip().lower()
    if style == "none":
        return

    h, w = frame.shape[:2]
    if w < 4 or h < 4:
        return

    if style == "solid":
        frame[0, :] = border_color
        frame[h - 1, :] = border_color
        frame[:, 0] = border_color
        frame[:, w - 1] = border_color
        return

    # Build ordered perimeter coordinates clockwise
    perim: List[Tuple[int, int]] = []
    for x in range(w):
        perim.append((x, 0))
    for y in range(1, h):
        perim.append((w - 1, y))
    for x in range(w - 2, -1, -1):
        perim.append((x, h - 1))
    for y in range(h - 2, 0, -1):
        perim.append((0, y))

    total = max(1, len(perim))
    if style == "chasing_bulbs":
        spacing = 3 if min(w, h) <= 24 else 4
        offset = int(elapsed * 6.0) % spacing
        dim = tuple(max(12, c // 5) for c in border_color)
        for idx, (px, py) in enumerate(perim):
            lit = (idx - offset) % spacing == 0
            frame[py, px] = border_color if lit else dim
    elif style == "neon_rainbow":
        hue_base = (elapsed * 0.25) % 1.0
        for idx, (px, py) in enumerate(perim):
            hue = (hue_base + idx / total) % 1.0
            r, g, b = colorsys.hsv_to_rgb(hue, 0.92, 0.95)
            frame[py, px] = (int(r * 255), int(g * 255), int(b * 255))


def composite_rgba_onto_rgb(
    dst_rgb: np.ndarray,
    src_rgba: np.ndarray,
    x: int,
    y: int,
    *,
    opacity: float = 1.0,
    clip_rect: Optional[Tuple[int, int, int, int]] = None,
) -> None:
    """Alpha-blend ``src_rgba`` onto ``dst_rgb`` at ``(x, y)`` with optional clip rect."""
    if opacity <= 0.001:
        return
    dh, dw = dst_rgb.shape[:2]
    sh, sw = src_rgba.shape[:2]

    clip_x0, clip_y0, clip_x1, clip_y1 = clip_rect or (0, 0, dw, dh)
    clip_x0 = max(0, clip_x0)
    clip_y0 = max(0, clip_y0)
    clip_x1 = min(dw, clip_x1)
    clip_y1 = min(dh, clip_y1)

    dst_x0 = max(clip_x0, x)
    dst_y0 = max(clip_y0, y)
    dst_x1 = min(clip_x1, x + sw)
    dst_y1 = min(clip_y1, y + sh)
    if dst_x0 >= dst_x1 or dst_y0 >= dst_y1:
        return

    src_x0 = dst_x0 - x
    src_y0 = dst_y0 - y
    src_x1 = src_x0 + (dst_x1 - dst_x0)
    src_y1 = src_y0 + (dst_y1 - dst_y0)

    patch = src_rgba[src_y0:src_y1, src_x0:src_x1]
    alpha = (patch[:, :, 3:4].astype(np.float32) / 255.0) * float(opacity)
    if not np.any(alpha > 0):
        return
    dst_slice = dst_rgb[dst_y0:dst_y1, dst_x0:dst_x1].astype(np.float32)
    blended = patch[:, :, :3].astype(np.float32) * alpha + dst_slice * (1.0 - alpha)
    dst_rgb[dst_y0:dst_y1, dst_x0:dst_x1] = np.clip(np.round(blended), 0, 255).astype(
        np.uint8
    )


def parse_hex_or_rgb(
    value: Any, default: Tuple[int, int, int] = (255, 255, 255)
) -> Tuple[int, int, int]:
    """Convenience wrapper over ``led_color.parse_color``."""
    return parse_color(value, default)


def apply_color_order_array(frame_rgb: np.ndarray, color_order: str) -> np.ndarray:
    """Swap channels on an RGB numpy array when running on LiveMatrix with non-RGB LEDs."""
    if not color_order or color_order == "rgb":
        return frame_rgb
    idx_map = {"r": 0, "g": 1, "b": 2}
    order = [idx_map.get(ch, i) for i, ch in enumerate(color_order[:3])]
    return frame_rgb[:, :, order]
