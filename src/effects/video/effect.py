import math
import time
from pathlib import Path

import cv2
from PIL import Image

DEFAULT_FPS = 30.0
USAGE_TEXT = (
    'Usage: make run effect=video config=\'{"file":"video-file.mp4"}\''
)
CHANNEL_INDEX = {"r": 0, "g": 1, "b": 2}


def _resolve_safe_video_path(effect_dir, raw_file):
    if not isinstance(raw_file, str) or not raw_file.strip():
        raise ValueError("Missing video file in effect config.")
    base_dir = Path(effect_dir).resolve()
    candidate = (base_dir / raw_file.strip()).resolve()
    try:
        candidate.relative_to(base_dir)
    except ValueError as exc:
        raise ValueError("Video path must reside inside the video effect directory.") from exc
    if not candidate.is_file():
        raise FileNotFoundError(f"Video file not found: {raw_file}")
    return candidate


def _resolve_fps(cap):
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or math.isnan(fps) or fps <= 0 or fps > 240:
        return DEFAULT_FPS
    return float(fps)


def _wait_until(matrix, target_time):
    """Wait until monotonic target_time while keeping virtual window events responsive."""
    while matrix.ready():
        remaining = target_time - time.monotonic()
        if remaining <= 0.001:
            return
        # Cap each wait slice so quit/skip events stay snappy
        slice_sec = min(remaining, 0.05)
        slice_ms = max(1, int(slice_sec * 1000))
        before = time.monotonic()
        matrix.delay(slice_ms)
        # On headless Pi, cv2.waitKey inside led_time.delay can return immediately
        actual_elapsed = time.monotonic() - before
        leftover = slice_sec - actual_elapsed
        if leftover > 0.001 and matrix.ready():
            time.sleep(leftover)


def run(matrix, config):
    """play video file in real time using the video's native frame rate"""
    effect_dir = config["effect_dir"]
    pixel_width = config["pixel_width"]
    pixel_height = config["pixel_height"]
    effect_cfg = config.get("effect") or {}
    if not isinstance(effect_cfg, dict):
        print("Error: invalid video effect config")
        print(USAGE_TEXT)
        raise ValueError("Invalid video effect config")

    video_path = _resolve_safe_video_path(effect_dir, effect_cfg.get("file"))
    video_file = str(video_path)
    print("Playing video file: ", video_file)

    try:
        speed = float(effect_cfg.get("speed", 1.0) or 1.0)
    except (TypeError, ValueError):
        speed = 1.0
    if not math.isfinite(speed) or speed <= 0 or speed > 16.0:
        speed = 1.0

    color_order = config.get("color_order", "rgb").lower()
    channel_order = (
        [CHANNEL_INDEX[ch] for ch in color_order] if color_order != "rgb" else None
    )

    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened():
        raise RuntimeError(f"Unable to open video file: {video_file}")

    fps = _resolve_fps(cap)
    frame_duration = 1.0 / (fps * speed)

    try:
        loop_count = 0
        while matrix.ready():
            if loop_count > 0:
                if not cap.set(cv2.CAP_PROP_POS_FRAMES, 0):
                    cap.release()
                    cap = cv2.VideoCapture(video_file)
                    if not cap.isOpened():
                        break
            loop_count += 1
            loop_start = time.monotonic()
            frame_index = 0

            while matrix.ready():
                target_time = loop_start + frame_index * frame_duration
                now = time.monotonic()

                # If rendering fell behind real time (e.g. slower physical LED refresh),
                # skip decoding stale frames via grab() to stay locked to real-world speed.
                behind_frames = int((now - target_time) / frame_duration)
                if behind_frames > 0:
                    eof = False
                    for _ in range(behind_frames):
                        if not cap.grab():
                            eof = True
                            break
                        frame_index += 1
                    if eof:
                        break
                    target_time = loop_start + frame_index * frame_duration

                has_frame, frame_bgr = cap.read()
                if not has_frame:
                    break

                frame_index += 1

                if (
                    frame_bgr.shape[1] != pixel_width
                    or frame_bgr.shape[0] != pixel_height
                ):
                    frame_bgr = cv2.resize(
                        frame_bgr,
                        (pixel_width, pixel_height),
                        interpolation=cv2.INTER_AREA,
                    )

                frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                if channel_order is not None:
                    frame_rgb = frame_rgb[:, :, channel_order]

                # Pace to the frame's real presentation timestamp before displaying
                _wait_until(matrix, target_time)
                if not matrix.ready():
                    break

                matrix.image(Image.fromarray(frame_rgb, mode="RGB"))
                # Pass delay_ms=0 so virtual_framerate (e.g. 75ms) doesn't throttle real-time video
                matrix.show(delay_ms=0)

            # Avoid a tight spin if the video has 0 decodable frames
            if frame_index == 0:
                # Try one reopen fallback in case seek-to-0 failed silently
                if loop_count > 1:
                    cap.release()
                    cap = cv2.VideoCapture(video_file)
                    if cap.isOpened():
                        loop_count = 0
                        continue
                print("Error: no readable frames in video file")
                break
    finally:
        cap.release()
