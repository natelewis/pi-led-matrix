#
# Multiball
#
# 25 July 2022
#

from operator import itemgetter
import random


def random_velocity(max_speed):
    """pick a non-zero velocity in [-max_speed, max_speed]"""
    val = 0
    while val == 0:
        val = random.randint(-max_speed, max_speed)
    return val


def step_ball(ball, bounds):
    """advance a single ball and bounce off bounds"""
    x, y, x_vector, y_vector, color = itemgetter(
        "x", "y", "x_vector", "y_vector", "color"
    )(ball)
    x_min, y_min, x_max, y_max = bounds

    if x + x_vector <= x_min or x + x_vector >= x_max:
        x_vector *= -1
    if y + y_vector <= y_min or y + y_vector >= y_max:
        y_vector *= -1

    return {
        "x": max(x_min, min(x_max, x + x_vector)),
        "y": max(y_min, min(y_max, y + y_vector)),
        "x_vector": x_vector,
        "y_vector": y_vector,
        "color": color,
    }


def run(matrix, config):
    """multiball!"""
    width = config["pixel_width"]
    height = config["pixel_height"]
    ball_radius = 1 if min(width, height) >= 50 else 0
    bounds = (
        ball_radius,
        ball_radius,
        max(ball_radius, width - 1 - ball_radius),
        max(ball_radius, height - 1 - ball_radius),
    )

    default_balls = max(8, round(width * height / 112))
    try:
        num_of_balls = int(config["argv"][0]) or default_balls
    except (KeyError, IndexError, ValueError, TypeError):
        num_of_balls = default_balls

    max_speed = max(3, min(width, height) // 15)
    all_balls = [
        {
            "x": random.randint(bounds[0], bounds[2]),
            "y": random.randint(bounds[1], bounds[3]),
            "x_vector": random_velocity(max_speed),
            "y_vector": random_velocity(max_speed),
            "color": matrix.random_color(),
        }
        for _ in range(num_of_balls)
    ]

    while matrix.ready():
        matrix.reset()

        for idx, ball in enumerate(all_balls):
            updated = step_ball(ball, bounds)
            pos = (updated["x"], updated["y"])
            if ball_radius > 0:
                matrix.circle(pos, ball_radius, updated["color"], -1)
            else:
                matrix.pixel(pos, updated["color"])
            all_balls[idx] = updated

        matrix.show()
