"""Smart, screen-aware multi-line LED marquee player with declarative CONFIG_SCHEMA and live preview."""

from __future__ import annotations

import math
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image

from lib.led_fonts import BUILTIN_PIXEL_FONT_ID, DEFAULT_FONT_ID, get_font_meta
from lib.text_layout import (
    apply_color_order_array,
    apply_text_transform,
    classify_screen,
    colorize_mask_rgba,
    composite_rgba_onto_rgb,
    draw_border_rgb,
    expand_dynamic_tokens,
    fit_font_size,
    measure_text_line,
    parse_hex_or_rgb,
    render_background_rgb,
    render_text_mask,
    should_render_crisp,
    wrap_text_to_width,
)

DEFAULT_TEXT = "WELCOME TO\nLED MATRIX"

CONFIG_SCHEMA = [
    # ── Content ──────────────────────────────────────────────────────────────
    {
        "key": "content_mode",
        "label": "Composition Mode",
        "section": "Content",
        "type": "select",
        "default": "simple",
        "description": "Use Multi-line Text for fast signs, credits, and slides (separate slides with ---), or Styled Lines to customize each line's font, color, and motion independently.",
        "options": [
            {"value": "simple", "label": "Multi-line Text & Slides"},
            {"value": "layers", "label": "Styled Lines (Per-line Font, Color & Motion)"},
        ],
    },
    {
        "key": "text",
        "label": "Message Text",
        "section": "Content",
        "type": "textarea",
        "default": "WELCOME TO\nLED MATRIX",
        "placeholder": "Type one or more lines...\nUse --- on its own line to create multiple slides.",
        "description": "Press Enter for multiple lines, or put --- on its own line to create a multi-slide deck.",
        "tokens": [
            {"token": "{time}", "label": "Time (12h)"},
            {"token": "{time24}", "label": "Time (24h)"},
            {"token": "{date}", "label": "Date"},
            {"token": "{day}", "label": "Weekday"},
            {"token": "{countdown:2026-12-31 23:59}", "label": "Countdown"},
        ],
        "showWhen": {"key": "content_mode", "equals": "simple"},
    },
    {
        "key": "wrap",
        "label": "Auto Word-Wrap",
        "section": "Content",
        "type": "boolean",
        "default": False,
        "description": "Automatically wrap long sentences across multiple lines to fit the matrix width.",
        "showWhen": {"key": "content_mode", "equals": "simple"},
    },
    {
        "key": "lines",
        "label": "Styled Lines",
        "section": "Content",
        "type": "list",
        "itemLabel": "Line",
        "addLabel": "Add Styled Line",
        "minItems": 1,
        "maxItems": 8,
        "reorderable": True,
        "description": "Stack independent lines — e.g., a static centered header above a scrolling ticker.",
        "showWhen": {"key": "content_mode", "equals": "layers"},
        "default": [
            {
                "text": "NOW PLAYING",
                "font": "barlow_condensed_bold.ttf",
                "size": "auto",
                "color": "#00e5ff",
                "color_mode": "inherit",
                "color2": "#ff4081",
                "align": "center",
                "motion": "static",
            },
            {
                "text": "Welcome to LED Matrix Studio • Customize fonts, colors & motion!",
                "font": "dosis.ttf",
                "size": "auto",
                "color": "#ffd700",
                "color_mode": "inherit",
                "color2": "#ff4081",
                "align": "center",
                "motion": "scroll_left",
            },
        ],
        "itemFields": [
            {
                "key": "text",
                "label": "Text",
                "type": "text",
                "default": "Hello LED Matrix",
                "placeholder": "Line text (supports {time}, {date})...",
                "required": True,
            },
            {
                "key": "font",
                "label": "Font",
                "type": "font",
                "default": "dosis.ttf",
                "previewTextKey": "text",
            },
            {
                "key": "size",
                "label": "Size",
                "type": "number",
                "allowAuto": True,
                "default": "auto",
                "min": 6,
                "max": 96,
                "step": 1,
                "integer": True,
                "unit": "px",
            },
            {
                "key": "color",
                "label": "Color",
                "type": "color",
                "default": "#00e5ff",
            },
            {
                "key": "color_mode",
                "label": "Fill",
                "type": "select",
                "default": "inherit",
                "options": [
                    {"value": "inherit", "label": "Inherit Global"},
                    {"value": "solid", "label": "Solid"},
                    {"value": "gradient_x", "label": "Horizontal Gradient"},
                    {"value": "gradient_y", "label": "Vertical Gradient"},
                    {"value": "rainbow", "label": "Rainbow Wave"},
                    {"value": "pulse", "label": "Neon Pulse"},
                ],
            },
            {
                "key": "motion",
                "label": "Line Motion",
                "type": "select",
                "default": "inherit",
                "options": [
                    {"value": "inherit", "label": "Inherit Global"},
                    {"value": "auto", "label": "Smart Auto"},
                    {"value": "static", "label": "Static"},
                    {"value": "scroll_left", "label": "Scroll Left"},
                    {"value": "scroll_right", "label": "Scroll Right"},
                    {"value": "bounce", "label": "Bounce"},
                ],
            },
            {
                "key": "color2",
                "label": "Gradient End",
                "type": "color",
                "default": "#ff4081",
                "showWhen": {"key": "color_mode", "in": ["gradient_x", "gradient_y"]},
            },
            {
                "key": "align",
                "label": "Horizontal Align",
                "type": "alignment",
                "mode": "horizontal",
                "default": "center",
            },
        ],
    },
    # ── Typography ───────────────────────────────────────────────────────────
    {
        "key": "font",
        "label": "Font Family",
        "section": "Typography",
        "type": "font",
        "default": "dosis.ttf",
        "previewTextKey": "text",
        "description": "Bundled LED-tested fonts & custom uploads. Pixel fonts stay sharp on tiny matrices.",
    },
    {
        "key": "font_size",
        "label": "Font Size",
        "section": "Typography",
        "type": "number",
        "allowAuto": True,
        "default": "auto",
        "min": 6,
        "max": 120,
        "step": 1,
        "integer": True,
        "unit": "px",
        "description": "Auto chooses the largest readable size for your screen dimensions and line count.",
    },
    {
        "key": "align",
        "label": "Alignment",
        "section": "Typography",
        "type": "alignment",
        "mode": "grid",
        "default": "center-middle",
        "description": "Optical horizontal and vertical positioning on the LED canvas.",
    },
    {
        "key": "letter_spacing",
        "label": "Letter Spacing",
        "section": "Typography",
        "type": "number",
        "default": 0,
        "min": -2,
        "max": 8,
        "step": 1,
        "integer": True,
        "unit": "px",
    },
    {
        "key": "line_spacing",
        "label": "Line Spacing",
        "section": "Typography",
        "type": "number",
        "default": 1.15,
        "min": 0.85,
        "max": 2.0,
        "step": 0.05,
        "unit": "×",
    },
    {
        "key": "transform",
        "label": "Text Case",
        "section": "Typography",
        "type": "select",
        "default": "none",
        "options": [
            {"value": "none", "label": "As Typed"},
            {"value": "uppercase", "label": "UPPERCASE"},
            {"value": "lowercase", "label": "lowercase"},
            {"value": "title", "label": "Title Case"},
        ],
    },
    {
        "key": "rendering",
        "label": "Pixel Crispness",
        "section": "Typography",
        "type": "select",
        "default": "auto",
        "description": "Auto uses razor-sharp binary pixels on small matrices and smooth anti-aliasing on large displays.",
        "options": [
            {"value": "auto", "label": "Smart Auto"},
            {"value": "crisp", "label": "Crisp Pixel (No Blur)"},
            {"value": "smooth", "label": "Smooth Anti-Aliased"},
        ],
    },
    # ── Style ────────────────────────────────────────────────────────────────
    {
        "key": "color_mode",
        "label": "Text Fill",
        "section": "Style",
        "type": "select",
        "default": "solid",
        "options": [
            {"value": "solid", "label": "Solid Color"},
            {"value": "gradient_x", "label": "Horizontal Gradient"},
            {"value": "gradient_y", "label": "Vertical Gradient"},
            {"value": "rainbow", "label": "Animated Rainbow"},
            {"value": "pulse", "label": "Neon Pulse"},
        ],
    },
    {
        "key": "color",
        "label": "Text Color",
        "section": "Style",
        "type": "color",
        "default": "#00e5ff",
        "showWhen": {"key": "color_mode", "notEquals": "rainbow"},
    },
    {
        "key": "color2",
        "label": "Gradient End Color",
        "section": "Style",
        "type": "color",
        "default": "#ff4081",
        "showWhen": {"key": "color_mode", "in": ["gradient_x", "gradient_y"]},
    },
    {
        "key": "outline_width",
        "label": "Outline Thickness",
        "section": "Style",
        "type": "number",
        "default": 0,
        "min": 0,
        "max": 3,
        "step": 1,
        "integer": True,
        "unit": "px",
    },
    {
        "key": "outline_color",
        "label": "Outline Color",
        "section": "Style",
        "type": "color",
        "default": "#000000",
        "showWhen": {"key": "outline_width", "gt": 0},
    },
    {
        "key": "shadow",
        "label": "Drop Shadow",
        "section": "Style",
        "type": "boolean",
        "default": False,
        "description": "Adds a crisp 1px offset shadow behind lettering for contrast.",
    },
    {
        "key": "shadow_color",
        "label": "Shadow Color",
        "section": "Style",
        "type": "color",
        "default": "#002b36",
        "showWhen": {"key": "shadow", "truthy": True},
    },
    {
        "key": "glow",
        "label": "Neon Glow",
        "section": "Style",
        "type": "number",
        "default": 0,
        "min": 0,
        "max": 3,
        "step": 1,
        "integer": True,
        "description": "Soft luminous halo around lettering (best on standard & large displays).",
    },
    {
        "key": "bg_type",
        "label": "Background",
        "section": "Style",
        "type": "select",
        "default": "solid",
        "options": [
            {"value": "solid", "label": "Solid"},
            {"value": "gradient_v", "label": "Vertical Gradient"},
            {"value": "gradient_h", "label": "Horizontal Gradient"},
            {"value": "starfield", "label": "Twinkling Starfield"},
            {"value": "scanlines", "label": "Retro Scanlines"},
        ],
    },
    {
        "key": "bg_color",
        "label": "Background Color",
        "section": "Style",
        "type": "color",
        "default": "#000000",
    },
    {
        "key": "bg_color2",
        "label": "Background Accent",
        "section": "Style",
        "type": "color",
        "default": "#0b1437",
        "showWhen": {"key": "bg_type", "notEquals": "solid"},
    },
    {
        "key": "border",
        "label": "Frame Border",
        "section": "Style",
        "type": "select",
        "default": "none",
        "options": [
            {"value": "none", "label": "None"},
            {"value": "solid", "label": "Solid Line"},
            {"value": "chasing_bulbs", "label": "Chasing Marquee Bulbs"},
            {"value": "neon_rainbow", "label": "Animated Neon Rainbow"},
        ],
    },
    {
        "key": "border_color",
        "label": "Border Color",
        "section": "Style",
        "type": "color",
        "default": "#ffd700",
        "showWhen": {"key": "border", "in": ["solid", "chasing_bulbs"]},
    },
    {
        "key": "padding",
        "label": "Safe Padding",
        "section": "Style",
        "type": "number",
        "default": 2,
        "min": 0,
        "max": 16,
        "step": 1,
        "integer": True,
        "unit": "px",
    },
    # ── Motion ───────────────────────────────────────────────────────────────
    {
        "key": "mode",
        "label": "Motion Mode",
        "section": "Motion",
        "type": "select",
        "default": "auto",
        "description": "Smart Auto centers text when it fits cleanly and automatically scrolls or bounces when it overflows.",
        "options": [
            {"value": "auto", "label": "Smart Auto (Fit or Scroll)"},
            {"value": "static", "label": "Static (Fit & Center)"},
            {"value": "scroll_left", "label": "Ticker Scroll (Right → Left)"},
            {"value": "scroll_right", "label": "Reverse Scroll (Left → Right)"},
            {"value": "scroll_up", "label": "Credits Roll (Scroll Up)"},
            {"value": "bounce", "label": "Ping-Pong Bounce"},
            {"value": "typewriter", "label": "Typewriter Reveal"},
        ],
    },
    {
        "key": "speed",
        "label": "Scroll Speed",
        "section": "Motion",
        "type": "number",
        "default": 36,
        "min": 6,
        "max": 140,
        "step": 2,
        "integer": True,
        "unit": "px/s",
        "showWhen": {"key": "mode", "notEquals": "static"},
    },
    {
        "key": "loop_gap",
        "label": "Loop Gap",
        "section": "Motion",
        "type": "number",
        "default": 28,
        "min": 6,
        "max": 120,
        "step": 2,
        "integer": True,
        "unit": "px",
        "description": "Space between the end of the message and the start of the next seamless loop.",
        "showWhen": {"key": "mode", "in": ["auto", "scroll_left", "scroll_right", "scroll_up"]},
    },
    {
        "key": "pause_sec",
        "label": "Edge / Reveal Pause",
        "section": "Motion",
        "type": "number",
        "default": 1.2,
        "min": 0.0,
        "max": 6.0,
        "step": 0.2,
        "unit": "s",
        "showWhen": {"key": "mode", "in": ["auto", "bounce", "typewriter"]},
    },
    {
        "key": "slide_sec",
        "label": "Slide Hold Time",
        "section": "Motion",
        "type": "number",
        "default": 4.0,
        "min": 1.5,
        "max": 20.0,
        "step": 0.5,
        "unit": "s",
        "description": "How long each slide stays visible when using --- slide dividers.",
        "showWhen": {"key": "content_mode", "equals": "simple"},
    },
    {
        "key": "transition",
        "label": "Slide Transition",
        "section": "Motion",
        "type": "select",
        "default": "fade",
        "showWhen": {"key": "content_mode", "equals": "simple"},
        "options": [
            {"value": "fade", "label": "Crossfade"},
            {"value": "slide_left", "label": "Slide Left"},
            {"value": "slide_up", "label": "Slide Up"},
            {"value": "cut", "label": "Instant Cut"},
        ],
    },
]

CONFIG_PRESETS = [
    {
        "id": "neon_welcome",
        "label": "Neon Sign",
        "description": "Centered bold 2-line sign with gradient, glow & chasing bulbs",
        "config": {
            "content_mode": "simple",
            "text": "WELCOME\nTO THE LAB",
            "font": "bungee.ttf",
            "font_size": "auto",
            "align": "center-middle",
            "color_mode": "gradient_x",
            "color": "#00e5ff",
            "color2": "#ff4081",
            "glow": 1,
            "border": "chasing_bulbs",
            "border_color": "#ffd700",
            "bg_type": "solid",
            "bg_color": "#050712",
            "padding": 4,
            "mode": "auto",
        },
    },
    {
        "id": "classic_ticker",
        "label": "Classic Ticker",
        "description": "Seamless high-speed single-line ticker banner",
        "config": {
            "content_mode": "simple",
            "text": "BREAKING NEWS • PI LED MATRIX STUDIO IS LIVE • CUSTOM FONTS & SMART LAYOUT",
            "font": "barlow_condensed_bold.ttf",
            "font_size": "auto",
            "align": "center-middle",
            "color_mode": "solid",
            "color": "#ffd700",
            "bg_type": "solid",
            "bg_color": "#000000",
            "border": "none",
            "mode": "scroll_left",
            "speed": 46,
            "loop_gap": 36,
        },
    },
    {
        "id": "header_ticker",
        "label": "Header + Ticker",
        "description": "Static centered title over an independent scrolling ticker",
        "config": {
            "content_mode": "layers",
            "bg_type": "gradient_v",
            "bg_color": "#050b1f",
            "bg_color2": "#000000",
            "border": "solid",
            "border_color": "#1e3a5f",
            "padding": 3,
            "speed": 38,
            "lines": [
                {
                    "text": "NOW PLAYING",
                    "font": "space_grotesk_bold.ttf",
                    "size": "auto",
                    "color": "#00e5ff",
                    "color_mode": "solid",
                    "color2": "#ff4081",
                    "align": "center",
                    "motion": "static",
                },
                {
                    "text": "Synthwave Night • Fresh Drinks in the Kitchen • Enjoy the Light Show!",
                    "font": "dosis.ttf",
                    "size": "auto",
                    "color": "#ffd700",
                    "color_mode": "gradient_x",
                    "color2": "#ff8c00",
                    "align": "center",
                    "motion": "scroll_left",
                },
            ],
        },
    },
    {
        "id": "live_clock",
        "label": "Live Clock",
        "description": "Real-time clock & date using dynamic tokens",
        "config": {
            "content_mode": "simple",
            "text": "{time}\n{day} • {date}",
            "font": "share_tech_mono.ttf",
            "font_size": "auto",
            "align": "center-middle",
            "color_mode": "gradient_y",
            "color": "#00e5ff",
            "color2": "#00e676",
            "bg_type": "gradient_v",
            "bg_color": "#040814",
            "bg_color2": "#0a1628",
            "border": "none",
            "mode": "static",
            "padding": 3,
        },
    },
    {
        "id": "retro_pixel",
        "label": "Tiny / Arcade",
        "description": "Razor-sharp 5×7 pixel text built for 32×16 & 64×32 panels",
        "config": {
            "content_mode": "simple",
            "text": "PLAYER 1\nREADY!",
            "font": "pixel_5x7",
            "font_size": "auto",
            "align": "center-middle",
            "rendering": "crisp",
            "color_mode": "solid",
            "color": "#00e676",
            "bg_type": "scanlines",
            "bg_color": "#040a06",
            "bg_color2": "#0e2a16",
            "border": "none",
            "mode": "auto",
            "padding": 1,
        },
    },
    {
        "id": "credits_roll",
        "label": "Credits Roll",
        "description": "Auto-wrapped multi-line vertical credits over a starfield",
        "config": {
            "content_mode": "simple",
            "text": "STARRING\nPI LED MATRIX\n\nDIRECTED BY\nYOU\n\nBUILT WITH\nPYTHON & PIXELS",
            "wrap": True,
            "font": "oswald_bold.ttf",
            "font_size": "auto",
            "align": "center-middle",
            "color_mode": "solid",
            "color": "#ffd700",
            "bg_type": "starfield",
            "bg_color": "#030510",
            "bg_color2": "#4f8cff",
            "border": "none",
            "mode": "scroll_up",
            "speed": 22,
            "loop_gap": 24,
        },
    },
    {
        "id": "multi_slide",
        "label": "Slide Deck",
        "description": "3 rotating announcement cards with smooth crossfade",
        "config": {
            "content_mode": "simple",
            "text": "WELCOME!\nMAKE YOURSELF AT HOME\n---\nWIFI: GUEST\nPASS: PIXELS123\n---\nENJOY THE\nLIGHT SHOW!",
            "font": "space_grotesk_bold.ttf",
            "font_size": "auto",
            "align": "center-middle",
            "color_mode": "rainbow",
            "bg_type": "solid",
            "bg_color": "#050712",
            "border": "neon_rainbow",
            "padding": 4,
            "mode": "auto",
            "slide_sec": 3.5,
            "transition": "fade",
        },
    },
]


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{max(0, min(255, int(r))):02x}{max(0, min(255, int(g))):02x}{max(0, min(255, int(b))):02x}"


def _parse_align(align_value: Any) -> Tuple[str, str]:
    raw = str(align_value or "center-middle").strip().lower()
    if "-" in raw:
        h_part, v_part = raw.split("-", 1)
    elif raw in ("left", "center", "right"):
        h_part, v_part = raw, "middle"
    else:
        h_part, v_part = "center", "middle"
    h = h_part if h_part in ("left", "center", "right") else "center"
    v = v_part if v_part in ("top", "middle", "bottom") else "middle"
    return h, v


def _safe_float(val: Any, default: float, lo: float, hi: float) -> float:
    try:
        f = float(val)
        if not math.isfinite(f):
            return default
        return max(lo, min(hi, f))
    except (TypeError, ValueError):
        return default


def _safe_int(val: Any, default: int, lo: int, hi: int) -> int:
    return int(round(_safe_float(val, float(default), float(lo), float(hi))))


def normalize_marquee_config(raw_cfg: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Normalize both new v2 configs and legacy ``{messages: [...]}`` configs cleanly."""
    cfg = dict(raw_cfg) if isinstance(raw_cfg, dict) else {}

    # Detect legacy schema: {"messages": [{"left", "right", "r", "g", "b", "message", "font", "font_size"}]}
    has_legacy = (
        isinstance(cfg.get("messages"), list)
        and len(cfg["messages"]) > 0
        and "content_mode" not in cfg
        and "text" not in cfg
        and "lines" not in cfg
    )

    if has_legacy:
        converted_lines: List[Dict[str, Any]] = []
        for entry in cfg["messages"]:
            if not isinstance(entry, dict):
                continue
            msg = str(entry.get("message") or "").strip()
            if not msg:
                continue
            r = _safe_int(entry.get("r"), 255, 0, 255)
            g = _safe_int(entry.get("g"), 255, 0, 255)
            b = _safe_int(entry.get("b"), 255, 0, 255)
            fsize = entry.get("font_size")
            converted_lines.append(
                {
                    "text": msg,
                    "font": str(entry.get("font") or DEFAULT_FONT_ID),
                    "size": _safe_int(fsize, 0, 6, 120) if fsize is not None else "auto",
                    "color": _rgb_to_hex(r, g, b),
                    "color_mode": "solid",
                    "color2": "#ff4081",
                    "align": "center",
                    "motion": "scroll_left",
                }
            )
        cfg["content_mode"] = "layers"
        cfg["lines"] = converted_lines or [
            {
                "text": DEFAULT_TEXT.replace("\n", " "),
                "font": DEFAULT_FONT_ID,
                "size": "auto",
                "color": "#00e5ff",
                "color_mode": "solid",
                "color2": "#ff4081",
                "align": "center",
                "motion": "scroll_left",
            }
        ]
        cfg.setdefault("mode", "scroll_left")

    content_mode = str(cfg.get("content_mode") or "simple").strip().lower()
    if content_mode not in ("simple", "layers"):
        content_mode = "simple"

    raw_font_size = cfg.get("font_size", "auto")
    if raw_font_size is None or str(raw_font_size).strip().lower() == "auto":
        font_size: Any = "auto"
    else:
        font_size = _safe_int(raw_font_size, 16, 5, 160)

    out: Dict[str, Any] = {
        "content_mode": content_mode,
        "text": (str(cfg["text"]) if "text" in cfg and cfg["text"] is not None else DEFAULT_TEXT)[:4000],
        "wrap": bool(cfg.get("wrap", False)),
        "lines": (cfg.get("lines") if isinstance(cfg.get("lines"), list) else [])[:32],
        "font": str(cfg.get("font") or DEFAULT_FONT_ID).strip() or DEFAULT_FONT_ID,
        "font_size": font_size,
        "align": str(cfg.get("align") or "center-middle"),
        "letter_spacing": _safe_int(cfg.get("letter_spacing"), 0, -2, 8),
        "line_spacing": _safe_float(cfg.get("line_spacing"), 1.15, 0.85, 2.0),
        "transform": str(cfg.get("transform") or "none").strip().lower(),
        "rendering": str(cfg.get("rendering") or "auto").strip().lower(),
        "color_mode": str(cfg.get("color_mode") or "solid").strip().lower(),
        "color": str(cfg.get("color") or "#00e5ff"),
        "color2": str(cfg.get("color2") or "#ff4081"),
        "outline_width": _safe_int(cfg.get("outline_width"), 0, 0, 3),
        "outline_color": str(cfg.get("outline_color") or "#000000"),
        "shadow": bool(cfg.get("shadow", False)),
        "shadow_color": str(cfg.get("shadow_color") or "#002b36"),
        "glow": _safe_int(cfg.get("glow"), 0, 0, 3),
        "bg_type": str(cfg.get("bg_type") or "solid").strip().lower(),
        "bg_color": str(cfg.get("bg_color") or "#000000"),
        "bg_color2": str(cfg.get("bg_color2") or "#0b1437"),
        "border": str(cfg.get("border") or "none").strip().lower(),
        "border_color": str(cfg.get("border_color") or "#ffd700"),
        "padding": _safe_int(cfg.get("padding"), 2, 0, 16),
        "mode": str(cfg.get("mode") or "auto").strip().lower(),
        "speed": _safe_int(cfg.get("speed"), 36, 6, 140),
        "loop_gap": _safe_int(cfg.get("loop_gap"), 28, 6, 120),
        "pause_sec": _safe_float(cfg.get("pause_sec"), 1.2, 0.0, 6.0),
        "slide_sec": _safe_float(cfg.get("slide_sec"), 4.0, 1.0, 30.0),
        "transition": str(cfg.get("transition") or "fade").strip().lower(),
    }
    return out


def _split_slides_from_text(raw_text: str) -> List[List[str]]:
    """Split simple textarea text into slides using ``---`` dividers."""
    slides: List[List[str]] = []
    current: List[str] = []
    for raw_line in raw_text.splitlines():
        if raw_line.strip() == "---":
            if current:
                slides.append(current)
                current = []
        else:
            current.append(raw_line)
    if current:
        slides.append(current)
    # Remove leading/trailing empty lines per slide, keep internal blank lines for spacing
    cleaned: List[List[str]] = []
    for sl in slides:
        while sl and not sl[0].strip():
            sl.pop(0)
        while sl and not sl[-1].strip():
            sl.pop()
        if sl:
            cleaned.append(sl[:40])
    return cleaned[:16] or [["LED MATRIX"]]


class _PreparedLine:
    """Pre-measured & pre-masked line ready for blazing-fast frame compositing."""

    def __init__(
        self,
        *,
        text: str,
        font_ref: str,
        font_size: int,
        crisp: bool,
        color: Tuple[int, int, int],
        color_mode: str,
        color2: Tuple[int, int, int],
        align_h: str,
        motion: str,
        outline_width: int,
        outline_color: Tuple[int, int, int],
        shadow_dx: int,
        shadow_dy: int,
        shadow_color: Tuple[int, int, int],
        glow: int,
        letter_spacing: int,
    ) -> None:
        self.text = text
        self.font_ref = font_ref
        self.font_size = font_size
        self.crisp = crisp
        self.color = color
        self.color_mode = color_mode
        self.color2 = color2
        self.align_h = align_h
        self.motion = motion
        self.outline_width = outline_width
        self.outline_color = outline_color
        self.shadow_dx = shadow_dx
        self.shadow_dy = shadow_dy
        self.shadow_color = shadow_color
        self.glow = glow
        self.letter_spacing = letter_spacing

        self.mask, self.metrics = render_text_mask(
            text,
            font_ref,
            font_size,
            letter_spacing=letter_spacing,
            crisp=crisp,
        )
        self.ink_w = self.mask.width if text.strip() else 0
        self.ink_h = self.mask.height if text.strip() else max(4, font_size // 2)
        self.is_animated_color = color_mode in ("rainbow", "pulse")
        self._static_rgba: Optional[Tuple[np.ndarray, int, int]] = None
        if not self.is_animated_color and text.strip():
            self._static_rgba = colorize_mask_rgba(
                self.mask,
                color=self.color,
                color_mode=self.color_mode,
                color2=self.color2,
                phase=0.0,
                outline_width=self.outline_width,
                outline_color=self.outline_color,
                shadow_dx=self.shadow_dx,
                shadow_dy=self.shadow_dy,
                shadow_color=self.shadow_color,
                glow=self.glow,
            )

    def get_rgba(self, phase: float) -> Tuple[Optional[np.ndarray], int, int]:
        if not self.text.strip():
            return None, 0, 0
        if self._static_rgba is not None:
            return self._static_rgba
        return colorize_mask_rgba(
            self.mask,
            color=self.color,
            color_mode=self.color_mode,
            color2=self.color2,
            phase=phase,
            outline_width=self.outline_width,
            outline_color=self.outline_color,
            shadow_dx=self.shadow_dx,
            shadow_dy=self.shadow_dy,
            shadow_color=self.shadow_color,
            glow=self.glow,
        )


class _PreparedSlide:
    """Compiled slide with optical line positions, effective motion modes, and diagnostics."""

    def __init__(
        self,
        *,
        lines: List[_PreparedLine],
        line_ys: List[int],
        total_block_h: int,
        vertical_scroll: bool,
        safe_rect: Tuple[int, int, int, int],
        align_v: str,
        is_typewriter: bool,
    ) -> None:
        self.lines = lines
        self.line_ys = line_ys
        self.total_block_h = total_block_h
        self.vertical_scroll = vertical_scroll
        self.safe_rect = safe_rect
        self.align_v = align_v
        self.is_typewriter = is_typewriter


def _build_slides_and_diagnostics(
    norm: Dict[str, Any],
    width: int,
    height: int,
    now: Optional[datetime] = None,
) -> Tuple[List[_PreparedSlide], List[Dict[str, Any]], Dict[str, Any]]:
    """Run the smart screen-aware layout solver and return prepared slides + diagnostics."""
    screen = classify_screen(width, height)
    border_inset = 1 if norm["border"] != "none" else 0
    max_pad = 0 if screen["tier"] == "micro" and norm["padding"] <= 1 else max(0, min(width, height) // 4 - border_inset)
    pad = min(norm["padding"], max_pad)
    inset = border_inset + pad
    safe_x0 = inset
    safe_y0 = inset
    safe_x1 = max(safe_x0 + 4, width - inset)
    safe_y1 = max(safe_y0 + 4, height - inset)
    safe_w = safe_x1 - safe_x0
    safe_h = safe_y1 - safe_y0
    safe_rect = (safe_x0, safe_y0, safe_x1, safe_y1)

    align_h, align_v = _parse_align(norm["align"])
    global_color = parse_hex_or_rgb(norm["color"], (0, 229, 255))
    global_color2 = parse_hex_or_rgb(norm["color2"], (255, 64, 129))
    outline_color = parse_hex_or_rgb(norm["outline_color"], (0, 0, 0))
    shadow_color = parse_hex_or_rgb(norm["shadow_color"], (0, 43, 54))
    outline_w = norm["outline_width"]
    glow_w = norm["glow"]
    shadow_dx = 1 if norm["shadow"] else 0
    shadow_dy = 1 if norm["shadow"] else 0
    letter_spacing = norm["letter_spacing"]
    line_spacing = norm["line_spacing"]
    global_mode = norm["mode"]

    diagnostics: List[Dict[str, Any]] = []
    warned_keys: set[str] = set()

    def _add_diag(
        level: str,
        message: str,
        *,
        key: Optional[str] = None,
        actions: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        if key and key in warned_keys:
            return
        if key:
            warned_keys.add(key)
        item: Dict[str, Any] = {"level": level, "message": message}
        if actions:
            item["actions"] = actions
        diagnostics.append(item)

    # Guardrails for tiny matrices
    effective_glow = glow_w
    if glow_w > 0 and not screen["supports_glow"]:
        effective_glow = 0
        _add_diag(
            "warn",
            f"Neon glow is automatically softened/disabled on {width}×{height} micro screens to keep letters sharp.",
            key="micro_glow",
            actions=[{"label": "Turn Off Glow", "patch": {"glow": 0}}],
        )

    effective_outline = outline_w
    if outline_w > 1 and not screen["supports_thick_outline"]:
        effective_outline = 1
        _add_diag(
            "warn",
            f"{outline_w}px outline is clamped to 1px on {width}×{height} displays to prevent crowding.",
            key="thick_outline",
            actions=[{"label": "Set Outline 1px", "patch": {"outline_width": 1}}],
        )

    # Assemble raw slide specs: list of slides, each slide is a list of line spec dicts
    slide_specs: List[List[Dict[str, Any]]] = []
    if norm["content_mode"] == "layers":
        raw_lines = [ln for ln in norm["lines"] if isinstance(ln, dict)]
        if not raw_lines:
            raw_lines = [{"text": "Hello LED Matrix"}]
        layer_specs: List[Dict[str, Any]] = []
        for entry in raw_lines:
            raw_txt = apply_text_transform(
                expand_dynamic_tokens(str(entry.get("text") or ""), now=now),
                norm["transform"],
            )
            fref = str(entry.get("font") or norm["font"]).strip() or norm["font"]
            lsize = entry.get("size", "auto")
            if lsize is None or str(lsize).strip().lower() == "auto":
                lsize_parsed: Any = "auto"
            else:
                lsize_parsed = _safe_int(lsize, 14, 5, 160)
            lcmode = str(entry.get("color_mode") or "inherit").strip().lower()
            if lcmode == "inherit":
                lcmode = norm["color_mode"]
            lcol = parse_hex_or_rgb(entry.get("color"), global_color)
            lcol2 = parse_hex_or_rgb(entry.get("color2"), global_color2)
            lalign = str(entry.get("align") or align_h).strip().lower()
            if lalign not in ("left", "center", "right"):
                lalign = align_h
            lmotion = str(entry.get("motion") or "inherit").strip().lower()
            if lmotion == "inherit":
                lmotion = global_mode
            layer_specs.append(
                {
                    "text": raw_txt,
                    "font": fref,
                    "size": lsize_parsed,
                    "color": lcol,
                    "color_mode": lcmode,
                    "color2": lcol2,
                    "align_h": lalign,
                    "motion": lmotion,
                }
            )
        slide_specs.append(layer_specs)
    else:
        expanded = apply_text_transform(
            expand_dynamic_tokens(norm["text"], now=now), norm["transform"]
        )
        raw_slides = _split_slides_from_text(expanded)
        for sl_lines in raw_slides:
            slide_specs.append(
                [
                    {
                        "text": line_txt,
                        "font": norm["font"],
                        "size": norm["font_size"],
                        "color": global_color,
                        "color_mode": norm["color_mode"],
                        "color2": global_color2,
                        "align_h": align_h,
                        "motion": global_mode,
                    }
                    for line_txt in sl_lines
                ]
            )

    prepared_slides: List[_PreparedSlide] = []
    computed_sizes: List[int] = []
    auto_scrolled_lines = 0
    auto_bounced_lines = 0
    auto_credits_slides = 0

    for spec_lines in slide_specs:
        # Optional word-wrap for simple mode
        if norm["content_mode"] == "simple" and norm["wrap"]:
            probe_font = norm["font"]
            probe_size = (
                norm["font_size"]
                if isinstance(norm["font_size"], int)
                else max(
                    get_font_meta(probe_font).get("minHeight", 10),
                    min(safe_h // 2, max(8, round(safe_h * 0.28))),
                )
            )
            wrapped_specs: List[Dict[str, Any]] = []
            for item in spec_lines:
                if not item["text"].strip():
                    wrapped_specs.append(item)
                    continue
                for piece in wrap_text_to_width(
                    item["text"],
                    probe_font,
                    probe_size,
                    safe_w,
                    letter_spacing=letter_spacing,
                ):
                    wrapped_specs.append({**item, "text": piece})
            spec_lines = wrapped_specs

        n_lines = max(1, len(spec_lines))
        is_credits_explicit = global_mode == "scroll_up"

        # Compute target height budget per line when font_size == "auto"
        gap_ratio = max(0.18, line_spacing - 0.92)
        if is_credits_explicit:
            # Credits roll prefers legible medium-large sizing regardless of line count
            auto_slot_h = max(
                screen["recommended_min_font"],
                min(safe_h, int(round(safe_h * (0.42 if safe_h <= 24 else 0.28)))),
            )
        elif n_lines == 1:
            auto_slot_h = max(6, int(math.floor(safe_h * 0.92)))
        else:
            # Reserve equal breathing space across all (n_lines + 1) gaps: top, middle(s), bottom
            even_ratio = 0.08 if screen["tier"] == "micro" else gap_ratio
            denom = n_lines + (n_lines + 1) * even_ratio
            auto_slot_h = max(6, int(math.floor(safe_h / max(1.0, denom))))

        # Warn if a slide has too many lines for a micro/compact screen
        if n_lines > screen["max_comfortable_lines"] and not is_credits_explicit:
            actions = [
                {"label": "Credits Scroll", "patch": {"mode": "scroll_up"}},
            ]
            if norm["font"] != BUILTIN_PIXEL_FONT_ID:
                actions.insert(
                    0, {"label": "Use Pixel 5×7", "patch": {"font": BUILTIN_PIXEL_FONT_ID}}
                )
            _add_diag(
                "warn",
                f"{n_lines} lines on a {width}×{height} ({screen['tier']}) matrix is dense — consider Credits Scroll or Pixel 5×7.",
                key="dense_lines",
                actions=actions,
            )

        # Determine final size for each line
        compiled_lines: List[_PreparedLine] = []
        extra_v_pad = effective_outline * 2 + abs(shadow_dy)
        extra_h_pad = effective_outline * 2 + abs(shadow_dx)

        # If simple mode with auto size across multiple lines, use a harmonized size across non-empty lines
        harmonized_simple_size: Optional[int] = None
        if norm["content_mode"] == "simple" and norm["font_size"] == "auto":
            font_meta = get_font_meta(norm["font"])
            min_legible = max(6, int(font_meta.get("minHeight", 10)))
            target_line_h = max(6, auto_slot_h - extra_v_pad)
            non_empty = [ln["text"] for ln in spec_lines if ln["text"].strip()]
            widest_text = max(non_empty, key=len) if non_empty else "Hg"

            if global_mode == "static":
                # Shrink to fit BOTH width and height cleanly
                harmonized_simple_size = fit_font_size(
                    widest_text,
                    norm["font"],
                    max_w=max(8, safe_w - extra_h_pad),
                    max_h=target_line_h,
                    min_size=min(min_legible, target_line_h),
                    letter_spacing=letter_spacing,
                )
            elif global_mode in ("scroll_left", "scroll_right", "scroll_up"):
                # Maximize vertical legibility (scrolling handles width!)
                harmonized_simple_size = fit_font_size(
                    "Hg",
                    norm["font"],
                    max_w=None,
                    max_h=target_line_h,
                    min_size=min(min_legible, target_line_h),
                    letter_spacing=letter_spacing,
                )
            else:
                # Smart auto / bounce / typewriter: try fitting both first; if too tiny, prioritize legibility and let motion handle width
                fit_both = fit_font_size(
                    widest_text,
                    norm["font"],
                    max_w=max(8, safe_w - extra_h_pad),
                    max_h=target_line_h,
                    min_size=6,
                    letter_spacing=letter_spacing,
                )
                fit_height_only = fit_font_size(
                    "Hg",
                    norm["font"],
                    max_w=None,
                    max_h=target_line_h,
                    min_size=6,
                    letter_spacing=letter_spacing,
                )
                # Keep static & centered if fitting width stays legible
                if fit_both >= min_legible and (
                    fit_both >= int(round(fit_height_only * 0.35))
                    or len(widest_text) <= 18
                ):
                    harmonized_simple_size = fit_both
                else:
                    harmonized_simple_size = max(min_legible, fit_height_only)

        for idx, item in enumerate(spec_lines):
            fref = item["font"]
            font_meta = get_font_meta(fref)
            min_legible = max(6, int(font_meta.get("minHeight", 10)))

            if isinstance(item["size"], int):
                chosen_size = item["size"]
            elif harmonized_simple_size is not None:
                chosen_size = harmonized_simple_size
            else:
                # Independent layer sizing (e.g. header + ticker)
                target_h = max(6, auto_slot_h - extra_v_pad)
                if item["motion"] in ("scroll_left", "scroll_right"):
                    chosen_size = fit_font_size(
                        "Hg",
                        fref,
                        max_w=None,
                        max_h=target_h,
                        min_size=min(min_legible, target_h),
                        letter_spacing=letter_spacing,
                    )
                elif item["motion"] == "static":
                    chosen_size = fit_font_size(
                        item["text"] or "Hg",
                        fref,
                        max_w=max(8, safe_w - extra_h_pad),
                        max_h=target_h,
                        min_size=6,
                        letter_spacing=letter_spacing,
                    )
                else:
                    fit_both = fit_font_size(
                        item["text"] or "Hg",
                        fref,
                        max_w=max(8, safe_w - extra_h_pad),
                        max_h=target_h,
                        min_size=6,
                        letter_spacing=letter_spacing,
                    )
                    fit_h = fit_font_size(
                        "Hg",
                        fref,
                        max_w=None,
                        max_h=target_h,
                        min_size=6,
                        letter_spacing=letter_spacing,
                    )
                    chosen_size = (
                        fit_both
                        if fit_both >= min_legible
                        and (
                            fit_both >= int(round(fit_h * 0.35))
                            or len(item["text"]) <= 18
                        )
                        else max(min_legible, fit_h)
                    )

            # Check font minimum readability warning
            if chosen_size < min_legible and fref != BUILTIN_PIXEL_FONT_ID:
                _add_diag(
                    "warn",
                    f"{font_meta['name']} works best at ≥ {min_legible}px (currently {chosen_size}px on {width}×{height}).",
                    key=f"font_small_{fref}",
                    actions=[
                        {"label": "Use Pixel 5×7", "patch": {"font": BUILTIN_PIXEL_FONT_ID}},
                        {"label": "Use Silkscreen", "patch": {"font": "silkscreen.ttf"}},
                    ],
                )

            crisp = should_render_crisp(norm["rendering"], fref, chosen_size, height)
            probe = measure_text_line(
                item["text"] or "Hg", fref, chosen_size, letter_spacing=letter_spacing
            )
            eff_motion = item["motion"]
            if eff_motion == "auto":
                if probe["ink_w"] + extra_h_pad <= safe_w:
                    eff_motion = "static"
                elif probe["ink_w"] + extra_h_pad <= int(safe_w * 1.35):
                    eff_motion = "bounce"
                    auto_bounced_lines += 1
                else:
                    eff_motion = "scroll_left"
                    auto_scrolled_lines += 1

            computed_sizes.append(chosen_size)
            compiled_lines.append(
                _PreparedLine(
                    text=item["text"],
                    font_ref=fref,
                    font_size=chosen_size,
                    crisp=crisp,
                    color=item["color"],
                    color_mode=item["color_mode"],
                    color2=item["color2"],
                    align_h=item["align_h"],
                    motion=eff_motion,
                    outline_width=effective_outline,
                    outline_color=outline_color,
                    shadow_dx=shadow_dx,
                    shadow_dy=shadow_dy,
                    shadow_color=shadow_color,
                    glow=effective_glow,
                    letter_spacing=letter_spacing,
                )
            )

        # In simple multi-line mode with Smart Auto, keep all lines in the slide on one
        # unified horizontal motion so unequal-length lines travel together cohesively.
        if (
            norm["content_mode"] == "simple"
            and global_mode == "auto"
            and len(compiled_lines) > 1
        ):
            max_line_w = max((ln.ink_w for ln in compiled_lines), default=0)
            if max_line_w + extra_h_pad <= safe_w:
                unified_motion = "static"
            elif max_line_w + extra_h_pad <= int(safe_w * 1.35):
                unified_motion = "bounce"
            else:
                unified_motion = "scroll_left"
            for ln in compiled_lines:
                ln.motion = unified_motion

        # Compute vertical positions optically
        sum_ink_h = sum(ln.ink_h for ln in compiled_lines)
        min_gap_each = 1 if len(compiled_lines) > 1 else 0
        min_required_h = sum_ink_h + max(0, len(compiled_lines) - 1) * min_gap_each
        vertical_scroll = is_credits_explicit or (
            global_mode == "auto" and min_required_h > safe_h
        )
        if vertical_scroll and not is_credits_explicit:
            auto_credits_slides += 1

        line_ys: List[int] = []
        if vertical_scroll:
            gaps = [
                max(2, int(round(ln.ink_h * max(0.25, line_spacing - 0.85))))
                for ln in compiled_lines[:-1]
            ]
            total_h = sum_ink_h + sum(gaps)
            cursor_y = 0
            for idx, ln in enumerate(compiled_lines):
                line_ys.append(cursor_y)
                cursor_y += ln.ink_h + (gaps[idx] if idx < len(gaps) else 0)
        elif len(compiled_lines) == 1:
            total_h = sum_ink_h
            if align_v == "top":
                y0 = safe_y0
            elif align_v == "bottom":
                y0 = safe_y1 - total_h
            else:
                y0 = safe_y0 + (safe_h - total_h) // 2
            line_ys.append(y0)
        elif align_v == "middle":
            # Distribute vertical whitespace evenly across top, between lines, and bottom.
            # At default line_spacing (1.15), top == middle == bottom!
            n = len(compiled_lines)
            remaining = max(0, safe_h - sum_ink_h)
            even_gap = remaining / float(n + 1)
            scale = line_spacing / 1.15
            max_gap = remaining / float(max(1, n - 1)) if remaining > 0 else 0.0
            min_gap = 1.0 if remaining >= (n - 1) else 0.0
            target_gap = max(min_gap, min(max_gap, even_gap * scale))
            total_gaps_h = target_gap * (n - 1)
            edge_margin = max(0.0, (remaining - total_gaps_h) / 2.0)

            cursor_f = float(safe_y0) + edge_margin
            for idx, ln in enumerate(compiled_lines):
                line_ys.append(int(round(cursor_f)))
                cursor_f += ln.ink_h + target_gap
            total_h = int(round(sum_ink_h + total_gaps_h))
        else:
            # Top- or bottom-aligned stacks keep comfortable inter-line spacing
            gaps = [
                max(
                    1 if screen["tier"] == "micro" else 2,
                    int(round(ln.ink_h * max(0.22, line_spacing - 0.85))),
                )
                for ln in compiled_lines[:-1]
            ]
            # Clamp gaps if they would overflow safe_h
            if sum_ink_h + sum(gaps) > safe_h and len(gaps) > 0:
                avail_gap = max(0, safe_h - sum_ink_h)
                per_gap = avail_gap // len(gaps)
                gaps = [per_gap for _ in gaps]
            total_h = sum_ink_h + sum(gaps)
            start_y = safe_y0 if align_v == "top" else (safe_y1 - total_h)
            cursor_y = start_y
            for idx, ln in enumerate(compiled_lines):
                line_ys.append(cursor_y)
                cursor_y += ln.ink_h + (gaps[idx] if idx < len(gaps) else 0)

        prepared_slides.append(
            _PreparedSlide(
                lines=compiled_lines,
                line_ys=line_ys,
                total_block_h=total_h,
                vertical_scroll=vertical_scroll,
                safe_rect=safe_rect,
                align_v=align_v,
                is_typewriter=(global_mode == "typewriter"),
            )
        )

    # Concise positive/informational summary diagnostic
    unique_sizes = sorted(set(computed_sizes))
    size_label = (
        f"{unique_sizes[0]}px"
        if len(unique_sizes) == 1
        else f"{unique_sizes[0]}–{unique_sizes[-1]}px"
    )
    slide_suffix = f" · {len(prepared_slides)} slides" if len(prepared_slides) > 1 else ""
    all_motions = {ln.motion for sl in prepared_slides for ln in sl.lines}
    if auto_credits_slides > 0:
        _add_diag(
            "info",
            f"Auto-switched to vertical credits scroll ({size_label}{slide_suffix}) so all lines stay legible on {width}×{height}.",
        )
    elif global_mode == "scroll_up":
        _add_diag(
            "ok",
            f"Credits scrolling vertically at {norm['speed']} px/s on {width}×{height} ({screen['tier']} · {size_label}{slide_suffix}).",
        )
    elif global_mode == "typewriter":
        _add_diag(
            "ok",
            f"Typewriter reveal on {width}×{height} ({screen['tier']} · {size_label}{slide_suffix}).",
        )
    elif auto_scrolled_lines > 0:
        _add_diag(
            "info",
            f"Auto-scrolling wide text smoothly at {norm['speed']} px/s on {width}×{height} ({size_label}{slide_suffix}).",
        )
    elif auto_bounced_lines > 0:
        _add_diag(
            "info",
            f"Slightly wider than {width}px — using smooth ping-pong bounce ({size_label}{slide_suffix}).",
        )
    elif any(m in ("scroll_left", "scroll_right") for m in all_motions):
        if "static" in all_motions:
            _add_diag(
                "ok",
                f"Mixed static + scrolling composition on {width}×{height} ({screen['tier']} · {size_label}{slide_suffix}).",
            )
        else:
            _add_diag(
                "ok",
                f"Scrolling smoothly at {norm['speed']} px/s on {width}×{height} ({screen['tier']} · {size_label}{slide_suffix}).",
            )
    elif "bounce" in all_motions:
        _add_diag(
            "ok",
            f"Ping-pong bounce on {width}×{height} ({screen['tier']} · {size_label}{slide_suffix}).",
        )
    else:
        _add_diag(
            "ok",
            f"Fits cleanly & optically centered on {width}×{height} ({screen['tier']} · {size_label}{slide_suffix}).",
        )

    summary = {
        "tier": screen["tier"],
        "slideCount": len(prepared_slides),
        "sizes": unique_sizes,
    }
    return prepared_slides, diagnostics, summary


def _render_slide_frame(
    slide: _PreparedSlide,
    norm: Dict[str, Any],
    width: int,
    height: int,
    slide_elapsed: float,
    global_elapsed: float,
    *,
    bg_frame: np.ndarray,
    opacity: float = 1.0,
    offset_x: int = 0,
    offset_y: int = 0,
) -> None:
    """Composite one slide onto ``bg_frame`` in-place at ``slide_elapsed`` seconds."""
    sx0, sy0, sx1, sy1 = slide.safe_rect
    safe_w = sx1 - sx0
    safe_h = sy1 - sy0
    speed = float(norm["speed"])
    loop_gap = int(norm["loop_gap"])
    pause_sec = float(norm["pause_sec"])

    # Typewriter reveal mode
    if slide.is_typewriter:
        total_chars = sum(len(ln.text) for ln in slide.lines)
        cps = max(4.0, speed * 0.45)
        reveal_time = total_chars / cps
        cycle = reveal_time + max(0.8, pause_sec) + 0.4
        local_t = slide_elapsed % max(0.5, cycle)
        chars_visible = min(total_chars, int(local_t * cps))
        remaining = chars_visible

        for ln, base_y in zip(slide.lines, slide.line_ys):
            if remaining <= 0:
                break
            visible = ln.text[:remaining]
            remaining -= len(ln.text)
            if not visible.strip():
                continue
            show_cursor = remaining == 0 and int(global_elapsed * 3.0) % 2 == 0
            draw_txt = visible + ("_" if show_cursor else "")
            mask, _ = render_text_mask(
                draw_txt,
                ln.font_ref,
                ln.font_size,
                letter_spacing=ln.letter_spacing,
                crisp=ln.crisp,
            )
            rgba, pad_l, pad_t = colorize_mask_rgba(
                mask,
                color=ln.color,
                color_mode=ln.color_mode,
                color2=ln.color2,
                phase=global_elapsed,
                outline_width=ln.outline_width,
                outline_color=ln.outline_color,
                shadow_dx=ln.shadow_dx,
                shadow_dy=ln.shadow_dy,
                shadow_color=ln.shadow_color,
                glow=ln.glow,
            )
            # Align using the full line width so text doesn't jitter while typing
            if ln.align_h == "left":
                draw_x = sx0
            elif ln.align_h == "right":
                draw_x = sx1 - ln.ink_w
            else:
                draw_x = sx0 + (safe_w - ln.ink_w) // 2
            composite_rgba_onto_rgb(
                bg_frame,
                rgba,
                draw_x - pad_l + offset_x,
                base_y - pad_t + offset_y,
                opacity=opacity,
                clip_rect=slide.safe_rect,
            )
        return

    # Vertical credits scroll: enter completely below bottom, exit completely above top
    if slide.vertical_scroll:
        extra_pad = max(
            norm["outline_width"],
            norm["glow"] * 2,
            1 if norm["shadow"] else 0,
        )
        span = slide.total_block_h + safe_h + loop_gap + extra_pad * 2
        v_speed = max(8.0, speed * 0.65)
        scroll_y = (slide_elapsed * v_speed) % max(1.0, float(span))
        base_top = sy1 + extra_pad - int(round(scroll_y))
        for ln, rel_y in zip(slide.lines, slide.line_ys):
            rgba, pad_l, pad_t = ln.get_rgba(global_elapsed)
            if rgba is None:
                continue
            if ln.align_h == "left":
                draw_x = sx0
            elif ln.align_h == "right":
                draw_x = sx1 - ln.ink_w
            else:
                draw_x = sx0 + (safe_w - ln.ink_w) // 2
            composite_rgba_onto_rgb(
                bg_frame,
                rgba,
                draw_x - pad_l + offset_x,
                base_top + rel_y - pad_t + offset_y,
                opacity=opacity,
                clip_rect=slide.safe_rect,
            )
        return

    # Synchronized group widths so multi-line blocks of unequal widths move together smoothly
    group_widths: Dict[str, int] = {}
    for motion_key in ("scroll_left", "scroll_right", "bounce"):
        widths = [ln.ink_w for ln in slide.lines if ln.motion == motion_key and ln.ink_w > 0]
        if widths:
            group_widths[motion_key] = max(widths)

    # Horizontal per-line motion (static, scroll_left, scroll_right, bounce)
    for ln, base_y in zip(slide.lines, slide.line_ys):
        rgba, pad_l, pad_t = ln.get_rgba(global_elapsed)
        if rgba is None:
            continue

        draw_y = base_y - pad_t + offset_y
        motion = ln.motion

        if motion == "scroll_left":
            block_w = group_widths.get("scroll_left", ln.ink_w)
            period = max(1, block_w + loop_gap)
            inner_x = (
                0
                if ln.align_h == "left"
                else (block_w - ln.ink_w)
                if ln.align_h == "right"
                else (block_w - ln.ink_w) // 2
            )
            # Start entering smoothly from right edge, then loop continuously
            shift = (slide_elapsed * speed) % period
            start_block_x = sx0 + safe_w - int(round(shift))
            first_block_x = start_block_x
            while first_block_x + block_w > sx0:
                first_block_x -= period
            block_x = first_block_x
            while block_x < sx1:
                composite_rgba_onto_rgb(
                    bg_frame,
                    rgba,
                    block_x + inner_x - pad_l + offset_x,
                    draw_y,
                    opacity=opacity,
                    clip_rect=slide.safe_rect,
                )
                block_x += period
        elif motion == "scroll_right":
            block_w = group_widths.get("scroll_right", ln.ink_w)
            period = max(1, block_w + loop_gap)
            inner_x = (
                0
                if ln.align_h == "left"
                else (block_w - ln.ink_w)
                if ln.align_h == "right"
                else (block_w - ln.ink_w) // 2
            )
            shift = (slide_elapsed * speed) % period
            start_block_x = sx0 - block_w + int(round(shift))
            first_block_x = start_block_x
            while first_block_x + block_w > sx0:
                first_block_x -= period
            block_x = first_block_x
            while block_x < sx1:
                composite_rgba_onto_rgb(
                    bg_frame,
                    rgba,
                    block_x + inner_x - pad_l + offset_x,
                    draw_y,
                    opacity=opacity,
                    clip_rect=slide.safe_rect,
                )
                block_x += period
        elif motion == "bounce":
            block_w = group_widths.get("bounce", ln.ink_w)
            inner_x = (
                0
                if ln.align_h == "left"
                else (block_w - ln.ink_w)
                if ln.align_h == "right"
                else (block_w - ln.ink_w) // 2
            )
            overflow = max(0, block_w - safe_w)
            if overflow <= 0:
                # Bounce gently inside safe area if block fits
                travel = max(0, safe_w - block_w)
                if travel == 0:
                    block_x = sx0
                else:
                    move_t = travel / max(8.0, speed * 0.75)
                    cycle = 2.0 * (move_t + pause_sec)
                    t = slide_elapsed % max(0.2, cycle)
                    if t < pause_sec:
                        frac = 0.0
                    elif t < pause_sec + move_t:
                        frac = (t - pause_sec) / max(0.01, move_t)
                    elif t < 2.0 * pause_sec + move_t:
                        frac = 1.0
                    else:
                        frac = 1.0 - (t - 2.0 * pause_sec - move_t) / max(0.01, move_t)
                    smooth_frac = 0.5 - 0.5 * math.cos(frac * math.pi)
                    block_x = sx0 + int(round(smooth_frac * travel))
            else:
                move_t = overflow / max(8.0, speed)
                cycle = 2.0 * (move_t + pause_sec)
                t = slide_elapsed % max(0.2, cycle)
                if t < pause_sec:
                    frac = 0.0
                elif t < pause_sec + move_t:
                    frac = (t - pause_sec) / max(0.01, move_t)
                elif t < 2.0 * pause_sec + move_t:
                    frac = 1.0
                else:
                    frac = 1.0 - (t - 2.0 * pause_sec - move_t) / max(0.01, move_t)
                smooth_frac = 0.5 - 0.5 * math.cos(frac * math.pi)
                block_x = sx0 - int(round(smooth_frac * overflow))
            composite_rgba_onto_rgb(
                bg_frame,
                rgba,
                block_x + inner_x - pad_l + offset_x,
                draw_y,
                opacity=opacity,
                clip_rect=slide.safe_rect,
            )
        else:
            # Static aligned
            if ln.align_h == "left":
                draw_x = sx0
            elif ln.align_h == "right":
                draw_x = sx1 - ln.ink_w
            else:
                draw_x = sx0 + (safe_w - ln.ink_w) // 2
            composite_rgba_onto_rgb(
                bg_frame,
                rgba,
                draw_x - pad_l + offset_x,
                draw_y,
                opacity=opacity,
                clip_rect=slide.safe_rect,
            )


def _render_marquee_frame(
    slides: List[_PreparedSlide],
    norm: Dict[str, Any],
    width: int,
    height: int,
    elapsed: float,
) -> np.ndarray:
    """Render a complete RGB frame at ``elapsed`` seconds."""
    bg_color = parse_hex_or_rgb(norm["bg_color"], (0, 0, 0))
    bg_color2 = parse_hex_or_rgb(norm["bg_color2"], (11, 20, 55))
    border_color = parse_hex_or_rgb(norm["border_color"], (255, 215, 0))

    frame = render_background_rgb(
        width,
        height,
        bg_type=norm["bg_type"],
        bg_color=bg_color,
        bg_color2=bg_color2,
        elapsed=elapsed,
    )

    if len(slides) == 1:
        _render_slide_frame(
            slides[0], norm, width, height, elapsed, elapsed, bg_frame=frame
        )
    else:
        slide_sec = max(1.0, float(norm["slide_sec"]))
        trans_dur = 0.0 if norm["transition"] == "cut" else min(0.55, slide_sec * 0.25)
        total_cycle = slide_sec * len(slides)
        pos = elapsed % total_cycle
        idx = int(pos // slide_sec) % len(slides)
        local_t = pos - idx * slide_sec
        next_idx = (idx + 1) % len(slides)

        if trans_dur > 0.0 and local_t > (slide_sec - trans_dur):
            prog = (local_t - (slide_sec - trans_dur)) / trans_dur
            eased = 0.5 - 0.5 * math.cos(prog * math.pi)
            trans = norm["transition"]
            if trans == "slide_left":
                dx = int(round(eased * width))
                _render_slide_frame(
                    slides[idx], norm, width, height, local_t, elapsed, bg_frame=frame, offset_x=-dx
                )
                _render_slide_frame(
                    slides[next_idx],
                    norm,
                    width,
                    height,
                    0.0,
                    elapsed,
                    bg_frame=frame,
                    offset_x=width - dx,
                )
            elif trans == "slide_up":
                dy = int(round(eased * height))
                _render_slide_frame(
                    slides[idx], norm, width, height, local_t, elapsed, bg_frame=frame, offset_y=-dy
                )
                _render_slide_frame(
                    slides[next_idx],
                    norm,
                    width,
                    height,
                    0.0,
                    elapsed,
                    bg_frame=frame,
                    offset_y=height - dy,
                )
            else:
                _render_slide_frame(
                    slides[idx],
                    norm,
                    width,
                    height,
                    local_t,
                    elapsed,
                    bg_frame=frame,
                    opacity=1.0 - eased,
                )
                _render_slide_frame(
                    slides[next_idx],
                    norm,
                    width,
                    height,
                    0.0,
                    elapsed,
                    bg_frame=frame,
                    opacity=eased,
                )
        else:
            _render_slide_frame(
                slides[idx], norm, width, height, local_t, elapsed, bg_frame=frame
            )

    draw_border_rgb(
        frame,
        border_style=norm["border"],
        border_color=border_color,
        elapsed=elapsed,
    )
    return frame


def _has_animation(slides: List[_PreparedSlide], norm: Dict[str, Any]) -> bool:
    if len(slides) > 1:
        return True
    if norm["bg_type"] == "starfield":
        return True
    if norm["border"] in ("chasing_bulbs", "neon_rainbow"):
        return True
    for sl in slides:
        if sl.vertical_scroll or sl.is_typewriter:
            return True
        for ln in sl.lines:
            if ln.motion != "static" or ln.is_animated_color:
                return True
    return False


def _has_dynamic_tokens(norm: Dict[str, Any]) -> bool:
    if norm["content_mode"] == "layers":
        return any("{" in str(ln.get("text") or "") for ln in norm["lines"] if isinstance(ln, dict))
    return "{" in norm["text"]


def _compute_preview_cycle_sec(slides: List[_PreparedSlide], norm: Dict[str, Any]) -> float:
    """Compute a natural full-loop preview duration so animations exit/complete cleanly."""
    if len(slides) > 1:
        return min(14.0, float(norm["slide_sec"]) * min(len(slides), 3))

    sl = slides[0]
    sx0, sy0, sx1, sy1 = sl.safe_rect
    safe_w = sx1 - sx0
    safe_h = sy1 - sy0
    speed = float(norm["speed"])
    loop_gap = int(norm["loop_gap"])
    pause_sec = float(norm["pause_sec"])

    if sl.vertical_scroll:
        extra_pad = max(
            norm["outline_width"],
            norm["glow"] * 2,
            1 if norm["shadow"] else 0,
        )
        span = sl.total_block_h + safe_h + loop_gap + extra_pad * 2
        v_speed = max(8.0, speed * 0.65)
        return max(2.0, min(24.0, span / v_speed))

    if sl.is_typewriter:
        total_chars = sum(len(ln.text) for ln in sl.lines)
        cps = max(4.0, speed * 0.45)
        return max(2.0, min(12.0, total_chars / cps + max(0.8, pause_sec) + 0.4))

    cycles: List[float] = []
    for motion_key in ("scroll_left", "scroll_right"):
        widths = [ln.ink_w for ln in sl.lines if ln.motion == motion_key and ln.ink_w > 0]
        if widths:
            period = max(1, max(widths) + loop_gap)
            cycles.append(min(14.0, period / max(6.0, speed)))

    bounce_widths = [ln.ink_w for ln in sl.lines if ln.motion == "bounce" and ln.ink_w > 0]
    if bounce_widths:
        block_w = max(bounce_widths)
        overflow = max(0, block_w - safe_w)
        travel = overflow if overflow > 0 else max(0, safe_w - block_w)
        move_t = travel / max(8.0, speed if overflow > 0 else speed * 0.75)
        cycles.append(min(14.0, 2.0 * (move_t + pause_sec)))

    if cycles:
        return max(1.0, max(cycles))
    return 3.5


def preview(
    effect_config: Optional[Dict[str, Any]],
    pixel_width: int,
    pixel_height: int,
) -> Dict[str, Any]:
    """Generic Studio preview hook: renders pixel-exact RGB frames + smart screen diagnostics."""
    width = max(8, min(256, int(pixel_width)))
    height = max(8, min(256, int(pixel_height)))
    norm = normalize_marquee_config(effect_config)
    slides, diagnostics, summary = _build_slides_and_diagnostics(norm, width, height)

    animated = _has_animation(slides, norm)
    if not animated:
        frame = _render_marquee_frame(slides, norm, width, height, 0.0)
        return {
            "width": width,
            "height": height,
            "fps": 1,
            "frames": [frame],
            "diagnostics": diagnostics,
            "summary": summary,
        }

    duration_sec = _compute_preview_cycle_sec(slides, norm)
    target_fps = 14 if duration_sec <= 8.0 else 10
    # Keep total raw RGB payload compact while covering the full animation cycle
    max_frames = 140 if (width * height) <= 10_000 else 64
    frame_count = max(16, min(max_frames, int(round(duration_sec * target_fps))))
    dt = duration_sec / frame_count

    frames = [
        _render_marquee_frame(slides, norm, width, height, i * dt)
        for i in range(frame_count)
    ]
    return {
        "width": width,
        "height": height,
        "fps": round(frame_count / duration_sec, 2),
        "frames": frames,
        "diagnostics": diagnostics,
        "summary": summary,
    }


def run(matrix, config):
    """Smart multi-line marquee with custom fonts, optical centering, visual styles, and slides."""
    width = max(8, int(config["pixel_width"]))
    height = max(8, int(config["pixel_height"]))
    color_order = str(config.get("color_order") or "rgb")
    norm = normalize_marquee_config(config.get("effect"))

    has_tokens = _has_dynamic_tokens(norm)
    last_token_sec = int(time.time())
    slides, _, _ = _build_slides_and_diagnostics(norm, width, height)

    start_time = time.monotonic()
    target_frame_ms = 33  # ~30 FPS smooth wall-clock pacing

    while matrix.ready():
        frame_start = time.monotonic()
        elapsed = frame_start - start_time

        if has_tokens:
            cur_sec = int(time.time())
            if cur_sec != last_token_sec:
                last_token_sec = cur_sec
                slides, _, _ = _build_slides_and_diagnostics(norm, width, height)

        rgb_frame = _render_marquee_frame(slides, norm, width, height, elapsed)
        out_frame = apply_color_order_array(rgb_frame, color_order)
        matrix.image(Image.fromarray(out_frame, mode="RGB"))

        render_ms = (time.monotonic() - frame_start) * 1000.0
        sleep_ms = max(1, int(round(target_frame_ms - render_ms)))
        matrix.show(delay_ms=sleep_ms)
