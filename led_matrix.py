from PIL import ImageEnhance
from config import (
    pixel_width,
    pixel_height,
    brightness,
    contrast_factor,
    color_factor,
    framerate,
)
import cv2
import types

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
    import numpy as np
    VIRTUAL_ENV = True
    board = {}

pixel_pin = board.D18 if not VIRTUAL_ENV else 0
pixel_width = pixel_width
pixel_height = pixel_height
framerate = framerate


def delay(ms):
    cv2.waitKey(ms)

def enhance(image):
    color_enhance = ImageEnhance.Color(image)
    colored_image = color_enhance.enhance(color_factor)
    contrast_enhancer = ImageEnhance.Contrast(colored_image)
    return contrast_enhancer.enhance(contrast_factor)

class VirtualPixelFramebuffer():
    def __init__(self):
        self.frame = 0
        self.current_rendering = False
        self.image = self.fill(0, 0, 0)

    def image(self, img):
        self.current_rendering = False
        self.frame = np.array(img)

    def display(self):
        cv2.imshow('preview', self.frame)

        # this is the magic sauce -- waitKey runs all the cv2 handlers behind the scene
        # without this there is no rendering
        cv2.waitKey(100)

    def fill(self, r, g, b):
        # rgb -> bgr
        self.frame = np.full([pixel_height, pixel_width, 3],[b, g, r], np.uint8)

    def delay(self, ms):
        delay(ms)

    def enhance(self):
        enhance(self.image)

    def line(self, start, end, color, width):
        cv2.line(self.frame, start, end, color, width)


def pixels():
    if not VIRTUAL_ENV:
        return neopixel.NeoPixel(
            pixel_pin,
            pixel_width * pixel_height,
            brightness=brightness,
            auto_write=False,
        )

def framebuffer():
    if not VIRTUAL_ENV:
        neopixel = pixels()
        buff = PixelFramebuffer(
            neopixel,
            pixel_width,
            pixel_height,
            orientation=VERTICAL
        )

        buff.fill = types.MethodType( fill, buff )
        buff.image = buff.fill(0, 0, 0)

        def fill(self, *args):
            neopixel.fill(args)

        def delay(self, *args):
            delay(args)

        def enhance(self):
            enhance(self.image)

        def line(self, start, end, color, width):
            cv2.line(self.image, start, end, color, width)

        return buff

    # not on pi, virtual matrix
    return VirtualPixelFramebuffer()


