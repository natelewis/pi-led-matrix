"""Immersive 3D curving neon architectural hallway effect."""

import math
import time

import numpy as np
from PIL import Image

TWO_PI = 2.0 * math.pi
HALF_W = 1.0
HALF_H = 0.62
BAY_LEN = 2.35
MAX_DEPTH = 24.0
CHANNEL_INDEX = {"r": 0, "g": 1, "b": 2}

CONFIG_SCHEMA = [
    {
        "key": "theme",
        "label": "Theme",
        "type": "select",
        "default": "auto",
        "description": "Color mood for the corridor (Auto smoothly cycles through all themes).",
        "options": [
            {"value": "auto", "label": "Auto Cycle"},
            {"value": "cyber", "label": "Cyber"},
            {"value": "synthwave", "label": "Synthwave"},
            {"value": "crimson", "label": "Crimson"},
            {"value": "gold", "label": "Gold"},
            {"value": "emerald", "label": "Emerald"},
        ],
    },
    {
        "key": "speed",
        "label": "Travel Speed",
        "type": "number",
        "default": 1.0,
        "min": 0.2,
        "max": 3.0,
        "step": 0.1,
        "unit": "×",
    },
    {
        "key": "curve",
        "label": "Curve Intensity",
        "type": "number",
        "default": 1.0,
        "min": 0.0,
        "max": 2.0,
        "step": 0.1,
        "description": "Set to 0 for a straight hallway, or higher for dramatic sweeping turns.",
    },
    {
        "key": "pulse",
        "label": "Traveling Energy Pulses",
        "type": "boolean",
        "default": True,
        "description": "Send periodic waves of light racing down the corridor arches.",
    },
    {
        "key": "motes",
        "label": "Floating Light Motes",
        "type": "boolean",
        "default": True,
        "description": "Subtle 3D light particles drifting past the camera.",
    },
]

# Curated architectural color moods tuned for LED contrast=2.0 / color=1.5
THEMES = {
    "cyber": {
        "wall_base": (18.0, 26.0, 48.0),
        "wall_lit": (48.0, 82.0, 128.0),
        "ceil_base": (14.0, 20.0, 40.0),
        "floor_base": (14.0, 18.0, 36.0),
        "rib_core": (92.0, 244.0, 255.0),
        "rib_glow": (22.0, 138.0, 198.0),
        "accent": (255.0, 68.0, 172.0),
        "ceil_light": (226.0, 246.0, 255.0),
        "fog": (36.0, 68.0, 126.0),
        "portal": (148.0, 224.0, 255.0),
        "pulse": (255.0, 118.0, 220.0),
    },
    "synthwave": {
        "wall_base": (28.0, 16.0, 52.0),
        "wall_lit": (76.0, 38.0, 118.0),
        "ceil_base": (20.0, 14.0, 42.0),
        "floor_base": (18.0, 12.0, 38.0),
        "rib_core": (255.0, 76.0, 212.0),
        "rib_glow": (168.0, 34.0, 172.0),
        "accent": (56.0, 238.0, 255.0),
        "ceil_light": (255.0, 218.0, 148.0),
        "fog": (102.0, 36.0, 136.0),
        "portal": (255.0, 162.0, 112.0),
        "pulse": (82.0, 246.0, 255.0),
    },
    "crimson": {
        "wall_base": (32.0, 16.0, 22.0),
        "wall_lit": (84.0, 32.0, 40.0),
        "ceil_base": (24.0, 14.0, 18.0),
        "floor_base": (20.0, 12.0, 18.0),
        "rib_core": (255.0, 58.0, 48.0),
        "rib_glow": (182.0, 24.0, 30.0),
        "accent": (255.0, 164.0, 54.0),
        "ceil_light": (255.0, 234.0, 216.0),
        "fog": (102.0, 24.0, 30.0),
        "portal": (255.0, 142.0, 96.0),
        "pulse": (255.0, 202.0, 108.0),
    },
    "gold": {
        "wall_base": (34.0, 24.0, 20.0),
        "wall_lit": (92.0, 66.0, 42.0),
        "ceil_base": (26.0, 20.0, 18.0),
        "floor_base": (22.0, 18.0, 16.0),
        "rib_core": (255.0, 204.0, 108.0),
        "rib_glow": (182.0, 124.0, 46.0),
        "accent": (255.0, 132.0, 68.0),
        "ceil_light": (255.0, 244.0, 216.0),
        "fog": (96.0, 64.0, 38.0),
        "portal": (255.0, 226.0, 162.0),
        "pulse": (255.0, 236.0, 168.0),
    },
    "emerald": {
        "wall_base": (14.0, 30.0, 34.0),
        "wall_lit": (34.0, 92.0, 88.0),
        "ceil_base": (12.0, 24.0, 30.0),
        "floor_base": (10.0, 22.0, 26.0),
        "rib_core": (68.0, 255.0, 192.0),
        "rib_glow": (22.0, 158.0, 122.0),
        "accent": (92.0, 212.0, 255.0),
        "ceil_light": (222.0, 255.0, 242.0),
        "fog": (28.0, 88.0, 84.0),
        "portal": (144.0, 255.0, 216.0),
        "pulse": (168.0, 255.0, 132.0),
    },
}

CYCLE_ORDER = ("cyber", "synthwave", "crimson", "gold", "emerald")
THEME_KEYS = tuple(THEMES["cyber"].keys())


def _clamp_float(cfg, key, default, low, high):
    """Safely parse and clamp a finite float config option."""
    if not isinstance(cfg, dict) or key not in cfg or isinstance(cfg[key], bool):
        return default
    try:
        val = float(cfg[key])
        if math.isfinite(val):
            return max(low, min(val, high))
    except (TypeError, ValueError):
        pass
    return default


def _parse_bool(cfg, key, default):
    """Safely parse a boolean config option."""
    if not isinstance(cfg, dict) or key not in cfg:
        return default
    val = cfg[key]
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() not in ("0", "false", "no", "off")
    return bool(val)


def _theme_arrays(theme_dict):
    """Convert a theme dictionary of RGB tuples into float32 arrays."""
    return {key: np.array(val, dtype=np.float32) for key, val in theme_dict.items()}


def _blend_themes(theme_a, theme_b, mix):
    """Linearly interpolate two theme dictionaries."""
    inv = np.float32(1.0 - mix)
    weight = np.float32(mix)
    return {key: theme_a[key] * inv + theme_b[key] * weight for key in THEME_KEYS}


def _select_cycled_theme(theme_bank, elapsed):
    """Hold each curated color mood briefly, then cross-fade smoothly to the next."""
    hold_sec = 10.0
    fade_sec = 4.0
    slot_sec = hold_sec + fade_sec
    total = len(CYCLE_ORDER)
    pos = (elapsed / slot_sec) % total
    idx_a = int(pos)
    idx_b = (idx_a + 1) % total
    within = (pos - idx_a) * slot_sec
    if within <= hold_sec:
        return theme_bank[CYCLE_ORDER[idx_a]]
    mix = (within - hold_sec) / fade_sec
    mix = mix * mix * (3.0 - 2.0 * mix)
    return _blend_themes(
        theme_bank[CYCLE_ORDER[idx_a]], theme_bank[CYCLE_ORDER[idx_b]], mix
    )


def _solve_curved_plane(accel, ray, offset):
    """Return smallest positive root depth of accel*z^2 - ray*z + offset = 0."""
    inf = np.float32(1e6)
    if abs(accel) < 1e-6:
        valid = np.abs(ray) > 1e-7
        safe_ray = np.where(valid, ray, np.float32(1.0))
        depth = np.where(valid, offset / safe_ray, inf)
        return np.where(depth > 1e-4, depth, inf)

    disc = ray * ray - np.float32(4.0 * accel * offset)
    has_hit = disc >= 0.0
    sqrt_d = np.sqrt(np.maximum(disc, np.float32(0.0)))
    sign_r = np.where(ray >= 0.0, np.float32(1.0), np.float32(-1.0))
    quad = np.float32(0.5) * (ray + sign_r * sqrt_d)

    root1 = quad / np.float32(accel)
    valid_q = np.abs(quad) > 1e-7
    safe_q = np.where(valid_q, quad, np.float32(1.0))
    root2 = np.where(valid_q, np.float32(offset) / safe_q, inf)

    root1 = np.where(has_hit & (root1 > 1e-4), root1, inf)
    root2 = np.where(has_hit & (root2 > 1e-4), root2, inf)
    return np.minimum(root1, root2)


def _smooth_band(dist, half_width, aa_width):
    """Distance-aware anti-aliased band profile in [0, 1]."""
    return np.clip((half_width + aa_width - dist) / (2.0 * aa_width), 0.0, 1.0)


def _build_ray_grid(width, height):
    """Precompute aspect-correct camera ray directions for the matrix."""
    aspect = width / max(float(height), 1.0)
    focal = 1.32 if aspect >= 1.35 else max(0.85, aspect * 0.98)

    xs = ((np.arange(width, dtype=np.float32) + 0.5) - width * 0.5) / (
        height * 0.5 * focal
    )
    ys = ((np.arange(height, dtype=np.float32) + 0.5) - height * 0.5) / (
        height * 0.5 * focal
    )
    base_rx, base_ry = np.meshgrid(xs, ys)
    return base_rx.astype(np.float32), base_ry.astype(np.float32), focal


def _camera_pose(elapsed, curve_strength):
    """Compute smooth corridor curvature, camera banking, and subtle glide bob."""
    wave_x = 0.68 * math.sin(elapsed * 0.31) + 0.32 * math.sin(elapsed * 0.71 + 0.9)
    bend_x = math.copysign(abs(wave_x) ** 1.35, wave_x) * 0.036 * curve_strength
    bend_y = (
        (0.60 * math.sin(elapsed * 0.23 + 0.6) + 0.40 * math.cos(elapsed * 0.49))
        * 0.011
        * curve_strength
    )
    roll = -bend_x * 3.4
    cos_r = np.float32(math.cos(roll))
    sin_r = np.float32(math.sin(roll))
    sway_scale = min(1.0, curve_strength + 0.3)
    cam_x = -bend_x * 3.2 + 0.055 * math.sin(elapsed * 0.82) * sway_scale
    cam_y = 0.032 * math.sin(elapsed * 2.1)
    return cam_x, cam_y, bend_x, bend_y, cos_r, sin_r


def _init_motes(count):
    """Create drifting 3D light motes floating down the corridor."""
    rng = np.random.default_rng(73)
    return {
        "x": rng.uniform(-HALF_W * 0.82, HALF_W * 0.82, size=count).astype(np.float32),
        "y": rng.uniform(-HALF_H * 0.76, HALF_H * 0.76, size=count).astype(np.float32),
        "z": rng.uniform(1.2, 15.0, size=count).astype(np.float32),
        "speed": rng.uniform(0.75, 1.35, size=count).astype(np.float32),
        "phase": rng.uniform(0.0, TWO_PI, size=count).astype(np.float32),
        "tint": rng.uniform(0.0, 1.0, size=count).astype(np.float32),
    }


def _render_motes(canvas, motes, depth_buf, width, height, focal, pose, theme, elapsed):
    """Project and blend drifting 3D light particles inside the curved corridor."""
    cam_x, cam_y, bend_x, bend_y, cos_r, sin_r = pose
    half_w_px = width * 0.5
    half_h_px = height * 0.5
    scale_px = half_h_px * focal
    rib_c = theme["rib_core"]
    acc_c = theme["accent"]

    for i in range(len(motes["z"])):
        mote_z = float(motes["z"][i])
        if mote_z <= 0.45 or mote_z >= 14.0:
            continue

        phase = float(motes["phase"][i])
        drift_x = float(motes["x"][i]) + 0.08 * math.sin(elapsed * 1.4 + phase)
        drift_y = float(motes["y"][i]) + 0.05 * math.cos(elapsed * 1.1 + phase)
        world_x = drift_x + cam_x + bend_x * mote_z * mote_z
        world_y = drift_y + cam_y + bend_y * mote_z * mote_z

        ray_x = world_x / mote_z
        ray_y = world_y / mote_z
        screen_rx = ray_x * float(cos_r) + ray_y * float(sin_r)
        screen_ry = -ray_x * float(sin_r) + ray_y * float(cos_r)

        px = int(round(screen_rx * scale_px + half_w_px - 0.5))
        py = int(round(screen_ry * scale_px + half_h_px - 0.5))
        if px < 0 or px >= width or py < 0 or py >= height:
            continue
        if mote_z > float(depth_buf[py, px]) + 0.20:
            continue

        twinkle = 0.70 + 0.30 * math.sin(elapsed * 4.0 + phase)
        fade = math.exp(-mote_z * 0.22) * min(1.0, (mote_z - 0.45) / 0.85) * twinkle
        mix = float(motes["tint"][i])
        col = (rib_c * (1.0 - mix) + acc_c * mix) * 0.72 + 58.0

        canvas[py, px] = np.minimum(255.0, canvas[py, px] + col * fade * 0.88)
        if mote_z < 4.5:
            halo = col * fade * 0.28
            for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nx, ny = px + ox, py + oy
                if 0 <= nx < width and 0 <= ny < height:
                    canvas[ny, nx] = np.minimum(255.0, canvas[ny, nx] + halo)


def _raycast_corridor(base_rx, base_ry, pose):
    """Analytically intersect camera rays with the curved rectangular corridor."""
    cam_x, cam_y, bend_x, bend_y, cos_r, sin_r = pose
    rx = base_rx * cos_r - base_ry * sin_r
    ry = base_rx * sin_r + base_ry * cos_r

    z_right = _solve_curved_plane(bend_x, rx, cam_x + HALF_W)
    z_left = _solve_curved_plane(bend_x, rx, cam_x - HALF_W)
    z_floor = _solve_curved_plane(bend_y, ry, cam_y + HALF_H)
    z_ceil = _solve_curved_plane(bend_y, ry, cam_y - HALF_H)

    z_wall = np.minimum(z_left, z_right)
    z_horz = np.minimum(z_floor, z_ceil)
    depth = np.minimum(np.minimum(z_wall, z_horz), np.float32(MAX_DEPTH))

    is_wall = z_wall <= z_horz
    is_floor = (~is_wall) & (z_floor <= z_ceil)
    is_ceil = (~is_wall) & (~is_floor)

    wx = rx * depth - (cam_x + bend_x * depth * depth)
    wy = ry * depth - (cam_y + bend_y * depth * depth)
    u_x = np.clip(wx / np.float32(HALF_W), -1.0, 1.0)
    u_y = np.clip(wy / np.float32(HALF_H), -1.0, 1.0)

    return {
        "depth": depth,
        "is_wall": is_wall,
        "is_floor": is_floor,
        "is_ceil": is_ceil,
        "u_x": u_x,
        "u_y": u_y,
    }


def _shade_base_surfaces(geom, fields, theme):
    """Shade corridor walls, ceiling, and floor with corner AO and panel seams."""
    u_x = geom["u_x"]
    u_y = geom["u_y"]
    mid_dist = fields["mid_dist"]
    light_pool = fields["light_pool"]
    aa_z = fields["aa_z"]
    detail_lod = fields["detail_lod"]

    wall_ao = np.float32(1.0) - np.float32(0.48) * (u_y * u_y * u_y * u_y)
    wall_top_lit = np.clip((np.float32(0.75) - u_y) * np.float32(0.68), 0.0, 1.0)
    wall_light = (
        np.float32(0.16) + np.float32(0.88) * light_pool * wall_top_lit
    ) * wall_ao

    seam_v = _smooth_band(np.abs(mid_dist - np.float32(0.24)), np.float32(0.011), aa_z)
    seam_h = _smooth_band(
        np.abs(u_y + np.float32(0.38)), np.float32(0.016), np.float32(0.024)
    )
    wall_seam = (
        np.maximum(seam_v, seam_h * np.float32(0.75)) * detail_lod * np.float32(0.34)
    )
    wall_shade = np.clip(wall_light * (np.float32(1.0) - wall_seam), 0.0, 1.25)

    ceil_ao = np.float32(1.0) - np.float32(0.42) * (u_x * u_x * u_x * u_x)
    floor_ao = np.float32(1.0) - np.float32(0.38) * (u_x * u_x * u_x * u_x)

    tile_x_dist = np.abs(np.abs(u_x) - np.float32(0.56))
    tile_line = (
        np.maximum(
            _smooth_band(tile_x_dist, np.float32(0.016), np.float32(0.026)),
            _smooth_band(mid_dist, np.float32(0.013), aa_z) * np.float32(0.60),
        )
        * detail_lod
        * np.float32(0.35)
    )

    height, width = geom["depth"].shape
    canvas = np.empty((height, width, 3), dtype=np.float32)

    wall_col = (
        theme["wall_base"][None, None, :] * (np.float32(1.0) - wall_shade[:, :, None])
        + theme["wall_lit"][None, None, :] * wall_shade[:, :, None]
    )
    ceil_col = (
        theme["ceil_base"][None, None, :]
        * (np.float32(0.68) + np.float32(0.58) * light_pool[:, :, None])
        * ceil_ao[:, :, None]
    )
    floor_col = (
        theme["floor_base"][None, None, :]
        * (np.float32(0.74) + np.float32(0.45) * light_pool[:, :, None])
        * floor_ao[:, :, None]
        * (np.float32(1.0) - tile_line[:, :, None])
    )

    canvas[geom["is_wall"]] = wall_col[geom["is_wall"]]
    canvas[geom["is_ceil"]] = ceil_col[geom["is_ceil"]]
    canvas[geom["is_floor"]] = floor_col[geom["is_floor"]]

    rib_shell = _smooth_band(fields["rib_dist"], np.float32(0.070), aa_z)
    bulkhead_dim = np.float32(1.0) - rib_shell * np.float32(0.52) * detail_lod
    canvas *= bulkhead_dim[:, :, None]
    return canvas


def _add_emissive_architecture(canvas, geom, fields, theme):
    """Add ceiling light panels, wall accent rails, and glowing portal arch ribs."""
    u_x = geom["u_x"]
    u_y = geom["u_y"]
    is_wall = geom["is_wall"]
    is_ceil = geom["is_ceil"]
    is_floor = geom["is_floor"]
    mid_dist = fields["mid_dist"]
    rib_dist = fields["rib_dist"]
    aa_z = fields["aa_z"]
    emissive_lod = fields["emissive_lod"]
    energy_wave = fields["energy_wave"]

    # Recessed overhead ceiling light fixtures
    ceil_fix_x = _smooth_band(np.abs(u_x), np.float32(0.36), np.float32(0.065))
    ceil_fix_z = _smooth_band(mid_dist, np.float32(0.17), aa_z)
    ceil_core_x = _smooth_band(np.abs(u_x), np.float32(0.24), np.float32(0.08))
    ceil_panel = (
        np.where(is_ceil, ceil_fix_x * ceil_fix_z, np.float32(0.0)) * emissive_lod
    )
    ceil_hot = ceil_panel * ceil_core_x
    ceil_bloom = (
        np.where(
            is_ceil,
            np.exp(-((u_x / np.float32(0.58)) ** 2))
            * np.exp(-((mid_dist / np.float32(0.33)) ** 2))
            * np.float32(0.45),
            np.float32(0.0),
        )
        * emissive_lod
    )
    canvas += (
        ceil_panel[:, :, None] * theme["rib_core"][None, None, :] * np.float32(0.42)
        + ceil_hot[:, :, None] * theme["ceil_light"][None, None, :] * np.float32(0.85)
        + ceil_bloom[:, :, None] * theme["rib_glow"][None, None, :] * np.float32(0.52)
    )

    # Wall accent sconce rails & baseboard guide strips
    rail_gap = _smooth_band(mid_dist, np.float32(0.31), aa_z)
    mid_rail = (
        _smooth_band(
            np.abs(u_y - np.float32(0.14)), np.float32(0.036), np.float32(0.044)
        )
        * rail_gap
        * emissive_lod
    )
    mid_rail_glow = (
        np.exp(-(((u_y - np.float32(0.14)) / np.float32(0.20)) ** 2))
        * rail_gap
        * emissive_lod
    )
    base_strip = (
        _smooth_band(
            np.abs(u_y - np.float32(0.88)), np.float32(0.028), np.float32(0.042)
        )
        * emissive_lod
    )
    rail_boost = np.float32(1.0) + energy_wave * np.float32(0.42)
    canvas += (
        np.where(is_wall, mid_rail, np.float32(0.0))[:, :, None]
        * (theme["accent"][None, None, :] * rail_boost[:, :, None] + np.float32(20.0))
        + np.where(is_wall, mid_rail_glow, np.float32(0.0))[:, :, None]
        * theme["accent"][None, None, :]
        * np.float32(0.26)
        + np.where(is_wall, base_strip, np.float32(0.0))[:, :, None]
        * theme["rib_core"][None, None, :]
        * np.float32(0.55)
    )

    # Portal arch ribs wrapping left wall, ceiling, and right wall
    rib_core = _smooth_band(rib_dist, np.float32(0.022), aa_z * np.float32(0.85))
    rib_halo = np.exp(-((rib_dist / (np.float32(0.068) + aa_z * np.float32(0.5))) ** 2))
    floor_anchor = np.clip(
        (np.abs(u_x) - np.float32(0.76)) / np.float32(0.24), 0.0, 1.0
    )
    rib_weight = np.where(
        is_floor, floor_anchor * floor_anchor * np.float32(0.65), np.float32(1.0)
    )
    pulse_mix = energy_wave[:, :, None] * np.float32(0.78)
    rib_color = (
        theme["rib_core"][None, None, :] * (np.float32(1.0) - pulse_mix)
        + theme["pulse"][None, None, :] * pulse_mix
    )
    rib_gain = np.float32(0.92) + energy_wave[:, :, None] * np.float32(0.30)
    canvas += (rib_core * rib_weight * emissive_lod)[:, :, None] * (
        rib_color * rib_gain
    ) + (rib_halo * rib_weight * emissive_lod * np.float32(0.46))[:, :, None] * theme[
        "rib_glow"
    ][
        None, None, :
    ]
    return rail_gap, rib_halo, rib_color


def _add_floor_reflections_and_fog(
    canvas, geom, fields, rail_gap, rib_halo, rib_color, theme, elapsed
):
    """Add polished floor reflections, runway guides, atmospheric fog, and portal glow."""
    depth = geom["depth"]
    u_x = geom["u_x"]
    is_floor = geom["is_floor"]
    mid_dist = fields["mid_dist"]
    light_pool = fields["light_pool"]
    detail_lod = fields["detail_lod"]
    emissive_lod = fields["emissive_lod"]
    energy_wave = fields["energy_wave"]

    fresnel = np.clip(np.float32(0.30) + depth * np.float32(0.055), 0.0, 0.92)
    refl_ceil = (
        np.where(
            is_floor,
            np.exp(-((u_x / np.float32(0.40)) ** 2))
            * np.exp(-((mid_dist / np.float32(0.29)) ** 2))
            * fresnel
            * np.float32(0.68),
            np.float32(0.0),
        )
        * emissive_lod
    )
    edge_prox = np.clip((np.abs(u_x) - np.float32(0.38)) / np.float32(0.62), 0.0, 1.0)
    refl_wall = (
        np.where(
            is_floor,
            (edge_prox * edge_prox)
            * (np.float32(0.34) + np.float32(0.66) * rail_gap)
            * np.float32(0.48),
            np.float32(0.0),
        )
        * emissive_lod
    )
    refl_rib = (
        np.where(
            is_floor,
            (edge_prox * edge_prox) * rib_halo * np.float32(0.36),
            np.float32(0.0),
        )
        * emissive_lod
    )
    runway_dist = np.abs(np.abs(u_x) - np.float32(0.19))
    runway_energy = (
        np.float32(0.42)
        + np.float32(0.58) * light_pool
        + energy_wave * np.float32(0.60)
    )
    runway = np.where(
        is_floor,
        _smooth_band(runway_dist, np.float32(0.014), np.float32(0.025))
        * runway_energy
        * detail_lod
        * np.float32(0.55),
        np.float32(0.0),
    )

    canvas += (
        refl_ceil[:, :, None] * theme["ceil_light"][None, None, :]
        + refl_wall[:, :, None] * theme["accent"][None, None, :]
        + refl_rib[:, :, None] * rib_color
        + runway[:, :, None] * rib_color
    )

    fog = np.float32(1.0) - np.exp(-depth * np.float32(0.155))
    portal_strength = np.clip((depth - np.float32(6.5)) / np.float32(10.5), 0.0, 1.0)
    portal_glow = (portal_strength * portal_strength) * (
        np.float32(0.84) + np.float32(0.16) * math.sin(elapsed * 1.15)
    )
    fog_col = (
        theme["fog"][None, None, :] * (np.float32(1.0) - portal_glow[:, :, None])
        + theme["portal"][None, None, :] * portal_glow[:, :, None]
    )
    return canvas * (np.float32(1.0) - fog[:, :, None]) + fog_col * fog[:, :, None]


def _shade_hallway(base_rx, base_ry, travel, elapsed, pose, theme, enable_pulse):
    """Evaluate the curved 3D corridor shader and return (canvas_f32, depth_buf)."""
    geom = _raycast_corridor(base_rx, base_ry, pose)
    depth = geom["depth"]

    world_z = depth + np.float32(travel)
    bay_phase = np.mod(world_z, np.float32(BAY_LEN)) / np.float32(BAY_LEN)
    rib_dist = np.minimum(bay_phase, np.float32(1.0) - bay_phase)
    mid_dist = np.abs(bay_phase - np.float32(0.5))

    aa_z = np.clip(depth * np.float32(0.018), np.float32(0.012), np.float32(0.22))
    detail_lod = np.exp(-depth * np.float32(0.15))
    emissive_lod = np.exp(
        -np.maximum(depth - np.float32(3.5), np.float32(0.0)) * np.float32(0.14)
    )

    if enable_pulse:
        wave_span = np.float32(BAY_LEN * 5.0)
        wave_cycle = np.mod(world_z - np.float32(travel * 2.6 + 1.5), wave_span)
        wave_dist = np.minimum(wave_cycle, wave_span - wave_cycle)
        energy_wave = np.exp(-((wave_dist / np.float32(1.45)) ** 2))
    else:
        energy_wave = np.zeros_like(depth)

    fields = {
        "rib_dist": rib_dist,
        "mid_dist": mid_dist,
        "aa_z": aa_z,
        "detail_lod": detail_lod,
        "emissive_lod": emissive_lod,
        "energy_wave": energy_wave,
        "light_pool": np.exp(-((mid_dist / np.float32(0.31)) ** 2)),
    }

    canvas = _shade_base_surfaces(geom, fields, theme)
    rail_gap, rib_halo, rib_color = _add_emissive_architecture(
        canvas, geom, fields, theme
    )
    canvas = _add_floor_reflections_and_fog(
        canvas, geom, fields, rail_gap, rib_halo, rib_color, theme, elapsed
    )
    return canvas, depth


def run(matrix, config):
    """Immersive 3D curving neon hallway with reflective floors and traveling light pulses."""
    width = max(1, int(config["pixel_width"]))
    height = max(1, int(config["pixel_height"]))
    effect_cfg = config.get("effect") or {}

    speed = _clamp_float(effect_cfg, "speed", 1.0, 0.2, 3.0)
    curve_strength = _clamp_float(effect_cfg, "curve", 1.0, 0.0, 2.0)
    enable_pulse = _parse_bool(effect_cfg, "pulse", True)
    enable_motes = _parse_bool(effect_cfg, "motes", True)

    theme_name = (
        str(effect_cfg.get("theme", effect_cfg.get("palette", "auto"))).strip().lower()
        if isinstance(effect_cfg, dict)
        else "auto"
    )
    cycle_mode = theme_name in ("auto", "cycle")
    theme_bank = {name: _theme_arrays(vals) for name, vals in THEMES.items()}
    fixed_theme = theme_bank.get(theme_name, theme_bank["cyber"])

    color_order = str(config.get("color_order", "rgb")).lower()
    channel_idx = (
        [CHANNEL_INDEX[ch] for ch in color_order]
        if color_order != "rgb"
        and len(color_order) == 3
        and set(color_order) == {"r", "g", "b"}
        else None
    )

    base_rx, base_ry, focal = _build_ray_grid(width, height)
    mote_count = max(8, min(28, (width * height) // 380))
    motes = _init_motes(mote_count)

    start_time = time.monotonic()
    last_time = start_time
    travel = 0.0

    while matrix.ready():
        now = time.monotonic()
        delta = min(now - last_time, 0.12)
        last_time = now
        elapsed = (now - start_time) * speed
        travel += delta * speed * 3.1

        theme = _select_cycled_theme(theme_bank, elapsed) if cycle_mode else fixed_theme
        pose = _camera_pose(elapsed, curve_strength)

        canvas, depth_buf = _shade_hallway(
            base_rx, base_ry, travel, elapsed, pose, theme, enable_pulse
        )

        if enable_motes:
            motes["z"] -= delta * speed * 3.1 * motes["speed"]
            reset_mask = motes["z"] <= 0.45
            if np.any(reset_mask):
                motes["z"][reset_mask] += 13.8
            _render_motes(
                canvas, motes, depth_buf, width, height, focal, pose, theme, elapsed
            )

        frame = np.clip(canvas, 0.0, 255.0).astype(np.uint8)
        if channel_idx is not None:
            frame = frame[:, :, channel_idx]
        matrix.image(Image.fromarray(frame, mode="RGB"))
        matrix.show()
