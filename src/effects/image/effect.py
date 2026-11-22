import sys
import time
from os.path import exists

from PIL import Image


USAGE = 'Usage: make run effect=image config=\'{"file": "image-name.png"}\''


def _load_rgb_image(image_file):
    """Load any RGB/RGBA/palette image composited onto black for LED output."""
    with Image.open(image_file) as raw:
        rgba = raw.convert("RGBA")
        background = Image.new("RGBA", rgba.size, (0, 0, 0, 255))
        return Image.alpha_composite(background, rgba).convert("RGB")


def run(matrix, config):
    """show an image for the configured playlist duration"""
    effect_dir = config["effect_dir"]
    effect_cfg = config.get("effect") or {}
    if not isinstance(effect_cfg, dict) or not effect_cfg.get("file"):
        print("Error: missing image file in effect config")
        print(USAGE)
        sys.exit(1)

    image_file = effect_dir + "/" + effect_cfg["file"]
    if not exists(image_file):
        print("Error: file not found")
        print(USAGE)
        sys.exit(1)

    image = _load_rgb_image(image_file)
    r, g, b = image.split()
    color_corrected_image = Image.merge(
        "RGB", matrix.swap_colors((r, g, b), config["color_order"])
    )

    matrix.image(color_corrected_image)
    matrix.show(delay_ms=0)

    # Hold the image until playlist_delay elapses (or user skips/quits in virtual mode)
    while matrix.ready():
        before = time.monotonic()
        matrix.delay(50)
        if time.monotonic() - before < 0.04 and matrix.ready():
            time.sleep(0.05)
