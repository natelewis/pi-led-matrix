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

class VirtualPixelFramebuffer():
    def __init__(self):
        self.frame = 0
        self.current_rendering = False

    def image(self, img):
        self.current_rendering = False
        self.frame = np.array(img)

    def display(self):
        cv2.imshow('preview', self.frame)

        # this is the magic sauce -- waitKey runs all the cv2 handlers behind the scene
        # without this there is no rendering
        cv2.waitKey(100)

def delay(ms):
    cv2.waitKey(ms)

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
        return PixelFramebuffer(
            neopixel,
            pixel_width,
            pixel_height,
            orientation=VERTICAL
        )
    return VirtualPixelFramebuffer()

def enhance_image(image):
    color_enhance = ImageEnhance.Color(image)
    colored_image = color_enhance.enhance(color_factor)
    contrast_enhancer = ImageEnhance.Contrast(colored_image)
    return contrast_enhancer.enhance(contrast_factor)
