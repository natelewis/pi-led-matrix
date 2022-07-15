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

    ['x', ' ', 'x', ' ', 'x'],

    [' ', 'x', 'x', 'x', ' '],

    ['x', ' ', 'x', ' ', 'x'],

    [' ', 'x', ' ', 'x', ' '],
]

def run(matrix, config):
    """falling snow"""
    flake_height = len(flake_1)
    snow_flakes = [{'y': -flake_height, 'x': 0}] * snow_flake_count
    while True:
        matrix.reset((0,0,0))
        for idx, _ in enumerate(snow_flakes):
            x, y = itemgetter('x', 'y')(snow_flakes[idx])

            # if fell to the bottom reset to the top
            if y > config['pixel_height']:
                y = -flake_height

            # move it down if it is falling
            if y > -flake_height:
                y = y + 1

            # reset it to the top at random if ready
            if y == -flake_height:
                x = int(random.random()*config['pixel_width'] - 1)
                if int(random.random()*random_delay) == 0:
                    # TODO: check if another flake is close to me, and if so, skip until I'm alone
                    # so flakes don't overlap
                    y = -flake_height + 1 # kicked off the flake

            snow_flakes[idx] = {'x': x, 'y': y }
            if (y > -flake_height):
                brightness = random.randint(50, 255)
                flake = flake_1 if (x % 2) == 0 else flake_2
                matrix.sprite(flake, (x, y), {'x': (brightness, brightness, brightness)})

        matrix.show()
