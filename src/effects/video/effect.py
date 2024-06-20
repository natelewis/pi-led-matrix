import sys
from os.path import exists

import cv2
from PIL import Image

FRAMERATE = 0.3  # in seconds
USAGE_TEXT = "Usage: ./run.sh video video-file.mp4"


def run(matrix, config):
    """play video file"""
    effect_dir = config["effect_dir"]
    pixel_width = config["pixel_width"]
    pixel_height = config["pixel_height"]
    video_file = effect_dir + "/" + config["effect"]["file"]

    print("Playing video file: ", video_file)

    if not exists(video_file):
        print("Error: file not found")
        print(USAGE_TEXT)
        sys.exit()

    cap = cv2.VideoCapture(video_file)

    def get_frame(sec):
        cap.set(cv2.CAP_PROP_POS_MSEC, sec * 1000)
        has_frames, image = cap.read()

        if has_frames:
            # convert data array to rgb image
            rgb_image = Image.fromarray(image, mode="RGB")
            rgb_image = rgb_image.resize((pixel_width, pixel_height))

            r, g, b = rgb_image.split()
            color_corrected_image = Image.merge(
                "RGB", matrix.swap_colors((b, g, r), config["color_order"])
            )

            # display frame
            matrix.image(color_corrected_image)
            matrix.show()

        return has_frames

    while True:
        sec = 0
        count = 1
        success = get_frame(sec)

        while success:
            count = count + 1
            sec = sec + FRAMERATE
            sec = round(sec, 2)
            success = get_frame(sec)
