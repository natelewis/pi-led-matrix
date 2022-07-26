#
# Multiball
#
# 25 July 2022
#

from operator import itemgetter
import random

DEFAULT_NUM_OF_BALLS = 16

#
# ./run.sh multiball [num_of_balls]
#
def run(matrix, config):
    """ multiball! """
    x_min = 0
    y_min = 0
    x_max = config['pixel_width'] - 1
    y_max = config['pixel_height'] - 1

    try:
        num_of_balls = int(config['argv'][0])
    except:
        num_of_balls = DEFAULT_NUM_OF_BALLS

    if not num_of_balls:
        num_of_balls = DEFAULT_NUM_OF_BALLS

    all_balls = []
    for ball in range(num_of_balls):
        x = random.randrange(x_max)
        y = random.randrange(y_max)
        x_vector = random.randint(-1, 5)
        y_vector = random.randint(-3, 3)
        if x_vector == 0:
            x_vector = 1
        if y_vector == 0:
            y_vector = 1
        color = (random.randrange(256), random.randrange(256), random.randrange(256))
        all_balls.append({'x': x, 'y': y, 'x_vector': x_vector, 'y_vector': y_vector, 'color': color})

    while True:
        matrix.reset()

        for ball, _ in enumerate(all_balls):
            x, y, x_vector, y_vector, color = itemgetter('x', 'y', 'x_vector', 'y_vector', 'color')(all_balls[ball])

            if x + x_vector <= x_min or x + x_vector >= x_max:
                x_vector *= -1
            if y + y_vector <= y_min or y + y_vector >= y_max:
                y_vector *= -1

            x += x_vector
            y += y_vector

            matrix.pixel((x, y), color)

            all_balls[ball] = {'x': x, 'y': y, 'x_vector': x_vector, 'y_vector': y_vector, 'color': color}

        matrix.show()
