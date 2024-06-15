#
# Matrix
# 5 September 2022
#

import random
from operator import itemgetter


def run(matrix, config):
    """Matrix"""
    lines = []
    min_y = 0
    max_y = config["pixel_height"]
    max_x = config["pixel_width"]

    # max speed of line movement
    max_speed = 6

    # percent chance each pixel in a line goes missing to simulate static
    percent_static = 0.20

    matrix_color = matrix.color("green")
    background_color = matrix.color("black")

    # create a new matrix line about to drop down
    def new_line():
        line_len = random.randrange(max_y)
        return {
            "tail": -line_len,
            "head": min_y,
            "speed": random.randrange(1, max_speed),
        }

    # create initial matrix lines
    for _ in range(max_x):
        lines.append(new_line())

    while matrix.ready():
        matrix.reset(background_color)

        for i in range(max_x):
            head, tail, speed = itemgetter("head", "tail", "speed")(lines[i])
            head += speed
            tail += speed
            matrix.line((i, head), (i, tail), matrix_color, 1)

            # add dead pixels in the matrix line to simulate static
            for j in range(tail, head):
                if random.random() < percent_static:
                    matrix.pixel((i, j), background_color)

            # if matrix line drops below screen, create a new matrix line
            if tail > max_y:
                lines[i] = new_line()
            else:
                lines[i] = {"tail": tail, "head": head, "speed": speed}

        matrix.show()
