import random

def run(matrix, config):
    snow_flake_count = 40
    random_delay = 10 # 1 in x chance of falling when reset to top
    snow_flakes = [{'y': 0, 'x': 0}]*snow_flake_count
    while True:
        matrix.fill(0,0,0)

        for idx, flake in enumerate(snow_flakes):
            # move it down if it is falling
            if flake['y'] > 0:
                snow_flakes[idx]['y'] = snow_flakes[idx]['y'] + 1

            # reset it to the top at random if ready
            if flake['y'] == 0:
                # give effect of pooling at the top
                snow_flakes[idx]['x'] = random.randint(0, config['pixel_width'] - 1)
                if random.randint(0, random_delay) == 0:
                    snow_flakes[idx]['y'] = 1

            # if fell to the bottom reset to the top
            if flake['y'] > config['pixel_height']:
                snow_flakes[idx]['y'] = 0

            matrix.circle((snow_flakes[idx]['x'], snow_flakes[idx]['y']), 1, (255,255,255), 1)

        matrix.show()
