import cv2
import numpy as np

from PIL import ImageEnhance, Image, ImageDraw, ImageFont
from config import (
    pixel_width,
    pixel_height,
    brightness,
    contrast,
    color,
    virtual_framerate,
    playlist,
    playlist_delay,
)

# config and mapping for virtual env vs pi with LED matrix
# Virtual env only works if it is a constant event loop
VIRTUAL_ENV = False

try:
    # live env
    import board
    import neopixel
    from adafruit_pixel_framebuf import PixelFramebuffer, VERTICAL
except ImportError:
    # virtual env
    VIRTUAL_ENV = True

pixel_pin = board.D18 if not VIRTUAL_ENV else 0
pixel_width = pixel_width
pixel_height = pixel_height
playlist = playlist
playlist_delay = playlist_delay

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

def swapRgbToBgr(rgb_color):
    r, g, b = rgb_color
    return (b, g, r)

def sprite(self, sprite_map, start, color_map):
    for y, line in enumerate(sprite_map):
        for x, pixel in enumerate(line):
            start_x, start_y = start
            if (pixel != ' '):
                self.pixel((start_x + x, start_y + y), color_map[pixel])

def text(self, message, start, font_size, rgb_color, ttf_file):
    image = Image.fromarray(self.frame)
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype('./fonts/' + ttf_file, font_size)
    draw.text(start, message, font = font, fill = (rgb_color))
    self.image(image)

class VirtualMatrix():
    def __init__(self):
        self.current_rendering = False
        self.reset()

    def image(self, img):
        rgb_image = img.convert(RGB);
        self.frame = np.array(rgb_image)

    def show(self):
        cv2.imshow('LED matrix', enhance(self.frame))

        # this is the magic sauce -- waitKey runs all the cv2 handlers behind the scene
        # without this there is no rendering
        cv2.waitKey(virtual_framerate)

    def reset(self, rgb_color = (0, 0, 0)):
        self.frame = reset(rgb_color)

    def delay(self, ms):
        delay(ms)

    def line(self, start, end, rgb_color, width):
        cv2.line(self.frame, start, end, swapRgbToBgr(rgb_color), width)

    def pixel(self, start, rgb_color):
        cv2.line(self.frame, start, start, swapRgbToBgr(rgb_color), 1)

    def rectangle(self, start, end, rgb_color, width):
        cv2.rectangle(self.frame,  start, end, swapRgbToBgr(rgb_color), width)

    def circle(self, center, radius, rgb_color, width):
        cv2.circle(self.frame, center, radius, swapRgbToBgr(rgb_color), width)

    def text(self, message, start, font_size, rgb_color, font = 'dosis.ttf'):
        text(self, message, start, font_size, swapRgbToBgr(rgb_color), font)

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
        self.reset()
        neopixel = pixels()
        self.buff = PixelFramebuffer(
            neopixel,
            pixel_width,
            pixel_height,
            orientation=VERTICAL
        )


    def reset(self, rgb_color = (0, 0, 0)):
        self.frame = reset(rgb_color)

    def image(self, img):
        rgb_image = img.convert(RGB);
        self.frame = np.array(rgb_image)

    def line(self, start, end, rgb_color, width):
        cv2.line(self.frame, start, end, rgb_color, width)

    def pixel(self, start, rgb_color):
        cv2.line(self.frame, start, start, rgb_color, 1)

    def rectangle(self, start, end, rgb_color, width):
        cv2.rectangle(self.frame,  start, end, rgb_color, width)

    def circle(self, center, radius, rgb_color, width):
        cv2.circle(self.frame, center, radius, rgb_color, width)

    def delay(self, ms):
        delay(ms)

    def sprite(self, sprite_map, start, color_map):
        sprite(self, sprite_map, start, color_map)

    def show(self):
        img = Image.fromarray(enhance(self.frame), mode=RGB)
        self.buff.image(img)
        self.buff.display()

    def text(self, message, start, font_size, rgb_color, font = 'dosis.ttf'):
        text(self, message, start, font_size, rgb_color, font)

def Matrix():
    if not VIRTUAL_ENV:
        return LiveMatrix()
    return VirtualMatrix()

