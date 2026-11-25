"""Backwards-compatible matrix.text() helper backed by cached, path-safe led_fonts."""

from __future__ import annotations

from PIL import Image, ImageDraw

from lib.led_fonts import Pixel5x7Font, load_font


def text(self, message, start, font_size, rgb_color, ttf_file="dosis.ttf"):
    """Draw text onto matrix.frame using cached fonts with safe fallback."""
    image = Image.fromarray(self.frame)
    font = load_font(ttf_file, int(font_size))
    if isinstance(font, Pixel5x7Font):
        mask = font.render_mask(str(message))
        color_img = Image.new("RGB", mask.size, tuple(int(c) for c in rgb_color))
        image.paste(color_img, (int(start[0]), int(start[1])), mask)
    else:
        draw = ImageDraw.Draw(image)
        draw.text(
            (int(start[0]), int(start[1])),
            str(message),
            font=font,
            fill=tuple(int(c) for c in rgb_color),
        )
    self.image(image)
