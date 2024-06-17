import json
import os


import cv2
import numpy as np
from PIL import Image

from lib import color as color_lib
from lib import image, text, time


class MockBoard:  # pylint: disable=too-few-public-methods
    """
    A mock board class representing a virtual board.

    This class provides a mock implementation of a board, specifically for use in the
    virtual environment.

    Attributes:
        D18 (str): A string representing the D18 pin of the mock board.
    """

    D18 = "Mock D18"


CUSTOM_CONFIG = os.path.exists("config.json")
CONFIG = "default_config.json" if not CUSTOM_CONFIG else "config.json"

print(
    f'Using {"custom" if CUSTOM_CONFIG else "default"} config file: '
    + os.getcwd()
    + "/"
    + CONFIG
)

with open(CONFIG, mode="r", encoding="utf8") as j_object:
    cfg = json.load(j_object)

# array of pixel pins for the LED matrix
# valid values for neoPixels are "D10", "D12", "D18" or "D21"
pixel_pins = cfg["pixel_pins"]

# size of matrix - this should be the full width and height of the LED matrix
# if using multiple pins to display more than one matrix then this should be
# the full width and height of all the matrices
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
    from adafruit_pixel_framebuf import VERTICAL, PixelFramebuffer
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
        panel_width = self.frame.shape[1] // len(
            pixel_pins
        )  # Calculate the width of each panel
        for index, _ in enumerate(pixel_pins):
            # Calculate start and end positions for slicing the frame
            start_x = index * panel_width
            end_x = start_x + panel_width

            # Slice the frame to get the current panel
            panel_frame = self.frame[:, start_x:end_x]

            frame = cv2.resize(
                panel_frame,
                (
                    panel_width * VIRTUAL_SIZE_MULTIPLIER,
                    pixel_height * VIRTUAL_SIZE_MULTIPLIER,
                ),
            )
            cv2.imshow(f"LED matrix {index}", image.enhance(frame, color, contrast))

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
        self.buffers = []  # List to hold PixelFramebuffer instances
        self.panel_width = self.frame.shape[1] // len(pixel_pins)
        for pin_name in pixel_pins:
            pin = getattr(board, pin_name)
            buffer = PixelFramebuffer(
                neopixel.NeoPixel(
                    pin,
                    self.panel_width * pixel_height,
                    brightness=brightness,
                    auto_write=False,
                ),
                self.panel_width,
                pixel_height,
                orientation=VERTICAL,
                alternating=alternating,
            )
            self.buffers.append(buffer)
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
        for index, _ in enumerate(pixel_pins):
            # Calculate start and end positions for slicing the frame
            start_x = index * self.panel_width
            end_x = start_x + self.panel_width

            # Slice the frame to get the current panel
            panel_frame = self.frame[:, start_x:end_x]

            img = Image.fromarray(
                image.enhance(panel_frame, color, contrast), mode="RGB"
            )
            self.buffers[index].image(img)

        for index, _ in enumerate(pixel_pins):
            self.buffers[index].display()

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
