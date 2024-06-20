from PIL import Image, ImageEnhance
import numpy as np


def reset(rgb_color, pixel_height, pixel_width):
    """
    Resets the image with the specified RGB color.

    Args:
            rgb_color (tuple): A tuple containing the RGB values of the color.
            pixel_height (int): The height of the image in pixels.
            pixel_width (int): The width of the image in pixels.

    Returns:
            numpy.ndarray: A numpy array representing the reset image.
    """
    r, g, b = rgb_color
    return np.full([pixel_height, pixel_width, 3], [r, b, g], np.uint8)


def enhance(image, color, contrast):
    """
    Enhances the given image by adjusting its color and contrast.

    Args:
        image (numpy.ndarray): The input image as a NumPy array.

    Returns:
        numpy.ndarray: The enhanced image as a NumPy array.
    """
    rgb_image = Image.fromarray(image, mode="RGB")
    color_enhance = ImageEnhance.Color(rgb_image)
    colored_image = color_enhance.enhance(color)
    contrast_enhancer = ImageEnhance.Contrast(colored_image)
    contrasted_image = contrast_enhancer.enhance(contrast)
    return np.array(contrasted_image)


def sprite(self, sprite_map, start, color_map):
    """
    Renders a sprite on the LED matrix.

    Args:
            sprite_map (list): A 2D list representing the sprite to be rendered.
            start (tuple): The starting position of the sprite on the LED matrix.
            color_map (dict): A dictionary mapping pixel characters to their corresponding colors.

    Returns:
            None
    """
    for y, line in enumerate(sprite_map):
        for x, pixel in enumerate(line):
            start_x, start_y = start
            if pixel != " ":
                self.pixel((start_x + x, start_y + y), color_map[pixel])
