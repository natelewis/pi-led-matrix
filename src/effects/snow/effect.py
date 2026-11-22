import random
from operator import itemgetter


def run(matrix, config):
    """falling snow"""
    width = config["pixel_width"]
    height = config["pixel_height"]
    snow_flake_count = max(20, (width * height) // 30)
    random_delay = 10  # 1 in x chance of falling when reset to top
    snow_flakes = [{"y": -1, "x": 0} for _ in range(snow_flake_count)]

    while matrix.ready():
        matrix.reset()
        for idx, flake in enumerate(snow_flakes):
            x, y = itemgetter("x", "y")(flake)

            if y >= height:
                y = -1

            if y > -1:
                y = y + 1

            if y == -1:
                x = random.randrange(width)
                if random.randrange(random_delay) == 0:
                    y = 0

            snow_flakes[idx] = {"x": x, "y": y}
            if y >= 0:
                matrix.pixel((x, y), (255, 255, 255))

        matrix.show()
