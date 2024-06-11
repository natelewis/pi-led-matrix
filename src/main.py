import json
import cv2
import numpy as np

from os.path import exists

from PIL import Image
from src.lib import image, text, color as color_lib, time


class MockBoard:
    D18 = "Mock D18"


CUSTOM_CONFIG = exists("config.json")
print(f'Using {"custom" if CUSTOM_CONFIG else "default"} config file')

CONFIG = "default_config.json" if not CUSTOM_CONFIG else "config.json"

with open(CONFIG, mode="r", encoding="utf8") as j_object:
    cfg = json.load(j_object)

# size of matrix
pixel_width = cfg["pixel_width"]
pixel_height = cfg["pixel_height"]

# brightness 0 - 1
brightness = cfg["brightness"]

# contrast (1 is no change)
contrast = cfg["contrast"]

# color (1 is no change)
color = cfg["color"]

# color rgb swap, default is string 'rgb' which does not swap any color
color_order = cfg["color_order"]

# alternating determines if the LED matrix is wired in a zigzag pattern
alternating = cfg["alternating"]

# framerate between renderings in milliseconds in virtual mode
# this mimics the delay of hardware latency
virtual_framerate = cfg["virtual_framerate"]

# playlists follow this format:
# [
#    {'effect': 'video', 'argv': ['cartoon-60x30.mp4']},
#    {'effect': 'image', 'argv': ['josie-60x30.png']},
#    {'effect': 'snow', 'argv': []},
#    {'effect': 'water_ripple', 'argv':[]},
# ]
playlist = cfg["playlist"]
playlist_delay = cfg["playlist_delay"]

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
    # mock the board module for the virtual env
    board = MockBoard()


class VirtualMatrix:
    def __init__(self):
        self.frame = []
        self.reset()
        self.start_time = time.get_start_time()

    def ready(self):
        return time.ready(self.start_time, playlist_delay)

    def color(self, color_name):
        return color_lib.COLOR_MAP[color_name]

    def random_color(self):
        return color_lib.random_color()

    def image(self, img):
        rgb_image = img.convert("RGB")
        self.frame = np.array(rgb_image)

    def show(self):
        frame = cv2.resize(
            self.frame,
            (
                pixel_width * VIRTUAL_SIZE_MULTIPLIER,
                pixel_height * VIRTUAL_SIZE_MULTIPLIER,
            ),
        )
        cv2.imshow("LED matrix", image.enhance(frame, color, contrast))

        # this is the magic sauce -- waitKey runs all the cv2 handlers behind the scene
        # without this there is no rendering
        cv2.waitKey(virtual_framerate)

    def reset(self, rgb_color=(0, 0, 0)):
        self.frame = image.reset(rgb_color, pixel_height, pixel_width)

    def delay(self, ms):
        time.delay(ms)

    def line(self, start, end, rgb_color, width):
        cv2.line(self.frame, start, end, color_lib.swap_colors(rgb_color, "bgr"), width)

    def pixel(self, start, rgb_color):
        cv2.line(self.frame, start, start, color_lib.swap_colors(rgb_color, "bgr"), 1)

    def rectangle(self, start, end, rgb_color, width):
        cv2.rectangle(
            self.frame, start, end, color_lib.swap_colors(rgb_color, "bgr"), width
        )

    def circle(self, center, radius, rgb_color, width):
        cv2.circle(
            self.frame, center, radius, color_lib.swap_colors(rgb_color, "bgr"), width
        )

    def text(self, message, start, font_size, rgb_color, font="dosis.ttf"):
        text.text(
            self,
            message,
            start,
            font_size,
            color_lib.swap_colors(rgb_color, "bgr"),
            font,
        )

    def sprite(self, sprite_map, start, color_map):
        image.sprite(self, sprite_map, start, color_map)


# NeoPixels must be connected to D10, D12, D18 or D21
def pixels(pixel_pin=board.D18):
    if not VIRTUAL_ENV:
        return neopixel.NeoPixel(
            pixel_pin,
            pixel_width * pixel_height,
            brightness=brightness,
            auto_write=False,
        )


class LiveMatrix:
    def __init__(self):
        self.frame = []
        self.reset()
        neopixel_pixels = pixels()
        self.buff = PixelFramebuffer(
            neopixel_pixels,
            pixel_width,
            pixel_height,
            orientation=VERTICAL,
            alternating=alternating,
        )
        self.start_time = time.get_start_time()

    def ready(self):
        return time.ready(self.start_time, playlist_delay)

    def color(self, color_name):
        return color_lib.COLOR_MAP[color_name]

    def random_color(self):
        return color_lib.random_color()

    def reset(self, rgb_color=(0, 0, 0)):
        self.frame = image.reset(rgb_color, pixel_height, pixel_width)

    def image(self, img):
        rgb_image = img.convert("RGB")
        self.frame = np.array(rgb_image)

    def line(self, start, end, rgb_color, width):
        cv2.line(
            self.frame, start, end, color_lib.swap_colors(rgb_color, color_order), width
        )

    def pixel(self, start, rgb_color):
        cv2.line(
            self.frame, start, start, color_lib.swap_colors(rgb_color, color_order), 1
        )

    def rectangle(self, start, end, rgb_color, width):
        cv2.rectangle(
            self.frame, start, end, color_lib.swap_colors(rgb_color, color_order), width
        )

    def circle(self, center, radius, rgb_color, width):
        cv2.circle(
            self.frame,
            center,
            radius,
            color_lib.swap_colors(rgb_color, color_order),
            width,
        )

    def delay(self, ms):
        time.delay(ms)

    def sprite(self, sprite_map, start, color_map):
        image.sprite(self, sprite_map, start, color_map)

    def show(self):
        img = Image.fromarray(image.enhance(self.frame, color, contrast), mode="RGB")
        self.buff.image(img)
        self.buff.display()

    def text(self, message, start, font_size, rgb_color, font="dosis.ttf"):
        text.text(
            self,
            message,
            start,
            font_size,
            color_lib.swap_colors(rgb_color, color_order),
            font,
        )


# return the class for your env
def Matrix():  # pylint: disable=invalid-name
    if not VIRTUAL_ENV:
        return LiveMatrix()
    return VirtualMatrix()
