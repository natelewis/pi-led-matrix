import random
from operator import itemgetter

# 1 in x chance of falling when reset to top
RANDOM_DELAY = 2

# how close can they be ( 1 is touching, but not overlapping)
SNOW_FLAKE_DISTANCE = 1.1

# alternate the flake pattern randomly while filling
SPIN_FLAKE = True

FLAKE_1 = [
    ["x", " ", "x", " ", "x"],
    [" ", "x", "x", "x", " "],
    ["x", "x", " ", "x", "x"],
    [" ", "x", "x", "x", " "],
    ["x", " ", "x", " ", "x"],
]

FLAKE_2 = [
    [" ", "x", " ", "x", " "],
    ["x", " ", "x", " ", "x"],
    [" ", "x", "x", "x", " "],
    ["x", " ", "x", " ", "x"],
    [" ", "x", " ", "x", " "],
]


def scale_sprite(sprite, scale):
    """scale a 2D sprite array by an integer factor"""
    if scale <= 1:
        return sprite
    return [
        [cell for cell in row for _ in range(scale)]
        for row in sprite
        for _ in range(scale)
    ]


def is_overlapping(x, snow_flakes, flake_height):
    """check if a new flake at x overlaps an existing flake near the top"""
    spacing = flake_height * SNOW_FLAKE_DISTANCE
    for flake in snow_flakes:
        if (
            -flake_height < flake["y"] < flake_height
            and flake["x"] - spacing < x < flake["x"] + spacing
        ):
            return True
    return False


def run(matrix, config):
    """falling snow"""
    width = config["pixel_width"]
    height = config["pixel_height"]
    scale = max(1, min(width, height) // 36)
    flake_1 = scale_sprite(FLAKE_1, scale)
    flake_2 = scale_sprite(FLAKE_2, scale)
    flake_height = len(flake_1)
    flake_count = max(10, round(width * height / (flake_height * flake_height * 3.6)))
    snow_flakes = [{"y": -flake_height, "x": 0} for _ in range(flake_count)]

    while matrix.ready():
        matrix.reset()
        for idx, entry in enumerate(snow_flakes):
            x, y = itemgetter("x", "y")(entry)

            if y > height:
                y = -flake_height

            if y > -flake_height:
                y = y + scale

            if y == -flake_height:
                x = random.randint(-flake_height + 1, width - 1)
                if random.randrange(RANDOM_DELAY) == 0 and not is_overlapping(
                    x, snow_flakes, flake_height
                ):
                    y = -flake_height + 1

            snow_flakes[idx] = {"x": x, "y": y}
            if y > -flake_height:
                brightness = random.randint(50, 255)
                spin_axis = random.randint(0, 1) if SPIN_FLAKE else x
                sprite = flake_1 if (spin_axis % 2) == 0 else flake_2
                matrix.sprite(
                    sprite, (x, y), {"x": (brightness, brightness, brightness)}
                )

        matrix.show()
