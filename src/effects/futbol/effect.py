#
# futbol
# 28 August 2022
#

import random

RED_FORMATION = [
    (24, 12),
    (28, 12),
    (32, 12),
    (36, 12),
    (4, 12),
    (8, 8),
    (13, 6),
    (54, 12),
    (48, 10),
    (30, 8),
    (40, 9),
]

BLUE_FORMATION = [
    (24, 18),
    (28, 18),
    (32, 18),
    (36, 18),
    (30, 23),
    (26, 23),
    (55, 23),
    (44, 20),
    (32, 26),
    (8, 22),
    (12, 24),
]


def scale_formation(formation, width, height):
    """scale 60x30 player coordinates to the configured matrix size"""
    return [
        (round(x * (width - 1) / 59), round(y * (height - 1) / 29))
        for x, y in formation
    ]


def move_team(team, other_team, width, height):
    """move players randomly without colliding or leaving the field"""
    for idx, (x, y) in enumerate(team):
        new_x = max(0, min(width - 1, x + random.randint(-1, 1)))
        new_y = max(0, min(height - 1, y + random.randint(-1, 1)))
        if (new_x, new_y) not in other_team and (new_x, new_y) not in team:
            team[idx] = (new_x, new_y)


def run(matrix, config):
    """futbol"""
    x_max = config["pixel_width"]
    y_max = config["pixel_height"]
    play_start = True

    red_pos = scale_formation(RED_FORMATION, x_max, y_max)
    blue_pos = scale_formation(BLUE_FORMATION, x_max, y_max)
    tick_len = max(2, round(x_max / 20))
    player_radius = 1 if min(x_max, y_max) >= 50 else 0

    while matrix.ready():
        matrix.reset((0, 20, 0))

        matrix.line((0, y_max // 2), (x_max - 1, y_max // 2), matrix.color("white"), 1)

        for tick in range(1, 8):
            tick_y = int(y_max / 8 * tick)
            left_hash = int(x_max / 3)
            right_hash = int(x_max - (x_max / 3))
            matrix.line(
                (left_hash - tick_len, tick_y),
                (left_hash, tick_y),
                matrix.color("white"),
                1,
            )
            matrix.line(
                (right_hash, tick_y),
                (right_hash + tick_len, tick_y),
                matrix.color("white"),
                1,
            )

        for pos in red_pos:
            if player_radius > 0:
                matrix.circle(pos, player_radius, matrix.color("red"), -1)
            else:
                matrix.pixel(pos, matrix.color("red"))

        for pos in blue_pos:
            if player_radius > 0:
                matrix.circle(pos, player_radius, matrix.color("blue"), -1)
            else:
                matrix.pixel(pos, matrix.color("blue"))

        matrix.show()

        if play_start:
            play_start = False
            matrix.delay(3000)

        move_team(red_pos, blue_pos, x_max, y_max)
        move_team(blue_pos, red_pos, x_max, y_max)
