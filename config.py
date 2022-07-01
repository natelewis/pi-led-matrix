import board
import neopixel
from adafruit_pixel_framebuf import PixelFramebuffer, VERTICAL

# all
pixel_pin = board.D18
pixel_width = 60
pixel_height = 30
brightness = 0.1

# video
framerate = 0.1 # in seconds

# marquee
delay = 0.0 # in seconds
font_size = 3
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
