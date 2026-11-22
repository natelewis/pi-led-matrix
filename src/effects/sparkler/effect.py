#
# Sparkler
# 25 July 2022
#

import random

GRAVITY_PULL = 0.35
FIZZLE_OUT = 0.25
ADD_PARTICLES = 3


def run(matrix, config):
    """Sparkler"""
    width = config["pixel_width"]
    height = config["pixel_height"]
    center_x = width // 2
    center_y = height // 2

    scale = max(1.0, min(width, height) / 30.0)
    gravity = GRAVITY_PULL * scale
    fizzle = FIZZLE_OUT * max(1.0, scale * 0.7)
    add_particles = max(ADD_PARTICLES, round(ADD_PARTICLES * scale))
    min_size = max(2, round(2 * scale))
    max_size = max(4, round(4 * scale))
    vel_limit = max(35, round(35 * scale))

    particles = []

    while matrix.ready():
        matrix.reset()

        for _ in range(add_particles):
            particles.append(
                {
                    "x": center_x,
                    "y": center_y,
                    "dx": random.randrange(-vel_limit, vel_limit) / 10,
                    "dy": random.randrange(-vel_limit, vel_limit) / 10,
                    "psize": random.randint(min_size, max_size),
                }
            )

        next_particles = []
        for particle in particles:
            particle["x"] += particle["dx"]
            particle["y"] += particle["dy"]
            particle["psize"] -= fizzle
            particle["dy"] += gravity

            if particle["psize"] > 0:
                matrix.circle(
                    (int(particle["x"]), int(particle["y"])),
                    max(1, int(particle["psize"])),
                    matrix.random_color(),
                    -1,
                )
                next_particles.append(particle)

        particles = next_particles
        matrix.show()
