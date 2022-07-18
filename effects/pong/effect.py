#
# Let's play a game of pong!
# 17 July 2022 - Added walls and paddles
# 13 July 2022 - bouncing ball
#

import random

#
# ./run.sh pong
#
def run(matrix, config):
    """ pong """
    matrix.reset()

    x_vector = 1
    y_vector = 1
    x_min = 3
    y_min = 0
    x_max = config['pixel_width'] - 4
    y_max = config['pixel_height'] - 1
    x = int(random.random() * x_max)
    y = int(random.random() * y_max)

    # Paddles
    left_paddle_y = int(y_max / 2)
    right_paddle_y = int(y_max / 2)

    # Don't start the ball inside the wall
    if y == 0 or y == y_max:
        y = 1

    # Draw top and bottom walls
    matrix.line((x_min, 0), (x_max, 0), (255, 255, 255), 1)
    matrix.line((x_min, y_max), (x_max, y_max), (255, 255, 255), 1)

    # Draw paddles
    matrix.rectangle((2, left_paddle_y), (3, left_paddle_y + 5), (255, 255, 255), 1)
    matrix.rectangle((x_max, right_paddle_y), (x_max + 1, right_paddle_y + 5), (255, 255, 255), 1)

    print(f"start at {x}, {y}")

    while True:
        prev_x = x
        prev_y = y

        if x + x_vector <= x_min or x + x_vector >= x_max:
            x_vector *= -1
        if y + y_vector <= y_min or y + y_vector >= y_max:
            y_vector *= -1

        x += x_vector
        y += y_vector

        # Move paddles to meet the ball
        if x <= x_min + 10:
            matrix.rectangle((2, left_paddle_y), (3, left_paddle_y + 5), (0 ,0 ,0), 1)
            left_paddle_y = y - 2
            matrix.rectangle((2, left_paddle_y), (3, left_paddle_y + 5), (255, 255, 255), 1)

        if x >= x_max - 10:
            matrix.rectangle((x_max, right_paddle_y), (x_max + 1, right_paddle_y + 5), (0, 0, 0), 1)
            right_paddle_y = y - 2
            matrix.rectangle((x_max, right_paddle_y), (x_max + 1, right_paddle_y + 5), (255, 255, 255), 1)

        matrix.pixel((x, y), (255, 255, 255))
        matrix.pixel((prev_x, prev_y), (0, 0, 0))

        matrix.show()
