#
# Let's play a game of pong!
# 20 July 2022 - updated logic to paddle behavior to make it almost miss sometimes
# 17 July 2022 - Added walls and paddles
# 13 July 2022 - bouncing ball
#

import random


def build_court(width, height):
    """compute court, paddle, and ball geometry for the matrix size"""
    scale = max(1, min(width, height) // 30)
    paddle_height = max(5, (height // 5) | 1)
    paddle_w = scale
    ball_r = scale - 1
    wall_t = scale
    margin_x = max(2, 2 * scale)
    return {
        "scale": scale,
        "paddle_height": paddle_height,
        "paddle_w": paddle_w,
        "ball_r": ball_r,
        "wall_t": wall_t,
        "left_x": margin_x,
        "right_x": width - 1 - margin_x - paddle_w,
        "x_min": margin_x + paddle_w + ball_r + 1,
        "x_max": width - 2 - margin_x - paddle_w - ball_r,
        "y_min": wall_t + ball_r,
        "y_max": height - 1 - wall_t - ball_r,
        "height": height,
    }


def move_paddle(paddle_y, ball_y, court):
    """move paddle toward ball within wall bounds"""
    paddle_mid = court["paddle_height"] // 2
    step = court["scale"]
    min_y = court["wall_t"]
    max_y = court["height"] - 1 - court["wall_t"] - court["paddle_height"]
    if ball_y > paddle_y + paddle_mid:
        return min(max_y, paddle_y + step)
    if ball_y < paddle_y + paddle_mid:
        return max(min_y, paddle_y - step)
    return paddle_y


def draw_frame(matrix, court, ball, paddles):
    """draw walls, paddles, and ball"""
    white = (255, 255, 255)
    left_y, right_y = paddles
    wall_t = court["wall_t"]
    height = court["height"]

    matrix.rectangle(
        (court["left_x"], 0),
        (court["right_x"] + court["paddle_w"], wall_t - 1),
        white,
        -1,
    )
    matrix.rectangle(
        (court["left_x"], height - wall_t),
        (court["right_x"] + court["paddle_w"], height - 1),
        white,
        -1,
    )
    matrix.rectangle(
        (court["left_x"], left_y),
        (court["left_x"] + court["paddle_w"] - 1, left_y + court["paddle_height"]),
        white,
        -1,
    )
    matrix.rectangle(
        (court["right_x"], right_y),
        (court["right_x"] + court["paddle_w"] - 1, right_y + court["paddle_height"]),
        white,
        -1,
    )
    if court["ball_r"] > 0:
        matrix.circle(ball, court["ball_r"], white, -1)
    else:
        matrix.pixel(ball, white)


def run(matrix, config):
    """pong"""
    court = build_court(config["pixel_width"], config["pixel_height"])
    step = court["scale"]
    x_vector = step
    y_vector = step
    x = random.randint(court["x_min"] + 1, max(court["x_min"] + 1, court["x_max"] - 1))
    y = random.randint(court["y_min"] + 1, max(court["y_min"] + 1, court["y_max"] - 1))

    y_mid = court["height"] // 2
    left_paddle_y = y_mid - court["paddle_height"] // 2
    right_paddle_y = left_paddle_y
    trigger = y_mid + court["paddle_height"]

    while matrix.ready():
        matrix.reset()

        if x + x_vector <= court["x_min"] or x + x_vector >= court["x_max"]:
            x_vector *= -1
        if y + y_vector <= court["y_min"] or y + y_vector >= court["y_max"]:
            y_vector *= -1

        x = max(court["x_min"], min(court["x_max"], x + x_vector))
        y = max(court["y_min"], min(court["y_max"], y + y_vector))

        if x <= court["x_min"] + trigger:
            left_paddle_y = move_paddle(left_paddle_y, y, court)
        if x >= court["x_max"] - trigger:
            right_paddle_y = move_paddle(right_paddle_y, y, court)

        draw_frame(matrix, court, (x, y), (left_paddle_y, right_paddle_y))
        matrix.show()
