#
# Let's play a game of pong!
# 13 July 2022
#

import random

#
# ./run.sh pong
#
def run(matrix, config):
    """ pong """
    x_vector = 1
    y_vector = 1
    x_min = 0
    y_min = 0
    x_max = config['pixel_width'] - 1
    y_max = config['pixel_height'] - 1
    x = int(random.random() * x_max)
    y = int(random.random() * y_max)

    print(f"start at {x}, {y}")
    
    matrix.fill(0, 0, 0)
    while True:
        prev_x = x
        prev_y = y

        if x + x_vector <= x_min or x + x_vector >= x_max:
            x_vector *= -1
        if y + y_vector <= y_min or y + y_vector >= y_max:
            y_vector *= -1

        x += x_vector
        y += y_vector

        matrix.pixel((x, y), (255,255,255), 1)
        matrix.pixel((prev_x, prev_y), (0, 0, 0,), 1)

        matrix.show()
