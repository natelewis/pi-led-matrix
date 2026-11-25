import json
import os
import sys
import time
import warnings

from PIL import Image
import numpy as np
import cv2


from lib import led_color, led_image, led_time, led_text, runtime_ipc

FRAME_MIRROR_INTERVAL_SEC = 0.12  # ~8 FPS max snapshot rate for Studio live mirror


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


def reload_config():
    """Reload config.json (or default_config.json) into module globals at runtime."""
    global CUSTOM_CONFIG, CONFIG, cfg
    global pixel_pins, pixel_width, pixel_height
    global brightness, contrast, color, alternating
    global virtual_framerate, virtual_mode, virtual_fullscreen, virtual_led_dots
    global playlist, playlist_delay, color_order

    CUSTOM_CONFIG = os.path.exists("config.json")
    CONFIG = "default_config.json" if not CUSTOM_CONFIG else "config.json"
    with open(CONFIG, mode="r", encoding="utf8") as handle:
        new_cfg = json.load(handle)

    prev_dims = (pixel_width, pixel_height)
    cfg = new_cfg
    pixel_pins = cfg["pixel_pins"]
    pixel_width = cfg["pixel_width"]
    pixel_height = cfg["pixel_height"]
    brightness = cfg["brightness"]
    contrast = cfg["contrast"]
    color = cfg["color"]
    alternating = cfg["alternating"]
    virtual_framerate = cfg["virtual_framerate"]
    virtual_mode = cfg.get("virtual", False) or os.environ.get("VIRTUAL_MATRIX") == "1"
    virtual_fullscreen = cfg.get("virtual_fullscreen", False)
    virtual_led_dots = cfg.get("virtual_led_dots", True)
    playlist = cfg["playlist"]
    playlist_delay = cfg["playlist_delay"]
    color_order = "rgb" if VIRTUAL_ENV else cfg["color_order"]

    return {
        "dims_changed": prev_dims != (pixel_width, pixel_height),
        "cfg": cfg,
    }


class VirtualMatrix:
    def __init__(self):
        os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        if (
            sys.platform.startswith("linux")
            and not os.environ.get("DISPLAY")
            and not os.environ.get("WAYLAND_DISPLAY")
        ):
            os.environ["DISPLAY"] = ":0"

        # Prefer native Wayland over XWayland when WAYLAND_DISPLAY is present to avoid
        # X11 RandR BadRROutput crashes on HDMI blanking/hotplug; fall back if unavailable.
        auto_wayland = (
            sys.platform.startswith("linux")
            and bool(os.environ.get("WAYLAND_DISPLAY"))
            and not os.environ.get("SDL_VIDEODRIVER")
        )
        if auto_wayland:
            os.environ["SDL_VIDEODRIVER"] = "wayland"

        warnings.filterwarnings(
            "ignore", message=".*neon capable.*", category=RuntimeWarning
        )
        import pygame  # pylint: disable=import-outside-toplevel

        self.pygame = pygame
        self.pygame.init()
        if auto_wayland and not self.pygame.display.get_init():
            os.environ.pop("SDL_VIDEODRIVER", None)
            self.pygame.init()

        self.frame = []
        self.fullscreen = virtual_fullscreen
        self.led_dots = virtual_led_dots
        self.screen = None
        self.layout = {}

        self._init_display()
        self.reset()
        self.start_time = led_time.get_start_time()
        self._last_show_time = None
        self._last_mirror_time = 0.0
        self._interrupt_check = None
        self._last_interrupt_poll = 0.0
        self._interrupted = False

    def set_interrupt_check(self, fn):
        self._interrupt_check = fn

    def apply_runtime_config(self, dims_changed=False):
        needs_reinit = dims_changed or (self.fullscreen != virtual_fullscreen)
        dots_changed = self.led_dots != virtual_led_dots
        self.fullscreen = virtual_fullscreen
        self.led_dots = virtual_led_dots
        if needs_reinit:
            self._init_display()
            self.reset()
        elif dots_changed:
            self._update_layout()

    def _check_interrupt(self):
        if self._interrupted:
            return True
        if self._interrupt_check is None:
            return False
        now = time.monotonic()
        if now - self._last_interrupt_poll >= 0.08:
            self._last_interrupt_poll = now
            if self._interrupt_check():
                self._interrupted = True
                self.start_time = 0
                return True
        return False

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

    @staticmethod
    def _build_dot_mask(draw_w, draw_h):
        step_x = draw_w / pixel_width
        step_y = draw_h / pixel_height
        x_idx = np.arange(draw_w, dtype=np.int64)
        y_idx = np.arange(draw_h, dtype=np.int64)
        dx = (x_idx + 0.5) - (((x_idx * pixel_width) // draw_w) + 0.5) * step_x
        dy = (y_idx + 0.5) - (((y_idx * pixel_height) // draw_h) + 0.5) * step_y
        radius = min(step_x, step_y) * 0.42
        mask = (
            ((dx[np.newaxis, :] ** 2 + dy[:, np.newaxis] ** 2) <= radius * radius)
            .astype(np.uint8)
            * 255
        )
        return np.repeat(mask[:, :, np.newaxis], 3, axis=2)

    def _update_layout(self):
        raw_w, raw_h = self.screen.get_size()
        win_w = max(1, raw_w)
        win_h = max(1, raw_h)
        scale = min(win_w / pixel_width, win_h / pixel_height)
        draw_w = max(1, min(win_w, int(round(pixel_width * scale))))
        draw_h = max(1, min(win_h, int(round(pixel_height * scale))))

        dot_mask = None
        if self.led_dots and scale >= 4:
            dot_mask = self._build_dot_mask(draw_w, draw_h)

        self.layout = {
            "win_w": raw_w,
            "win_h": raw_h,
            "draw_w": draw_w,
            "draw_h": draw_h,
            "offset_x": (win_w - draw_w) // 2,
            "offset_y": (win_h - draw_h) // 2,
            "dot_mask": dot_mask,
        }

    def _poll_events(self):
        resize_events = (self.pygame.VIDEORESIZE,)
        win_size_changed = getattr(self.pygame, "WINDOWSIZECHANGED", None)
        if win_size_changed is not None:
            resize_events = (self.pygame.VIDEORESIZE, win_size_changed)

        for event in self.pygame.event.get():
            if event.type == self.pygame.QUIT:
                self.pygame.quit()
                sys.exit(0)
            if event.type in resize_events:
                if self.screen.get_size() != (
                    self.layout.get("win_w"),
                    self.layout.get("win_h"),
                ):
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
        self._last_show_time = None
        self._interrupted = False

    def ready(self):
        if self._check_interrupt():
            return False
        return led_time.ready(self.start_time, playlist_delay)

    def color(self, color_name):
        return led_color.COLOR_MAP[color_name]

    def parse_color(self, value, default=(255, 255, 255)):
        return led_color.parse_color(value, default)

    def random_color(self):
        return led_color.random_color()

    def swap_colors(self, rgb_color, swapped_color_order):
        return led_color.swap_colors(rgb_color, swapped_color_order)

    def image(self, img):
        rgb_image = img.convert("RGB")
        if rgb_image.size != (pixel_width, pixel_height):
            rgb_image = rgb_image.resize((pixel_width, pixel_height), Image.NEAREST)
        self.frame = np.array(rgb_image)

    def show(self, delay_ms=None):
        self._poll_events()

        # Frame-budgeted pacing BEFORE building the surface so any runtime
        # layout changes triggered during delay() apply to this frame cleanly.
        if delay_ms is None:
            if self._last_show_time is not None and virtual_framerate > 0:
                elapsed_ms = (time.monotonic() - self._last_show_time) * 1000.0
                remaining_ms = int(round(virtual_framerate - elapsed_ms))
                if remaining_ms > 0:
                    self.delay(remaining_ms)
        elif delay_ms > 0:
            self.delay(delay_ms)

        enhanced = led_image.enhance(self.frame, color, contrast)
        scaled = cv2.resize(
            enhanced,
            (self.layout["draw_w"], self.layout["draw_h"]),
            interpolation=cv2.INTER_NEAREST,
        )
        if self.layout["dot_mask"] is not None:
            cv2.bitwise_and(scaled, self.layout["dot_mask"], dst=scaled)

        surface = self.pygame.image.frombuffer(
            scaled,
            (self.layout["draw_w"], self.layout["draw_h"]),
            "RGB",
        )

        self.screen.fill((0, 0, 0))
        self.screen.blit(surface, (self.layout["offset_x"], self.layout["offset_y"]))
        self.pygame.display.flip()
        now = time.monotonic()
        self._last_show_time = now
        if now - self._last_mirror_time >= FRAME_MIRROR_INTERVAL_SEC:
            self._last_mirror_time = now
            runtime_ipc.write_frame_snapshot(enhanced)

    def reset(self, rgb_color=(0, 0, 0)):
        self.frame = np.full([pixel_height, pixel_width, 3], rgb_color, np.uint8)

    def delay(self, ms):
        remaining = int(ms)
        while remaining > 0 and self.start_time != 0:
            self._poll_events()
            if self._check_interrupt():
                break
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
        cv2.polylines(self.frame, points, True, rgb_color, width)

    def polyfill(self, points, rgb_color):
        cv2.fillPoly(self.frame, points, rgb_color)

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
        self._last_mirror_time = 0.0

    def ready(self):
        return led_time.ready(self.start_time, playlist_delay)

    def color(self, color_name):
        return led_color.COLOR_MAP[color_name]

    def parse_color(self, value, default=(255, 255, 255)):
        return led_color.parse_color(value, default)

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
        if rgb_image.size != (pixel_width, pixel_height):
            rgb_image = rgb_image.resize((pixel_width, pixel_height), Image.NEAREST)
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

    def show(self, delay_ms=None):
        enhanced_panels = []
        for index, _ in enumerate(pixel_pins):
            # Calculate start and end positions for slicing the frame
            start_x = index * self.panel_width
            end_x = start_x + self.panel_width

            # Slice the frame to get the current panel
            panel_frame = self.frame[:, start_x:end_x]
            enhanced_panel = led_image.enhance(panel_frame, color, contrast)
            enhanced_panels.append(enhanced_panel)

            img = Image.fromarray(enhanced_panel, mode="RGB")
            self.buffers[index].image(img)

        for index, _ in enumerate(pixel_pins):
            self.buffers[index].display()

        now = time.monotonic()
        if (
            now - self._last_mirror_time >= FRAME_MIRROR_INTERVAL_SEC
            and runtime_ipc.is_mirror_active()
        ):
            self._last_mirror_time = now
            mirror_frame = (
                enhanced_panels[0]
                if len(enhanced_panels) == 1
                else np.concatenate(enhanced_panels, axis=1)
            )
            if color_order != "rgb":
                # Un-swap channels back to true RGB for the remote Studio preview
                inv = [color_order.index("r"), color_order.index("g"), color_order.index("b")]
                mirror_frame = mirror_frame[:, :, inv]
            runtime_ipc.write_frame_snapshot(mirror_frame)

        if delay_ms is not None and delay_ms > 0:
            self.delay(delay_ms)

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
