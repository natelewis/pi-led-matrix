import random
from operator import itemgetter

def run(matrix, config):
    """falling snow"""
    snow_flake_count = 60
    random_delay = 10 # 1 in x chance of falling when reset to top
    snow_flakes = [{'y': -1, 'x': 0}]*snow_flake_count
    while True:
        matrix.fill(0,0,0)
        for idx, _ in enumerate(snow_flakes):
            x, y = itemgetter('x', 'y')( snow_flakes[idx])

            # if fell to the bottom reset to the top
            if y > config['pixel_height']:
                y = -1

            # move it down if it is falling
            if y > -1:
                y = y + 1

            # reset it to the top at random if ready
            if y == -1:
                x = int(random.random()*config['pixel_width'] - 1)
                if int(random.random()*random_delay) == 0:
                    y = 0

            snow_flakes[idx] = {'x': x, 'y': y }
            matrix.pixel((x, y), (255,255,255), 1)

        matrix.show()
