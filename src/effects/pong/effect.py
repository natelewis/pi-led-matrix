#
# Let's play a game of pong!
# 20 July 2022 - updated logic to paddle behavior to make it almost miss sometimes
# 17 July 2022 - Added walls and paddles
# 13 July 2022 - bouncing ball
#

import random


#
# ./run.sh pong
#
def run(matrix, config):
    """pong"""
    paddle_height = 5  # should always be an odd number

    x_vector = 1
    y_vector = 1
    x_min = 3
    y_min = 0
    x_max = config["pixel_width"] - 4
    y_max = config["pixel_height"] - 1
    y_midpoint = round(y_max / 2)
    x = int(random.random() * x_max)
    y = int(random.random() * y_max)
    paddle_midpoint = int(paddle_height / 2) + 1

    # Paddles
    left_paddle_y = int(y_max / 2)
    right_paddle_y = int(y_max / 2)

    # Don't start the ball inside the wall
    if y == 0 or y == y_max:
        y = 1

    print(f"start at {x}, {y}")

    def move_paddle(paddle_y, ball_y):
        if ball_y > paddle_y + paddle_midpoint:
            if paddle_y < y_max - paddle_height - 1:
                return paddle_y + 1
        else:
            if paddle_y > 1:
                return paddle_y - 1
        return paddle_y

    while matrix.ready():
        matrix.reset()

        if x + x_vector <= x_min or x + x_vector >= x_max:
            x_vector *= -1
        if y + y_vector <= y_min or y + y_vector >= y_max:
            y_vector *= -1

        x += x_vector
        y += y_vector

        # Move paddles to meet the ball
        if x <= x_min + y_midpoint + paddle_height:
            left_paddle_y = move_paddle(left_paddle_y, y)

        if x >= x_max - y_midpoint - paddle_height:
            right_paddle_y = move_paddle(right_paddle_y, y)

        # Draw top and bottom walls
        matrix.line((x_min, 0), (x_max, 0), (255, 255, 255), 1)
        matrix.line((x_min, y_max), (x_max, y_max), (255, 255, 255), 1)

        # Draw paddles
        matrix.rectangle(
            (2, left_paddle_y), (3, left_paddle_y + paddle_height), (255, 255, 255), 1
        )
        matrix.rectangle(
            (x_max, right_paddle_y),
            (x_max + 1, right_paddle_y + paddle_height),
            (255, 255, 255),
            1,
        )

        # Draw ball
        matrix.pixel((x, y), (255, 255, 255))

        matrix.show()
