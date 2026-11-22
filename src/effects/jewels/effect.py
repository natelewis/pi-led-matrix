#
# Jewels
# 9 January 2023
#

import random


def find_matches(jewels, coord, step):
    """find 3 or more matching adjacent jewels along any axis"""
    target = jewels[coord]
    x, y = coord

    for delta_x, delta_y in [(0, -step), (0, step), (-step, 0), (step, 0)]:
        matches = [coord]
        cur_x = x + delta_x
        cur_y = y + delta_y
        while jewels.get((cur_x, cur_y)) == target:
            matches.append((cur_x, cur_y))
            cur_x += delta_x
            cur_y += delta_y
        if len(matches) > 2:
            return matches

    return [coord]


def draw_jewel(matrix, coord, color, scale):
    """draw a jewel scaled to the grid pitch"""
    if scale <= 1:
        matrix.pixel(coord, color)
    else:
        x, y = coord
        matrix.rectangle((x, y), (x + scale - 1, y + scale - 1), color, -1)


def step_jewels(matrix, jewels, layout, match_color):
    """drop jewels, draw them, and flag 3-in-a-row matches"""
    step = layout["step"]
    max_y = layout["max_y"]
    scale = layout["scale"]
    next_jewels = {}

    for coord, color in jewels.items():
        x, y = coord
        if y < (max_y - step) and (x, y + step) not in jewels:
            coord = (x, y + step)
        draw_jewel(matrix, coord, color, scale)
        if color != match_color:
            next_jewels[coord] = color

    result = next_jewels.copy()
    for coord in next_jewels:
        matches = find_matches(next_jewels, coord, step)
        if len(matches) > 1:
            for match in matches:
                result[match] = match_color
    return result


def run(matrix, config):
    """Jewels"""
    width = config["pixel_width"]
    height = config["pixel_height"]
    scale = max(1, min(width, height) // 36)
    step = 2 * scale
    layout = {
        "scale": scale,
        "step": step,
        "max_x": width - step,
        "max_y": height - step,
    }

    rainbow = [
        matrix.color("red"),
        matrix.color("green"),
        matrix.color("blue"),
        matrix.color("yellow"),
    ]
    background_color = matrix.color("black")
    match_color = matrix.color("white")

    jewels = {}
    stable_jewels = 0

    while matrix.ready():
        matrix.reset(background_color)

        added = 0
        for x in range(step, layout["max_x"], step):
            if (x, step) not in jewels:
                jewels[(x, step)] = random.choice(rainbow)
                added += 1

        stable_jewels = stable_jewels + 1 if added == 0 else 0
        if stable_jewels > 10:
            jewels = {}

        jewels = step_jewels(matrix, jewels, layout, match_color)
        matrix.show()
