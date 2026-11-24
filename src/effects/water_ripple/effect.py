import math

CONFIG_SCHEMA = [
    {
        "key": "color",
        "label": "Ripple Color",
        "type": "color",
        "default": "#0000ff",
        "description": "Primary color of the expanding ripple rings.",
    },
]


def tunnel_circle(matrix, center, radius, primary_color, halo_color):
    """create individual circle"""
    if radius > 0:
        matrix.circle(center, radius + 1, halo_color, 1)
        matrix.circle(center, radius, primary_color, 1)
        if radius - 1 > 0:
            matrix.circle(center, radius - 1, halo_color, 1)


def run(matrix, config):
    """water rippling outwards"""
    center = (config["pixel_width"] // 2, config["pixel_height"] // 2)
    effect_cfg = config.get("effect") or {}
    primary_color = matrix.parse_color(
        effect_cfg.get("color") if isinstance(effect_cfg, dict) else None,
        (0, 0, 255),
    )
    halo_color = tuple(int(round(channel * 0.35)) for channel in primary_color)
    ring_spacing = 10
    corner_dist = math.hypot(center[0], center[1]) + 2
    max_radius = math.ceil(corner_dist / ring_spacing) * ring_spacing
    rings = list(range(0, max_radius, ring_spacing))

    while matrix.ready():
        matrix.reset()
        for idx, radius in enumerate(rings):
            radius = radius + 1
            if radius >= max_radius:
                radius = 0
            rings[idx] = radius
            tunnel_circle(matrix, center, radius, primary_color, halo_color)

        matrix.show()
