#
# Jackson Pollack Art Generator
# 6 January 2023
#

import random

# Number of seconds between screen updates
# set PAUSE to 0 for an old timey static effect.
PAUSE = 5


def run(matrix, config):
    """Jackson Pollock Art Generator"""
    max_y = config["pixel_height"]
    max_x = config["pixel_width"]

    rainbow = [
        matrix.color("red"),
        matrix.color("green"),
        matrix.color("blue"),
        matrix.color("purple"),
        matrix.color("yellow"),
        matrix.color("white"),
    ]

    background_color = matrix.color("black")

    while matrix.ready():
        matrix.reset(background_color)

        for x in range(max_x):
            for y in range(max_y):
                matrix.pixel((x, y), random.choice(rainbow))

        matrix.show()

        if PAUSE > 0:
            matrix.delay(PAUSE * 1000)
