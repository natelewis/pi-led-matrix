from PIL import ImageEnhance, Image
from config import (
    pixel_width,
    pixel_height,
    brightness,
    contrast,
    color,
    virtual_framerate,
)
import cv2
import numpy as np

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

def delay(ms):
    cv2.waitKey(ms)

def fill(r, g, b):
    return np.full([pixel_height, pixel_width, 3],[b, g, r], np.uint8)

def enhance(image):
    rgb_image = Image.fromarray(image, mode="RGB")
    color_enhance = ImageEnhance.Color(rgb_image)
    colored_image = color_enhance.enhance(color)
    contrast_enhancer = ImageEnhance.Contrast(colored_image)
    contrasted_image =  contrast_enhancer.enhance(contrast)
    return np.array(contrasted_image)

def swapRgbToBgr(color):
    r, g, b = color
    return (b, g, r)

class VirtualMatrix():
    def __init__(self):
        self.current_rendering = False
        self.frame = fill(0, 0, 0)

    def image(self, img):
        rgb_image = img.convert("RGB");
        self.frame = np.array(rgb_image)

    def show(self):
        cv2.imshow('LED matrix', enhance(self.frame))

        # this is the magic sauce -- waitKey runs all the cv2 handlers behind the scene
        # without this there is no rendering
        cv2.waitKey(virtual_framerate)

    def fill(self, r, g, b):
        self.frame = fill(r, g, b)

    def delay(self, ms):
        delay(ms)

    def line(self, start, end, color, width):
        cv2.line(self.frame, start, end, swapRgbToBgr(color), width)

    def rectangle(self, start, end, color, width):
        cv2.rectangle(self.frame,  start, end, swapRgbToBgr(color), width)

    def circle(self, center, radius, color, width):
        cv2.circle(self.frame, center, radius, swapRgbToBgr(color), width)

    def text(self, text, start, scale, color, thickness, font = cv2.FONT_HERSHEY_PLAIN):
        cv2.putText(self.frame, text, start, font, scale, swapRgbToBgr(color), thickness, cv2.LINE_4)


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
        self.frame = fill(0, 0, 0)
        neopixel = pixels()
        self.buff = PixelFramebuffer(
            neopixel,
            pixel_width,
            pixel_height,
            orientation=VERTICAL
        )


    def fill(self, r, g, b):
        self.frame = fill(r, g, b)

    def image(self, img):
        rgb_image = img.convert("RGB");
        self.frame = np.array(rgb_image)

    def line(self, start, end, color, width):
        cv2.line(self.frame, start, end, color, width)

    def rectangle(self, start, end, color, width):
        cv2.rectangle(self.frame,  start, end, color, width)

    def circle(self, center, radius, color, width):
        cv2.circle(self.frame, center, radius, color, width)

    def delay(self, ms):
        delay(ms)

    def show(self):
        img = Image.fromarray(enhance(self.frame), mode="RGB")
        self.buff.image(img)
        self.buff.display()

    def text(self, text, start, scale, color, thickness, font = cv2.FONT_HERSHEY_PLAIN):
        cv2.putText(self.frame, text, start, font, scale, color, thickness, cv2.LINE_4)

def Matrix():
    if not VIRTUAL_ENV:
        return LiveMatrix()
    return VirtualMatrix()

