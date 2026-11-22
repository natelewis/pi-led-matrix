#
# Warp speed
#
# 25 July 2022 = Added black hole in center
# 21 July 2022 - Simple lines moving away from center using trig
#

import math
import random


STEP = 5.5


def make_star(matrix, center, dist):
    """create a star positioned at dist steps along a random angle"""
    mid_x, mid_y = center
    angle = random.uniform(0, 2 * math.pi)
    return {
        "color": matrix.random_color(),
        "x": mid_x + int(dist * STEP * math.cos(angle)),
        "y": mid_y - int(dist * STEP * math.sin(angle)),
        "angle": angle,
        "dist": dist,
    }


def run(matrix, config):
    """Warp speed effect"""
    width = config["pixel_width"]
    height = config["pixel_height"]
    center = (width // 2, height // 2)
    max_dist = max(6, math.ceil((math.hypot(*center) + 2) / STEP) + 1)
    num_of_stars = max(12, round(width * height / 150))
    hole_radius = max(2, min(center) // 8)

    galaxy = [make_star(matrix, center, idx % max_dist) for idx in range(num_of_stars)]

    while matrix.ready():
        matrix.reset()
        for idx, star in enumerate(galaxy):
            dist = star["dist"] + 1
            new_x = center[0] + int(dist * STEP * math.cos(star["angle"]))
            new_y = center[1] - int(dist * STEP * math.sin(star["angle"]))

            matrix.line((star["x"], star["y"]), (new_x, new_y), star["color"], 1)

            if dist >= max_dist:
                galaxy[idx] = make_star(matrix, center, 0)
            else:
                galaxy[idx] = {
                    "color": star["color"],
                    "x": new_x,
                    "y": new_y,
                    "angle": star["angle"],
                    "dist": dist,
                }

        matrix.circle(center, hole_radius, (0, 0, 0), -1)
        matrix.show()
