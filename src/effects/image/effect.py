import time
from pathlib import Path

from PIL import Image


USAGE = 'Usage: make run effect=image config=\'{"file": "image-name.png"}\''


def _resolve_safe_image_path(effect_dir, raw_file):
    if not isinstance(raw_file, str) or not raw_file.strip():
        raise ValueError("Missing image file in effect config.")
    base_dir = Path(effect_dir).resolve()
    candidate = (base_dir / raw_file.strip()).resolve()
    try:
        candidate.relative_to(base_dir)
    except ValueError as exc:
        raise ValueError("Image path must reside inside the image effect directory.") from exc
    if not candidate.is_file():
        raise FileNotFoundError(f"Image file not found: {raw_file}")
    return candidate


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
    if not isinstance(effect_cfg, dict):
        print("Error: invalid image effect config")
        print(USAGE)
        raise ValueError("Invalid image effect config")

    image_path = _resolve_safe_image_path(effect_dir, effect_cfg.get("file"))

    image = _load_rgb_image(image_path)
    target_size = (config["pixel_width"], config["pixel_height"])
    if image.size != target_size:
        image = image.resize(target_size, Image.LANCZOS)

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
