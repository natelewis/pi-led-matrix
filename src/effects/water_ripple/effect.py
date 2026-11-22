import math


def tunnel_circle(matrix, center, radius):
    """create individual circle"""
    if radius > 0:
        matrix.circle(center, radius + 1, (0, 0, 90), 1)
        matrix.circle(center, radius, (0, 0, 255), 1)
        if radius - 1 > 0:
            matrix.circle(center, radius - 1, (0, 0, 90), 1)


def run(matrix, config):
    """water rippling outwards"""
    center = (config["pixel_width"] // 2, config["pixel_height"] // 2)
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
            tunnel_circle(matrix, center, radius)

        matrix.show()
