import random
from operator import itemgetter

# max flakes on the matrix
SNOW_FLAKE_COUNT = 20

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


def run(matrix, config):
    """falling snow"""
    flake_height = len(FLAKE_1)
    snow_flakes = [{"y": -flake_height, "x": 0}] * SNOW_FLAKE_COUNT
    while matrix.ready():
        matrix.reset()
        for idx, _ in enumerate(snow_flakes):
            x, y = itemgetter("x", "y")(snow_flakes[idx])

            # if fell to the bottom reset to the top
            if y > config["pixel_height"]:
                y = -flake_height

            # move it down if it is falling
            if y > -flake_height:
                y = y + 1

            # reset it to the top at random if ready
            if y == -flake_height:
                # random x position where the position might be almost off screen on either side
                x = int(
                    random.random() * (config["pixel_width"] + flake_height)
                    - flake_height
                )
                if int(random.random() * RANDOM_DELAY) == 0:

                    # anti overlapping
                    overlapping = False
                    for flake in snow_flakes:
                        # find flakes that could overlap with a buffer above that is the
                        # size of the flake
                        if (
                            flake["y"] > -flake_height
                            and flake["y"] < flake_height
                            and x > flake["x"] - flake_height * SNOW_FLAKE_DISTANCE
                            and x < flake["x"] + flake_height * SNOW_FLAKE_DISTANCE
                        ):
                            overlapping = True

                    if not overlapping:
                        y = -flake_height + 1

            snow_flakes[idx] = {"x": x, "y": y}
            if y > -flake_height:
                # shimmer effect value by having random brightness
                brightness = random.randint(50, 255)
                spin_axis = random.randint(0, 1) if SPIN_FLAKE else x
                flake = FLAKE_1 if (spin_axis % 2) == 0 else FLAKE_2
                matrix.sprite(
                    flake, (x, y), {"x": (brightness, brightness, brightness)}
                )

        matrix.show()
