#
# eye looking at you
# 22 July 2022 - Simple eyes with random movement
#
# Brown Eyes: 45 percent
# Blue Eyes: 28 percent
# Hazel Eyes: 18 percent (shades of brown and green, sometimes called forestgreen)
# Green Eyes: 9 percent
#

import random


def run(matrix, config):
    """eyes looking at you"""
    width = config["pixel_width"]
    height = config["pixel_height"]
    eye_y = height // 2
    eye_positions = [width // 4, (width * 3) // 4]

    eye_radius = max(3, min(int(height * 0.4), int(width * 0.2)))
    iris_radius = max(2, round(eye_radius * 5 / 12))
    pupil_radius = max(1, round(eye_radius * 2 / 12))
    look = max(1, round(eye_radius * 5 / 12))

    eye_color = random.choices(
        [
            matrix.color("brown"),
            matrix.color("blue"),
            matrix.color("forestgreen"),
            matrix.color("green"),
        ],
        weights=[45, 28, 18, 9],
    )[0]

    while matrix.ready():
        x_dir, y_dir = random.choices(
            [
                (0, 0),
                (look, 0),
                (-look, 0),
                (0, look),
                (0, -look),
                (look, -look),
                (look, look),
                (-look, look),
                (-look, -look),
            ],
            weights=[60, 5, 5, 5, 5, 5, 5, 5, 5],
        )[0]
        matrix.reset()
        for eye_x in eye_positions:
            matrix.circle((eye_x, eye_y), eye_radius, matrix.color("white"), -1)
            matrix.circle((eye_x + x_dir, eye_y + y_dir), iris_radius, eye_color, -1)
            matrix.circle(
                (eye_x + x_dir, eye_y + y_dir),
                pupil_radius,
                matrix.color("black"),
                -1,
            )
        matrix.show()
        matrix.delay(3000)
