"""Swirling 6-fold crystalline snowflakes over a moonlit winter night."""

import math
import random
import time

import numpy as np
from PIL import Image

TWO_PI = 2.0 * math.pi
SIXTY_DEG = math.pi / 3.0
SQRT3_HALF = math.sqrt(3.0) * 0.5
ROTATION_STEPS = 15

# Curated color palettes tuned to look rich under default LED contrast/color enhancement
PALETTES = {
    "winter": {
        "sky_top": (3.0, 6.0, 18.0),
        "sky_bottom": (8.0, 16.0, 38.0),
        "tints": [
            (215.0, 240.0, 255.0),  # crisp ice white-blue
            (155.0, 220.0, 255.0),  # glacier cyan
            (190.0, 208.0, 255.0),  # frost periwinkle
            (242.0, 248.0, 255.0),  # pure snow white
            (135.0, 198.0, 255.0),  # Arctic sky blue
        ],
        "drift_crest": (222.0, 238.0, 255.0),
        "drift_shadow": (36.0, 68.0, 122.0),
    },
    "aurora": {
        "sky_top": (3.0, 8.0, 18.0),
        "sky_bottom": (8.0, 24.0, 38.0),
        "tints": [
            (170.0, 255.0, 232.0),  # mint frost
            (145.0, 224.0, 255.0),  # glacier cyan
            (196.0, 180.0, 255.0),  # polar violet
            (234.0, 252.0, 255.0),  # ice white
        ],
        "drift_crest": (205.0, 245.0, 242.0),
        "drift_shadow": (28.0, 72.0, 102.0),
    },
    "warm": {
        "sky_top": (7.0, 8.0, 18.0),
        "sky_bottom": (18.0, 18.0, 36.0),
        "tints": [
            (255.0, 244.0, 224.0),  # warm snow
            (255.0, 220.0, 178.0),  # champagne frost
            (225.0, 234.0, 255.0),  # silver frost
            (255.0, 234.0, 202.0),  # candlelight ivory
        ],
        "drift_crest": (244.0, 236.0, 224.0),
        "drift_shadow": (52.0, 58.0, 92.0),
    },
}


def _clamp_float(cfg, key, default, lo, hi):
    """Safely parse and clamp a finite float config option."""
    if not isinstance(cfg, dict) or key not in cfg:
        return default
    raw = cfg[key]
    if isinstance(raw, bool):
        return default
    try:
        val = float(raw)
        if math.isfinite(val):
            return max(lo, min(val, hi))
    except (TypeError, ValueError):
        pass
    return default


def _build_crystal_frame(size, angle, style, params, supersample=3):
    """Render one supersampled 6-fold symmetric crystalline snowflake frame.

    Returns (alpha, core) float32 arrays of shape (size, size) in [0, 1].
    Designed with airy negative space between arms so crystals stay crisp and
    lacy even on low-resolution LED matrices with high contrast enhancement.
    """
    ss = max(1, int(supersample))
    grid_n = size * ss
    coords = (np.arange(grid_n, dtype=np.float32) + 0.5) / (grid_n * 0.5) - 1.0
    gx, gy = np.meshgrid(coords, coords)

    ca = math.cos(angle)
    sa = math.sin(angle)
    rx = gx * ca + gy * sa
    ry = -gx * sa + gy * ca

    r = np.hypot(rx, ry)
    theta = np.arctan2(ry, rx)

    # Fold into fundamental 30-degree half-sector around the 6 main arms
    folded = np.abs(((theta + SIXTY_DEG * 0.5) % SIXTY_DEG) - SIXTY_DEG * 0.5)
    u = r * np.cos(folded)  # distance along nearest main arm
    v = r * np.sin(folded)  # perpendicular distance from nearest main arm

    px_step = 2.0 / max(1, size)
    spine_w = max(params["spine_w"], px_step * 0.42)
    branch_w = max(params["branch_w"], px_step * 0.38)

    # Slender tapered main 6 arms
    tip_len = params["tip_len"]
    taper = spine_w * (1.0 - 0.28 * np.clip(u / max(tip_len, 1e-4), 0.0, 1.0))
    shape = (u >= 0.0) & (u <= tip_len) & (v <= taper)

    # Small crisp hexagonal center jewel (kept compact so inner arms stay open)
    core_r = params["core_r"]
    shape |= u <= core_r

    # 60-degree crystal side-branches shared across styles
    for b_pos, b_len in params["branches"]:
        du = u - b_pos
        along = du * 0.5 + v * SQRT3_HALF
        perp = np.abs(-du * SQRT3_HALF + v * 0.5)
        shape |= (along >= 0.0) & (along <= b_len) & (perp <= branch_w)

    if style == "fern":
        # Tiny diamond tip at the end of each main arm
        tip_center = tip_len - 0.08
        shape |= (np.abs(u - tip_center) + 1.8 * v) <= max(0.095, px_step * 0.65)
    elif style == "ring":
        # Delicate open hexagonal web ring around the center
        ring_r = params["ring_r"]
        ring_w = max(params["ring_w"], px_step * 0.36)
        shape |= np.abs(u - ring_r) <= ring_w

    # Box-downsample and sharpen low-coverage tail so gaps stay genuinely dark
    alpha_hi = shape.astype(np.float32)
    raw_alpha = alpha_hi.reshape(size, ss, size, ss).mean(axis=(1, 3))
    alpha = np.clip((raw_alpha - 0.14) / 0.72, 0.0, 1.0)

    # Pure-white core & inner spine highlight fading to icy blue tips
    core_hi = (
        np.exp(-((r / max(core_r * 1.9, 0.20)) ** 2)) * 0.85
        + np.where(
            (u <= tip_len) & (v <= spine_w * 1.15),
            0.48 * (1.0 - 0.60 * np.clip(u / max(tip_len, 1e-4), 0.0, 1.0)),
            0.0,
        )
    ) * alpha_hi
    core = np.clip(
        core_hi.reshape(size, ss, size, ss).mean(axis=(1, 3)) * 1.25, 0.0, 1.0
    )

    return alpha.astype(np.float32), core.astype(np.float32)


def _generate_sprite_bank(base_scale):
    """Pre-generate rotated 6-fold crystal sprite frames for medium and hero tiers."""
    hero_sizes = [
        max(9, int(round(15 * base_scale)) | 1),
        max(9, int(round(17 * base_scale)) | 1),
        max(11, int(round(21 * base_scale)) | 1),
    ]
    mid_sizes = [
        max(7, int(round(9 * base_scale)) | 1),
        max(7, int(round(11 * base_scale)) | 1),
        max(9, int(round(13 * base_scale)) | 1),
    ]

    hero_specs = [
        # Ornate large stellar dendrite with generous open spacing
        (
            hero_sizes[2],
            "dendrite",
            {
                "spine_w": 0.048,
                "branch_w": 0.042,
                "tip_len": 0.94,
                "core_r": 0.13,
                "branches": [(0.36, 0.42), (0.66, 0.24)],
            },
        ),
        # Slender diamond-tipped fern star
        (
            hero_sizes[1],
            "fern",
            {
                "spine_w": 0.048,
                "branch_w": 0.042,
                "tip_len": 0.94,
                "core_r": 0.12,
                "branches": [(0.38, 0.36), (0.64, 0.20)],
            },
        ),
        # Open hexagonal web ring crystal with crisp corner chevrons
        (
            hero_sizes[1],
            "ring",
            {
                "spine_w": 0.050,
                "branch_w": 0.044,
                "tip_len": 0.94,
                "core_r": 0.11,
                "ring_r": 0.38,
                "ring_w": 0.048,
                "branches": [(0.66, 0.25)],
            },
        ),
        # Crisp medium-large V-tipped dendrite
        (
            hero_sizes[0],
            "dendrite",
            {
                "spine_w": 0.052,
                "branch_w": 0.045,
                "tip_len": 0.93,
                "core_r": 0.14,
                "branches": [(0.44, 0.36), (0.70, 0.18)],
            },
        ),
    ]

    mid_specs = [
        (
            mid_sizes[2],
            "dendrite",
            {
                "spine_w": 0.060,
                "branch_w": 0.052,
                "tip_len": 0.93,
                "core_r": 0.14,
                "branches": [(0.48, 0.34)],
            },
        ),
        (
            mid_sizes[1],
            "star",
            {
                "spine_w": 0.068,
                "branch_w": 0.056,
                "tip_len": 0.92,
                "core_r": 0.14,
                "branches": [(0.52, 0.30)],
            },
        ),
        (
            mid_sizes[0],
            "star",
            {
                "spine_w": 0.078,
                "branch_w": 0.062,
                "tip_len": 0.92,
                "core_r": 0.14,
                "branches": [(0.54, 0.26)],
            },
        ),
    ]

    angles = [i * (SIXTY_DEG / ROTATION_STEPS) for i in range(ROTATION_STEPS)]

    def build_group(specs):
        group = []
        for size, style, params in specs:
            frames = [
                _build_crystal_frame(size, ang, style, params, supersample=3)
                for ang in angles
            ]
            group.append({"size": size, "frames": frames})
        return group

    return build_group(hero_specs), build_group(mid_specs)


def _build_sky_backdrop(width, height, palette):
    """Precompute a velvety midnight winter sky gradient with subtle horizon glow."""
    y_norm = np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None]
    x_norm = np.linspace(0.0, 1.0, width, dtype=np.float32)[None, :]

    top = np.array(palette["sky_top"], dtype=np.float32)
    bot = np.array(palette["sky_bottom"], dtype=np.float32)

    grad = top[None, None, :] * (1.0 - y_norm[:, :, None]) + bot[None, None, :] * (
        y_norm[:, :, None] ** 1.35
    )

    # Very subtle horizon mist illumination along lower third
    horizon = np.exp(-(((y_norm - 0.88) / 0.22) ** 2)) * (
        0.75 + 0.25 * np.cos((x_norm - 0.5) * math.pi)
    )
    mist_col = np.array([bot[0] * 0.45, bot[1] * 0.50, bot[2] * 0.65], dtype=np.float32)
    sky = grad + horizon[:, :, None] * mist_col[None, None, :]
    return np.clip(sky, 0.0, 255.0).astype(np.float32)


def _stamp_crystal(canvas, cx, cy, alpha, core, tint, brightness, glint):
    """Blend a rotated crystalline snowflake cleanly onto the canvas."""
    h, w, _ = canvas.shape
    sh, sw = alpha.shape
    x0 = int(round(cx)) - sw // 2
    y0 = int(round(cy)) - sh // 2
    x1 = x0 + sw
    y1 = y0 + sh

    if x1 <= 0 or y1 <= 0 or x0 >= w or y0 >= h:
        return

    sx0 = max(0, -x0)
    sy0 = max(0, -y0)
    dx0 = max(0, x0)
    dy0 = max(0, y0)
    copy_w = min(x1, w) - dx0
    copy_h = min(y1, h) - dy0
    if copy_w <= 0 or copy_h <= 0:
        return

    a_patch = alpha[sy0 : sy0 + copy_h, sx0 : sx0 + copy_w]
    c_patch = core[sy0 : sy0 + copy_h, sx0 : sx0 + copy_w]

    # Icy tint on outer branches transitioning to crisp snow-white core + specular glint
    white_mix = np.clip(c_patch * (0.82 + 0.70 * glint), 0.0, 1.0)
    r_col = tint[0] + (255.0 - tint[0]) * white_mix
    g_col = tint[1] + (255.0 - tint[1]) * white_mix
    b_col = tint[2] + (255.0 - tint[2]) * white_mix

    cov = np.clip(a_patch * brightness * (1.0 + 0.25 * glint * c_patch), 0.0, 1.0)

    roi = canvas[dy0 : dy0 + copy_h, dx0 : dx0 + copy_w]
    # Standard alpha-over with subtle luminous lift so fading flakes vanish smoothly
    inv_a = 1.0 - cov * 0.85
    roi[:, :, 0] = np.minimum(255.0, roi[:, :, 0] * inv_a + r_col * cov)
    roi[:, :, 1] = np.minimum(255.0, roi[:, :, 1] * inv_a + g_col * cov)
    roi[:, :, 2] = np.minimum(255.0, roi[:, :, 2] * inv_a + b_col * cov)


def _stamp_micro_flake(canvas, x, y, kind, color, brightness):
    """Draw a delicate far-background 1px, 2px, or 3x3 micro ice crystal."""
    h, w, _ = canvas.shape
    ix = int(round(x))
    iy = int(round(y))
    if ix < -1 or ix > w or iy < -1 or iy > h:
        return

    r = color[0] * brightness
    g = color[1] * brightness
    b = color[2] * brightness

    def add_px(px, py, weight):
        if 0 <= px < w and 0 <= py < h:
            canvas[py, px, 0] = min(255.0, canvas[py, px, 0] + r * weight)
            canvas[py, px, 1] = min(255.0, canvas[py, px, 1] + g * weight)
            canvas[py, px, 2] = min(255.0, canvas[py, px, 2] + b * weight)

    if kind == 0:
        add_px(ix, iy, 1.0)
    elif kind == 1:
        add_px(ix, iy, 1.0)
        add_px(ix + 1, iy, 0.45)
        add_px(ix, iy + 1, 0.45)
    else:
        add_px(ix, iy, 1.0)
        add_px(ix - 1, iy, 0.55)
        add_px(ix + 1, iy, 0.55)
        add_px(ix, iy - 1, 0.55)
        add_px(ix, iy + 1, 0.55)


def _render_snowdrift(canvas, drift_height, palette, t, sparkles):
    """Render the rolling moonlit bottom snowbank and landing crystal glints."""
    h, w, _ = canvas.shape
    crest = np.array(palette["drift_crest"], dtype=np.float32)
    shadow = np.array(palette["drift_shadow"], dtype=np.float32)

    y_idx = np.arange(h, dtype=np.float32)[:, None]
    surface_y = float(h) - drift_height[None, :]
    depth = y_idx - surface_y

    cov = np.clip(depth + 0.65, 0.0, 1.0)
    if not np.any(cov > 0.0):
        return

    depth_norm = np.clip(depth / max(3.5, float(np.max(drift_height)) * 0.92), 0.0, 1.0)
    shade = 1.0 - (depth_norm**0.72)

    slope = np.gradient(drift_height) if w >= 2 else np.zeros_like(drift_height)
    moon_lit = np.clip(1.0 - slope * 0.35, 0.78, 1.15)[None, :]

    snow_r = (shadow[0] + (crest[0] - shadow[0]) * shade) * moon_lit
    snow_g = (shadow[1] + (crest[1] - shadow[1]) * shade) * moon_lit
    snow_b = (shadow[2] + (crest[2] - shadow[2]) * shade) * moon_lit

    inv_cov = 1.0 - cov
    canvas[:, :, 0] = np.clip(canvas[:, :, 0] * inv_cov + snow_r * cov, 0.0, 255.0)
    canvas[:, :, 1] = np.clip(canvas[:, :, 1] * inv_cov + snow_g * cov, 0.0, 255.0)
    canvas[:, :, 2] = np.clip(canvas[:, :, 2] * inv_cov + snow_b * cov, 0.0, 255.0)

    # Subtle ambient diamond-dust glints scattered along the snow crust
    rng_step = max(4, w // 18)
    for col in range(2, w - 2, rng_step):
        tw = math.sin(t * 2.4 + col * 1.37)
        if tw > 0.84:
            sy = int(round(h - drift_height[col] + 0.5))
            if 0 <= sy < h:
                boost = (tw - 0.84) / 0.16
                canvas[sy, col, 0] = min(255.0, canvas[sy, col, 0] + 115.0 * boost)
                canvas[sy, col, 1] = min(255.0, canvas[sy, col, 1] + 125.0 * boost)
                canvas[sy, col, 2] = min(255.0, canvas[sy, col, 2] + 140.0 * boost)

    # Active landing sparkles where flakes just settled into the snowbank
    for sp in sparkles:
        ix = int(round(sp["x"]))
        iy = int(round(sp["y"]))
        intensity = sp["life"] / sp["max_life"]
        glow = math.sin(intensity * math.pi)
        if 0 <= ix < w and 0 <= iy < h:
            canvas[iy, ix, 0] = min(255.0, canvas[iy, ix, 0] + 190.0 * glow)
            canvas[iy, ix, 1] = min(255.0, canvas[iy, ix, 1] + 220.0 * glow)
            canvas[iy, ix, 2] = min(255.0, canvas[iy, ix, 2] + 255.0 * glow)
            for ox, oy in ((-1, 0), (1, 0), (0, -1)):
                nx, ny = ix + ox, iy + oy
                if 0 <= nx < w and 0 <= ny < h:
                    canvas[ny, nx, 0] = min(255.0, canvas[ny, nx, 0] + 70.0 * glow)
                    canvas[ny, nx, 1] = min(255.0, canvas[ny, nx, 1] + 100.0 * glow)
                    canvas[ny, nx, 2] = min(255.0, canvas[ny, nx, 2] + 135.0 * glow)


def _pick_spaced_position(
    layer,
    width,
    height,
    size,
    existing,
    initial,
    slot_idx,
    slot_total,
    exclude=None,
):
    """Choose a spawn (x, y) that avoids bunching same-layer snowflakes together."""
    half = size * 0.5
    min_sep = size * (1.25 if layer == "hero" else 1.05)

    best_x = random.uniform(0.0, float(width))
    best_y = (
        random.uniform(-half * 0.3, height * 0.84)
        if initial
        else -half - random.uniform(0.0, size * 0.9)
    )

    if layer == "far" or not existing:
        return best_x, best_y

    best_dist = -1.0
    for attempt in range(8):
        if initial and attempt == 0 and slot_total > 0:
            # Stratified horizontal slot for balanced opening frame
            slot_w = width / float(slot_total)
            cand_x = (slot_idx + random.uniform(0.15, 0.85)) * slot_w
            cand_y = random.uniform(0.0, height * 0.82)
        else:
            cand_x = random.uniform(0.0, float(width))
            cand_y = (
                random.uniform(0.0, height * 0.82)
                if initial
                else -half - random.uniform(0.0, size * 0.9)
            )

        nearest = min(
            (
                math.hypot(cand_x - other["x"], cand_y - other["y"])
                for other in existing
                if other["layer"] == layer and other is not exclude
            ),
            default=9999.0,
        )
        if nearest >= min_sep:
            return cand_x, cand_y
        if nearest > best_dist:
            best_dist = nearest
            best_x, best_y = cand_x, cand_y

    return best_x, best_y


def _spawn_flake(
    layer,
    width,
    height,
    sprites,
    tints,
    existing=None,
    initial=False,
    slot_idx=0,
    slot_total=1,
    exclude=None,
):
    """Create a snowflake particle in the 'far', 'mid', or 'hero' depth layer."""
    if layer == "far":
        size = 3
        speed_y = random.uniform(4.2, 8.5) * (height / 72.0)
        sway_amp = random.uniform(1.5, 4.2)
        sway_freq = random.uniform(0.5, 1.2)
        sprite_idx = random.choice([0, 0, 1, 2])
        brightness = random.uniform(0.32, 0.62)
        spin_speed = 0.0
    elif layer == "mid":
        sprite_idx = random.randrange(len(sprites))
        size = sprites[sprite_idx]["size"]
        speed_y = random.uniform(8.5, 14.0) * (height / 72.0)
        sway_amp = random.uniform(3.0, 7.5)
        sway_freq = random.uniform(0.55, 1.25)
        brightness = random.uniform(0.68, 0.88)
        spin_speed = random.uniform(0.28, 0.72) * random.choice((-1.0, 1.0))
    else:  # hero foreground layer
        sprite_idx = random.randrange(len(sprites))
        size = sprites[sprite_idx]["size"]
        speed_y = random.uniform(12.0, 19.0) * (height / 72.0)
        sway_amp = random.uniform(4.5, 10.5)
        sway_freq = random.uniform(0.45, 1.0)
        brightness = random.uniform(0.90, 1.0)
        spin_speed = random.uniform(0.35, 0.90) * random.choice((-1.0, 1.0))

    x, y = _pick_spaced_position(
        layer,
        width,
        height,
        size,
        existing or [],
        initial,
        slot_idx,
        slot_total,
        exclude=exclude,
    )

    return {
        "layer": layer,
        "x": x,
        "y": y,
        "vy": speed_y,
        "sway_amp": sway_amp,
        "sway_freq": sway_freq,
        "sway_phase": random.uniform(0.0, TWO_PI),
        "angle": random.uniform(0.0, SIXTY_DEG),
        "spin": spin_speed,
        "glint_phase": random.uniform(0.0, TWO_PI),
        "shimmer_freq": random.uniform(1.2, 2.6),
        "sprite_idx": sprite_idx,
        "size": size,
        "tint": random.choice(tints),
        "brightness": brightness,
        "wind_factor": 0.45 if layer == "far" else (0.85 if layer == "mid" else 1.15),
    }


def run(matrix, config):
    """Swirling 6-fold crystalline snowflakes drifting through a moonlit winter night."""
    width = max(1, int(config["pixel_width"]))
    height = max(1, int(config["pixel_height"]))
    effect_cfg = config.get("effect") or {}

    speed = _clamp_float(effect_cfg, "speed", 1.0, 0.2, 3.0)
    wind_strength = _clamp_float(effect_cfg, "wind", 1.0, 0.0, 3.0)
    density = _clamp_float(effect_cfg, "density", 1.0, 0.3, 2.5)
    show_drift = (
        bool(effect_cfg.get("drift", True)) if isinstance(effect_cfg, dict) else True
    )
    palette_name = (
        str(effect_cfg.get("palette", "winter")).lower()
        if isinstance(effect_cfg, dict)
        else "winter"
    )
    palette = PALETTES.get(palette_name, PALETTES["winter"])

    # Scale crystals proportionally to display dimensions (1.0 at 128x72, capped for safety)
    base_scale = max(0.38, min(width / 128.0, height / 72.0, 2.5))
    hero_sprites, mid_sprites = _generate_sprite_bank(base_scale)
    sky_base = _build_sky_backdrop(width, height, palette)

    # Subtle high-altitude twinkling stars
    rng = np.random.default_rng(17)
    star_count = min(120, max(6, (width * height) // 360))
    star_x = rng.integers(0, width, size=star_count)
    star_y = rng.integers(0, max(1, int(height * 0.62)), size=star_count)
    star_phase = rng.uniform(0.0, TWO_PI, size=star_count).astype(np.float32)
    star_rate = rng.uniform(0.9, 2.4, size=star_count).astype(np.float32)

    # Balanced flake counts across 3 parallax layers (capped for large matrices)
    area_factor = (width * height) / (128.0 * 72.0)
    far_count = min(160, max(8, int(round(30 * area_factor * density))))
    mid_count = min(60, max(3, int(round(11 * area_factor * density))))
    hero_count = min(30, max(2, int(round(6 * area_factor * density))))

    tints = palette["tints"]
    flakes = []
    for i in range(far_count):
        flakes.append(
            _spawn_flake("far", width, height, None, tints, flakes, True, i, far_count)
        )
    for i in range(mid_count):
        flakes.append(
            _spawn_flake(
                "mid", width, height, mid_sprites, tints, flakes, True, i, mid_count
            )
        )
    for i in range(hero_count):
        flakes.append(
            _spawn_flake(
                "hero", width, height, hero_sprites, tints, flakes, True, i, hero_count
            )
        )

    # Organic rolling snowdrift heightfield at bottom of the matrix
    x_cols = np.linspace(0.0, TWO_PI, width, dtype=np.float32)
    base_drift_h = min(height * 0.22, max(1.0, height * 0.088))
    drift_target = (
        base_drift_h
        + (base_drift_h * 0.32) * np.cos(x_cols * 1.05 - 0.35)
        + (base_drift_h * 0.16) * np.sin(x_cols * 2.2 + 0.9)
    ).astype(np.float32)
    drift_height = drift_target.copy()
    max_drift_h = min(height * 0.35, max(2.0, height * 0.17))
    sparkles = []

    start_time = time.monotonic()
    last_time = start_time

    while matrix.ready():
        now = time.monotonic()
        dt = max(0.0, min(now - last_time, 0.12)) * speed
        last_time = now
        t = max(0.0, now - start_time) * speed

        # Smooth evolving breeze + occasional sweeping winter gusts
        gentle_breeze = math.sin(t * 0.28) * 6.5 + math.sin(t * 0.11 + 1.2) * 4.0
        gust_wave = max(0.0, math.sin(t * 0.19 - 0.7)) ** 4
        gust_dir = 1.0 if math.cos(t * 0.07) >= 0.0 else -1.0
        wind_vx = (
            (gentle_breeze + gust_dir * gust_wave * 18.0)
            * wind_strength
            * (width / 128.0)
        )

        canvas = sky_base.copy()

        # Subtle twinkling winter stars
        twinkle = 36.0 + 68.0 * (0.5 + 0.5 * np.sin(t * star_rate + star_phase))
        canvas[star_y, star_x, 0] = np.maximum(
            canvas[star_y, star_x, 0], twinkle * 0.82
        )
        canvas[star_y, star_x, 1] = np.maximum(
            canvas[star_y, star_x, 1], twinkle * 0.92
        )
        canvas[star_y, star_x, 2] = np.maximum(canvas[star_y, star_x, 2], twinkle)

        # Update and draw flakes back-to-front (far -> mid -> hero)
        for idx, flake in enumerate(flakes):
            layer = flake["layer"]
            sway_vx = (
                math.cos(t * flake["sway_freq"] + flake["sway_phase"])
                * flake["sway_amp"]
            )
            flake["x"] += (wind_vx * flake["wind_factor"] + sway_vx) * dt
            flake["y"] += flake["vy"] * dt
            gust_spin = 1.0 + 0.85 * gust_wave * wind_strength
            flake["angle"] = (
                flake["angle"] + flake["spin"] * gust_spin * dt
            ) % SIXTY_DEG

            half = flake["size"] * 0.5
            if flake["x"] < -half - 2.0:
                flake["x"] += width + flake["size"] + 4.0
            elif flake["x"] > width + half + 2.0:
                flake["x"] -= width + flake["size"] + 4.0

            col_idx = max(0, min(width - 1, int(round(flake["x"]))))
            ground_y = (
                float(height) - float(drift_height[col_idx])
                if show_drift
                else float(height) + half
            )

            landing_fade = 1.0
            if show_drift and layer != "far":
                sink = flake["y"] - (ground_y - half * 0.35)
                if sink > 0.0:
                    landing_fade = max(0.0, 1.0 - sink / max(2.5, half * 0.65))

            if flake["y"] > ground_y + (half * 0.45 if show_drift else half):
                if show_drift and layer != "far" and 0 <= col_idx < width:
                    add_h = 0.22 if layer == "hero" else 0.11
                    for dc, wt in (
                        (-2, 0.25),
                        (-1, 0.65),
                        (0, 1.0),
                        (1, 0.65),
                        (2, 0.25),
                    ):
                        nc = col_idx + dc
                        if 0 <= nc < width:
                            drift_height[nc] = min(
                                max_drift_h, drift_height[nc] + add_h * wt
                            )
                    if len(sparkles) < 16:
                        sparkles.append(
                            {
                                "x": float(col_idx),
                                "y": max(0.0, ground_y),
                                "life": 0.45,
                                "max_life": 0.45,
                            }
                        )
                sprites = mid_sprites if layer == "mid" else hero_sprites
                flakes[idx] = _spawn_flake(
                    layer,
                    width,
                    height,
                    sprites,
                    tints,
                    flakes,
                    initial=False,
                    exclude=flake,
                )
                continue

            if landing_fade <= 0.04:
                continue

            shimmer = 0.88 + 0.12 * math.sin(
                t * flake["shimmer_freq"] + flake["glint_phase"]
            )
            eff_brightness = flake["brightness"] * shimmer * landing_fade

            if layer == "far":
                _stamp_micro_flake(
                    canvas,
                    flake["x"],
                    flake["y"],
                    flake["sprite_idx"],
                    flake["tint"],
                    eff_brightness,
                )
            else:
                sprites = mid_sprites if layer == "mid" else hero_sprites
                sprite = sprites[flake["sprite_idx"]]
                frame_idx = (
                    int((flake["angle"] / SIXTY_DEG) * ROTATION_STEPS) % ROTATION_STEPS
                )
                alpha, core = sprite["frames"][frame_idx]
                glint = (
                    max(0.0, math.cos(flake["angle"] * 6.0 + flake["glint_phase"])) ** 6
                )
                _stamp_crystal(
                    canvas,
                    flake["x"],
                    flake["y"],
                    alpha,
                    core,
                    flake["tint"],
                    eff_brightness,
                    glint,
                )

        # Relax & smooth snowdrift so mounds stay softly rounded and balanced
        if show_drift:
            if width >= 3:
                smoothed = drift_height.copy()
                smoothed[1:-1] = (
                    0.2 * drift_height[:-2]
                    + 0.6 * drift_height[1:-1]
                    + 0.2 * drift_height[2:]
                )
                drift_height = drift_height + (smoothed - drift_height) * min(
                    1.0, dt * 1.4
                )
            drift_height += (drift_target - drift_height) * min(1.0, dt * 0.045)

            next_sparkles = []
            for sp in sparkles:
                sp["life"] -= dt
                if sp["life"] > 0.0:
                    next_sparkles.append(sp)
            sparkles = next_sparkles

            _render_snowdrift(canvas, drift_height, palette, t, sparkles)

        frame = np.clip(canvas, 0.0, 255.0).astype(np.uint8)
        matrix.image(Image.fromarray(frame, mode="RGB"))
        matrix.show()
