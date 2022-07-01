import board
import neopixel
import time
from adafruit_pixel_framebuf import PixelFramebuffer, VERTICAL

import sys
from os.path import exists
from config import framebuffer, pixel_height, pixel_width, delay, top_padding, font_size

usage = 'Usage: sudo image.py "my message"'
if len(sys.argv) != 2:
    print(usage)
    sys.exit()

message = sys.argv[1]

framebuf = framebuffer()
message_length = len(message);
marquee_size = message_length * font_size * 6;

def display_text(x, y):
    framebuf.fill(0x000000)
    framebuf.text(message, x, y, 0x0000FF, size=font_size)
    framebuf.display()

while True:
    for x in range(marquee_size, -marquee_size, -1):
        display_text(x, top_padding)
        time.sleep(delay);
