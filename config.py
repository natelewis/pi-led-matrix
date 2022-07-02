import board
import neopixel
from PIL import ImageEnhance
from adafruit_pixel_framebuf import PixelFramebuffer, VERTICAL

# all
pixel_pin = board.D18
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

def pixels():
    return neopixel.NeoPixel(
        pixel_pin,
        pixel_width * pixel_height,
        brightness=brightness,
        auto_write=False,
    )

def framebuffer():
    neopixel = pixels()
    return PixelFramebuffer(
        neopixel,
        pixel_width,
        pixel_height,
        orientation=VERTICAL
    )

def enhance_image(image):
    color_enhance = ImageEnhance.Color(image)
    colored_image = color_enhance.enhance(color_factor)
    contrast_enhancer = ImageEnhance.Contrast(colored_image)
    return contrast_enhancer.enhance(contrast_factor)
