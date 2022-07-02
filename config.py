# config and mapping for virtual env vs pi with LED matrix
# Virtual env only works if it is a constant event loop
VIRTUAL_ENV = False

try:
    import board
    import neopixel
    from adafruit_pixel_framebuf import PixelFramebuffer, VERTICAL
# virtual env
except ImportError:
    import cv2
    import numpy as np
    VIRTUAL_ENV = True
    board = {}

from PIL import ImageEnhance

# all
pixel_pin = board.D18 if not VIRTUAL_ENV else 0
pixel_width = 60
pixel_height = 30
brightness = 0.2
contrast_factor = 2
color_factor = 1.5

# video
framerate = 0.3 # in seconds

# marquee
delay = 0.0 # in seconds
font_size = 1
top_padding = 4

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
class VirtualPixelFramebuffer():
    def __init__(self):
        self.frame = 0
        self.current_rendering = False

    def image(self, img):
        self.current_rendering = False
        self.frame = np.array(img)

    def display(self):
        cv2.imshow('preview', self.frame)
        cv2.waitKey(100)



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
