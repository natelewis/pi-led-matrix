import json
import os
import sys
import warnings

from PIL import Image
import numpy as np
import cv2


from lib import led_color, led_image, led_time, led_text


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


# alternating determines if the LED matrix is wired in a zigzag pattern
alternating = cfg["alternating"]

# framerate between renderings in milliseconds in virtual mode
# this mimics the delay of hardware latency
virtual_framerate = cfg["virtual_framerate"]

# virtual display options (set virtual=true to force monitor mode on a Pi)
virtual_mode = cfg.get("virtual", False) or os.environ.get("VIRTUAL_MATRIX") == "1"
virtual_fullscreen = cfg.get("virtual_fullscreen", False)
virtual_led_dots = cfg.get("virtual_led_dots", True)

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
VIRTUAL_ENV = virtual_mode

VIRTUAL_SIZE_MULTIPLIER = 10

if not VIRTUAL_ENV:
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
else:
    board = MockBoard()

# color rgb swap, default is string 'rgb' which does not swap any color
color_order = "rgb" if VIRTUAL_ENV else cfg["color_order"]


class VirtualMatrix:
    def __init__(self):
        os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        if (
            sys.platform.startswith("linux")
            and not os.environ.get("DISPLAY")
            and not os.environ.get("WAYLAND_DISPLAY")
        ):
            os.environ["DISPLAY"] = ":0"

        warnings.filterwarnings(
            "ignore", message=".*neon capable.*", category=RuntimeWarning
        )
        import pygame  # pylint: disable=import-outside-toplevel

        self.pygame = pygame
        self.pygame.init()

        self.frame = []
        self.fullscreen = virtual_fullscreen
        self.led_dots = virtual_led_dots
        self.screen = None
        self.layout = {}

        self._init_display()
        self.reset()
        self.start_time = led_time.get_start_time()

    def _init_display(self):
        if self.fullscreen:
            self.screen = self.pygame.display.set_mode((0, 0), self.pygame.FULLSCREEN)
            self.pygame.mouse.set_visible(False)
        else:
            self.screen = self.pygame.display.set_mode(
                (
                    pixel_width * VIRTUAL_SIZE_MULTIPLIER,
                    pixel_height * VIRTUAL_SIZE_MULTIPLIER,
                ),
                self.pygame.RESIZABLE,
            )
            self.pygame.mouse.set_visible(True)
        self.pygame.display.set_caption("LED Matrix")
        self._update_layout()

    def _update_layout(self):
        win_w, win_h = self.screen.get_size()
        cell = max(1, min(win_w // pixel_width, win_h // pixel_height))
        draw_w = pixel_width * cell
        draw_h = pixel_height * cell

        dot_mask = None
        if self.led_dots and cell >= 4:
            row_grid, col_grid = np.ogrid[:cell, :cell]
            center = (cell - 1) / 2.0
            radius = cell * 0.42
            dot = (
                ((col_grid - center) ** 2 + (row_grid - center) ** 2) <= radius * radius
            ).astype(np.uint8)
            dot_mask = np.tile(dot, (pixel_height, pixel_width))[:, :, np.newaxis]

        self.layout = {
            "cell": cell,
            "draw_w": draw_w,
            "draw_h": draw_h,
            "offset_x": (win_w - draw_w) // 2,
            "offset_y": (win_h - draw_h) // 2,
            "dot_mask": dot_mask,
        }

    def _poll_events(self):
        for event in self.pygame.event.get():
            if event.type == self.pygame.QUIT:
                self.pygame.quit()
                sys.exit(0)
            if event.type == self.pygame.VIDEORESIZE and not self.fullscreen:
                self._update_layout()
            if event.type == self.pygame.KEYDOWN:
                if event.key in (self.pygame.K_ESCAPE, self.pygame.K_q):
                    self.pygame.quit()
                    sys.exit(0)
                if event.key == self.pygame.K_f:
                    self.fullscreen = not self.fullscreen
                    self._init_display()
                if event.key == self.pygame.K_d:
                    self.led_dots = not self.led_dots
                    self._update_layout()
                if event.key in (
                    self.pygame.K_n,
                    self.pygame.K_SPACE,
                    self.pygame.K_RIGHT,
                ):
                    self.start_time = 0

    def close(self):
        self.pygame.quit()

    def reset_timer(self):
        self.start_time = led_time.get_start_time()

    def ready(self):
        return led_time.ready(self.start_time, playlist_delay)

    def color(self, color_name):
        return led_color.COLOR_MAP[color_name]

    def random_color(self):
        return led_color.random_color()

    def swap_colors(self, rgb_color, swapped_color_order):
        return led_color.swap_colors(rgb_color, swapped_color_order)

    def image(self, img):
        rgb_image = img.convert("RGB")
        if rgb_image.size != (pixel_width, pixel_height):
            rgb_image = rgb_image.resize((pixel_width, pixel_height), Image.NEAREST)
        self.frame = np.array(rgb_image)

    def show(self):
        self._poll_events()

        cell = self.layout["cell"]
        enhanced = led_image.enhance(self.frame, color, contrast)
        scaled = np.repeat(np.repeat(enhanced, cell, axis=0), cell, axis=1)
        if self.layout["dot_mask"] is not None:
            scaled *= self.layout["dot_mask"]

        surface = self.pygame.image.frombuffer(
            scaled,
            (self.layout["draw_w"], self.layout["draw_h"]),
            "RGB",
        )
        self.screen.fill((0, 0, 0))
        self.screen.blit(surface, (self.layout["offset_x"], self.layout["offset_y"]))
        self.pygame.display.flip()

        self.delay(virtual_framerate)

    def reset(self, rgb_color=(0, 0, 0)):
        self.frame = np.full([pixel_height, pixel_width, 3], rgb_color, np.uint8)

    def delay(self, ms):
        remaining = int(ms)
        while remaining > 0 and self.start_time != 0:
            self._poll_events()
            step = min(remaining, 25)
            self.pygame.time.wait(step)
            remaining -= step

    def line(self, start, end, rgb_color, width):
        cv2.line(self.frame, start, end, rgb_color, width)

    def pixel(self, start, rgb_color):
        cv2.line(self.frame, start, start, rgb_color, 1)

    def rectangle(self, start, end, rgb_color, width):
        cv2.rectangle(self.frame, start, end, rgb_color, width)

    def circle(self, center, radius, rgb_color, width):
        cv2.circle(self.frame, center, radius, rgb_color, width)

    def polylines(self, points, rgb_color, width):
        cv2.polylines(self.frame, points, True, self.bgr_color_swap(rgb_color), width)

    def polyfill(self, points, rgb_color):
        cv2.fillPoly(self.frame, points, self.bgr_color_swap(rgb_color))

    def text(self, message, start, font_size, rgb_color, font="dosis.ttf"):
        led_text.text(self, message, start, font_size, rgb_color, font)

    def sprite(self, sprite_map, start, color_map):
        led_image.sprite(self, sprite_map, start, color_map)


def pixels(pixel_pin=board.D18):
    if not VIRTUAL_ENV:
        return neopixel.NeoPixel(
            pixel_pin,
            pixel_width * pixel_height,
            brightness=brightness,
            auto_write=False,
        )
    return None


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
        self.start_time = led_time.get_start_time()

    def ready(self):
        return led_time.ready(self.start_time, playlist_delay)

    def color(self, color_name):
        return led_color.COLOR_MAP[color_name]

    def random_color(self):
        return led_color.random_color()

    def swap_colors(self, rgb_color, swapped_color_order):
        return led_color.swap_colors(rgb_color, swapped_color_order)

    def reset(self, rgb_color=(0, 0, 0)):
        self.frame = led_image.reset(
            led_color.swap_colors(rgb_color, color_order), pixel_height, pixel_width
        )

    def image(self, img):
        rgb_image = img.convert("RGB")
        self.frame = np.array(rgb_image)

    def line(self, start, end, rgb_color, width):
        cv2.line(
            self.frame, start, end, led_color.swap_colors(rgb_color, color_order), width
        )

    def pixel(self, start, rgb_color):
        cv2.line(
            self.frame, start, start, led_color.swap_colors(rgb_color, color_order), 1
        )

    def rectangle(self, start, end, rgb_color, width):
        cv2.rectangle(
            self.frame, start, end, led_color.swap_colors(rgb_color, color_order), width
        )

    def circle(self, center, radius, rgb_color, width):
        cv2.circle(
            self.frame,
            center,
            radius,
            led_color.swap_colors(rgb_color, color_order),
            width,
        )

    def polylines(self, points, rgb_color, width):
        cv2.polylines(
            self.frame,
            points,
            True,
            led_color.swap_colors(rgb_color, color_order),
            width,
        )

    def polyfill(self, points, rgb_color):
        cv2.fillPoly(self.frame, points, led_color.swap_colors(rgb_color, color_order))

    def delay(self, ms):
        led_time.delay(ms)

    def sprite(self, sprite_map, start, color_map):
        led_image.sprite(self, sprite_map, start, color_map)

    def show(self):
        for index, _ in enumerate(pixel_pins):
            # Calculate start and end positions for slicing the frame
            start_x = index * self.panel_width
            end_x = start_x + self.panel_width

            # Slice the frame to get the current panel
            panel_frame = self.frame[:, start_x:end_x]

            img = Image.fromarray(
                led_image.enhance(panel_frame, color, contrast), mode="RGB"
            )
            self.buffers[index].image(img)

        for index, _ in enumerate(pixel_pins):
            self.buffers[index].display()

    def text(self, message, start, font_size, rgb_color, font="dosis.ttf"):
        led_text.text(
            self,
            message,
            start,
            font_size,
            led_color.swap_colors(rgb_color, color_order),
            font,
        )


# return the class for your env
def Matrix():  # pylint: disable=invalid-name
    if not VIRTUAL_ENV:
        return LiveMatrix()
    return VirtualMatrix()
