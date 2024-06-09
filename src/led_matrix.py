from os.path import exists
import json
import random
import cv2
import time
import numpy as np

from lib import colors
from PIL import ImageEnhance, Image, ImageDraw, ImageFont
from .lib import colors

CUSTOM_CONFIG = exists('config.json')
# print the name of the config file being used
print(f'Using {"custom" if CUSTOM_CONFIG else "default"} config file')

CONFIG = 'default_config.json' if not CUSTOM_CONFIG else 'config.json'

with open(CONFIG, mode='r',  encoding='utf8') as j_object:
    cfg = json.load(j_object)

# size of matrix
pixel_width = cfg['pixel_width']
pixel_height = cfg['pixel_height']

# brightness 0 - 1
brightness = cfg['brightness']

#contrast (1 is no change)
contrast = cfg['contrast']

#color (1 is no change)
color = cfg['color']

#color rgb swap, default is string 'rgb' which does not swap any color
color_order = cfg['color_order']

# framerate between renderings in milliseconds in virtual mode
# this mimics the delay of hardware latency
virtual_framerate = cfg['virtual_framerate']

# playlists follow this format:
# [
#    {'effect': 'video', 'argv': ['cartoon-60x30.mp4']},
#    {'effect': 'image', 'argv': ['josie-60x30.png']},
#    {'effect': 'snow', 'argv': []},
#    {'effect': 'water_ripple', 'argv':[]},
# ]
playlist = cfg['playlist']
playlist_delay = cfg['playlist_delay']

# config and mapping for virtual env vs pi with LED matrix
# Virtual env only works if it is a constant event loop
VIRTUAL_ENV = False

VIRTUAL_SIZE_MULTIPLIER = 10

try:
    # live env
    import board
    import neopixel
    from adafruit_pixel_framebuf import PixelFramebuffer, VERTICAL
except ImportError:
    # virtual env
    VIRTUAL_ENV = True

pixel_pin = board.D18 if not VIRTUAL_ENV else 0
RGB = 'RGB'

def delay(ms):
    cv2.waitKey(ms)

def reset(rgb_color):
    r, g, b = rgb_color
    return np.full([pixel_height, pixel_width, 3],[b, g, r], np.uint8)

def enhance(image):
    rgb_image = Image.fromarray(image, mode=RGB)
    color_enhance = ImageEnhance.Color(rgb_image)
    colored_image = color_enhance.enhance(color)
    contrast_enhancer = ImageEnhance.Contrast(colored_image)
    contrasted_image =  contrast_enhancer.enhance(contrast)
    return np.array(contrasted_image)

def swap_colors(rgb_color, order='rgb'):
    """
    Swaps the order of an RGB color tuple according to the specified order.

    Parameters:
    - rgb_color: A tuple representing the color (R, G, B).
    - order: A string representing the desired order, e.g., 'bgr', 'rbg', etc.

    Returns:
    - A tuple of the color in the new order.
    """
    # Create a mapping from characters to their indices in the original tuple
    index_map = {'r': 0, 'g': 1, 'b': 2}
    # Use the mapping to rearrange the tuple according to the specified order
    return tuple(rgb_color[index_map[char]] for char in order)

# exclusive to the virtual env
def swap_rgb_to_bgr(rgb_color):
    return swap_colors(rgb_color, 'bgr')


def sprite(self, sprite_map, start, color_map):
    for y, line in enumerate(sprite_map):
        for x, pixel in enumerate(line):
            start_x, start_y = start
            if pixel != ' ':
                self.pixel((start_x + x, start_y + y), color_map[pixel])

def text(self, message, start, font_size, rgb_color, ttf_file):
    image = Image.fromarray(self.frame)
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype('./fonts/' + ttf_file, font_size)
    draw.text(start, message, font = font, fill = (rgb_color))
    self.image(image)

def random_color():
    return (random.randrange(255), random.randrange(255), random.randrange(255))

def ready(start_time):
    if (int(time.time()) - start_time) < playlist_delay:
        return True
    else:
        return False
    
class VirtualMatrix():
    def __init__(self):
        self.frame = []
        self.reset()
        self.start_time = int(time.time())

    def ready(self):
        return ready(self.start_time)
    
    def color(self, color_name):
        return colors.MAP[color_name]

    def random_color(self):
        return random_color()

    def image(self, img):
        rgb_image = img.convert(RGB)
        self.frame = np.array(rgb_image)

    def show(self):
        frame = cv2.resize(self.frame, (pixel_width * VIRTUAL_SIZE_MULTIPLIER, pixel_height * VIRTUAL_SIZE_MULTIPLIER))
        cv2.imshow('LED matrix', enhance(frame))

        # this is the magic sauce -- waitKey runs all the cv2 handlers behind the scene
        # without this there is no rendering
        cv2.waitKey(virtual_framerate)

    def reset(self, rgb_color = (0, 0, 0)):
        self.frame = reset(rgb_color)

    def delay(self, ms):
        delay(ms)

    def line(self, start, end, rgb_color, width):
        cv2.line(self.frame, start, end, swap_rgb_to_bgr(rgb_color), width)

    def pixel(self, start, rgb_color):
        cv2.line(self.frame, start, start, swap_rgb_to_bgr(rgb_color), 1)

    def rectangle(self, start, end, rgb_color, width):
        cv2.rectangle(self.frame,  start, end, swap_rgb_to_bgr(rgb_color), width)

    def circle(self, center, radius, rgb_color, width):
        cv2.circle(self.frame, center, radius, swap_rgb_to_bgr(rgb_color), width)

    def text(self, message, start, font_size, rgb_color, font = 'dosis.ttf'):
        text(self, message, start, font_size, swap_rgb_to_bgr(rgb_color), font)

    def sprite(self, sprite_map, start, color_map):
        sprite(self, sprite_map, start, color_map)

def pixels():
    if not VIRTUAL_ENV:
        return neopixel.NeoPixel(
            pixel_pin,
            pixel_width * pixel_height,
            brightness=brightness,
            auto_write=False,
        )

class LiveMatrix():
    def __init__(self):
        self.frame = []
        self.reset()
        neopixel_pixels = pixels()
        self.buff = PixelFramebuffer(
            neopixel_pixels,
            pixel_width,
            pixel_height,
            orientation=VERTICAL,
            alternating=True,
        )
        self.start_time = int(time.time())

    def ready(self):
        return ready(self.start_time)

    def color(self, color_name):
        return colors.MAP[color_name]

    def random_color(self):
        return random_color()

    def reset(self, rgb_color = (0, 0, 0)):
        self.frame = reset(rgb_color)

    def image(self, img):
        rgb_image = img.convert(RGB)
        self.frame = np.array(rgb_image)

    def line(self, start, end, rgb_color, width):
        print(f'line: {start} {end} {swap_colors(rgb_color, color_order)} {width}')
        cv2.line(self.frame, start, end, swap_colors(rgb_color, color_order), width)

    def pixel(self, start, rgb_color):
        cv2.line(self.frame, start, start, swap_colors(rgb_color, color_order), 1)

    def rectangle(self, start, end, rgb_color, width):
        cv2.rectangle(self.frame,  start, end, swap_colors(rgb_color, color_order), width)

    def circle(self, center, radius, rgb_color, width):
        cv2.circle(self.frame, center, radius, swap_colors(rgb_color, color_order), width)

    def delay(self, ms):
        delay(ms)

    def sprite(self, sprite_map, start, color_map):
        sprite(self, sprite_map, start, color_map)

    def show(self):
        img = Image.fromarray(enhance(self.frame), mode=RGB)
        self.buff.image(img)
        self.buff.display()

    def text(self, message, start, font_size, rgb_color, font = 'dosis.ttf'):
        text(self, message, start, font_size, swap_colors(rgb_color, color_order), font)

# return the class for your env
def Matrix(): # pylint: disable=invalid-name
    if not VIRTUAL_ENV:
        return LiveMatrix()
    return VirtualMatrix()
