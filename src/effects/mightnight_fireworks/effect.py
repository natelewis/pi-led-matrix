"""Midnight fireworks wave effect."""

import time

import numpy as np
from PIL import Image


def run(matrix, config):
    """Glowing rockets soaring and bursting into shimmering multi-color sparks."""
    width = max(1, int(config["pixel_width"]))
    height = max(1, int(config["pixel_height"]))
    xx, yy = np.meshgrid(
        np.linspace(-1.0, 1.0, width, dtype=np.float32),
        np.linspace(-1.0, 1.0, height, dtype=np.float32),
    )
    dist = np.hypot(xx, yy * 0.85)
    start = time.monotonic()

    while matrix.ready():
        t = time.monotonic() - start
        wave = 0.5 + 0.5 * np.sin(
            dist * 9.0 - t * 3.2 + np.sin(xx * 4.0 + t * 1.4) * 1.5
        )
        r = np.clip(wave * 255.0, 0, 255).astype(np.uint8)
        g = np.clip(
            (0.5 + 0.5 * np.sin(dist * 7.0 + t * 2.0 + 2.1)) * 240.0, 0, 255
        ).astype(np.uint8)
        b = np.clip(
            (0.5 + 0.5 * np.cos(xx * 4.0 - t * 2.5)) * 255.0, 0, 255
        ).astype(np.uint8)
        frame = np.stack((r, g, b), axis=-1)
        matrix.image(Image.fromarray(frame, mode="RGB"))
        matrix.show()
