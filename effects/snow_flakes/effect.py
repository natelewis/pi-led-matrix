import random
from operator import itemgetter

snow_flake_count = 20
random_delay = 10 # 1 in x chance of falling when reset to top

flake_1 = [
    ['x', ' ', 'x', ' ', 'x'],

    [' ', 'x', 'x', 'x', ' '],

    ['x', 'x', ' ', 'x', 'x'],

    [' ', 'x', 'x', 'x', ' '],

    ['x', ' ', 'x', ' ', 'x'],
]

flake_2 = [
    [' ', 'x', ' ', 'x', ' '],

    ['x', 'x', 'x', 'x', 'x'],

    [' ', 'x', ' ', 'x', ' '],

    ['x', 'x', 'x', 'x', 'x'],

    [' ', 'x', ' ', 'x', ' '],
]

def run(matrix, config):
    """falling snow"""
    snow_flakes = [{'y': -1, 'x': 0}] * snow_flake_count
    while True:
        matrix.reset((0,0,0))
        for idx, _ in enumerate(snow_flakes):
            x, y = itemgetter('x', 'y')(snow_flakes[idx])

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
            if (y > -1):
                brightness = random.randint(100, 255)
                flake = flake_1 if (y % 2) == 0 else flake_2
                matrix.sprite(flake, (x, y), {'x': (brightness, brightness, brightness)})

        matrix.show()
