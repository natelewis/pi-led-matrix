"""Shimmering Northern Lights (Aurora Borealis) effect."""

import math
import time

import numpy as np
from PIL import Image


def run(matrix, config):
    """Shimmering Northern Lights curtains over a twinkling night sky."""
    width = max(1, int(config["pixel_width"]))
    height = max(1, int(config["pixel_height"]))
    effect_cfg = config.get("effect") or {}
    speed = 1.0
    if isinstance(effect_cfg, dict) and "speed" in effect_cfg:
        try:
            parsed = float(effect_cfg["speed"])
            if math.isfinite(parsed):
                speed = max(0.1, min(parsed, 5.0))
        except (TypeError, ValueError):
            pass
    show_stars = (
        bool(effect_cfg.get("stars", True)) if isinstance(effect_cfg, dict) else True
    )

    # Normalized coordinate grids (H, W)
    x = np.linspace(0.0, 1.0, width, dtype=np.float32)[None, :]
    y = np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None]

    # Deep arctic night sky backdrop (dark navy -> near-black horizon)
    sky_r = (3.0 + 9.0 * (1.0 - y) ** 2).astype(np.float32)
    sky_g = (6.0 + 14.0 * (1.0 - y) ** 2).astype(np.float32)
    sky_b = (16.0 + 28.0 * (1.0 - y) ** 1.5).astype(np.float32)

    # Subtle twinkling starfield in the upper 70% of the sky
    rng = np.random.default_rng(42)
    star_count = max(8, (width * height) // 260)
    star_y = rng.integers(0, max(1, int(height * 0.7)), size=star_count)
    star_x = rng.integers(0, width, size=star_count)
    star_phase = rng.uniform(0.0, 2.0 * np.pi, size=star_count).astype(np.float32)
    star_rate = rng.uniform(1.1, 3.2, size=star_count).astype(np.float32)

    start = time.monotonic()

    while matrix.ready():
        t = (time.monotonic() - start) * speed

        # Two overlapping flowing aurora ribbon ridges
        ridge1 = (
            0.52
            + 0.14 * np.sin(x * 5.2 + t * 0.65)
            + 0.07 * np.sin(x * 11.4 - t * 1.15)
            + 0.04 * np.cos(x * 2.8 + t * 0.35)
        )
        ridge2 = (
            0.36
            + 0.11 * np.sin(x * 4.1 - t * 0.52 + 1.4)
            + 0.06 * np.cos(x * 9.3 + t * 0.95)
        )

        # Vertical curtain glow: sharp lower edge, softly fading upward into the sky
        dy1 = ridge1 - y
        pos1 = np.maximum(dy1, 0.0)
        neg1 = np.minimum(dy1, 0.0)
        curtain1 = np.where(
            dy1 >= 0.0,
            np.exp(-pos1 * 4.4) * (1.0 - np.exp(-pos1 * 26.0)),
            np.exp(neg1 * 18.0) * 0.35,
        )

        dy2 = ridge2 - y
        pos2 = np.maximum(dy2, 0.0)
        neg2 = np.minimum(dy2, 0.0)
        curtain2 = np.where(
            dy2 >= 0.0,
            np.exp(-pos2 * 5.2) * (1.0 - np.exp(-pos2 * 22.0)),
            np.exp(neg2 * 16.0) * 0.25,
        )

        # Vertical shimmering rays dancing along the curtains
        rays1 = 0.62 + 0.38 * np.sin(x * 24.0 + np.sin(x * 6.0 + t * 0.8) * 2.2 - t * 1.7)
        rays2 = 0.58 + 0.42 * np.sin(x * 19.0 - np.cos(x * 5.0 - t * 0.7) * 1.9 + t * 1.3)

        glow1 = np.clip(curtain1 * rays1 * 1.55, 0.0, 1.3)
        glow2 = np.clip(curtain2 * rays2 * 1.15, 0.0, 1.1)

        # Color transitions with altitude above the curtain bottom edge:
        # emerald green at the base -> cyan/teal middle -> violet/magenta upper tips
        alt1 = np.clip(dy1 / 0.42, 0.0, 1.0)
        alt2 = np.clip(dy2 / 0.38, 0.0, 1.0)

        r = sky_r + glow1 * (30.0 + 185.0 * (alt1 ** 1.7)) + glow2 * (95.0 + 145.0 * alt2)
        g = sky_g + glow1 * (245.0 * (1.0 - 0.65 * alt1)) + glow2 * (190.0 * (1.0 - 0.55 * alt2))
        b = sky_b + glow1 * (115.0 + 130.0 * alt1) + glow2 * (175.0 + 75.0 * alt2)

        if show_stars:
            twinkle = 90.0 + 135.0 * (0.5 + 0.5 * np.sin(t * star_rate + star_phase))
            r[star_y, star_x] = np.maximum(r[star_y, star_x], twinkle * 0.85)
            g[star_y, star_x] = np.maximum(g[star_y, star_x], twinkle * 0.92)
            b[star_y, star_x] = np.maximum(b[star_y, star_x], twinkle)

        frame = np.stack(
            (
                np.clip(r, 0.0, 255.0),
                np.clip(g, 0.0, 255.0),
                np.clip(b, 0.0, 255.0),
            ),
            axis=-1,
        ).astype(np.uint8)

        matrix.image(Image.fromarray(frame, mode="RGB"))
        matrix.show()
