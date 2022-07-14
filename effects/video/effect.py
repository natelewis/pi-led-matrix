import sys
import cv2
from PIL import Image
from os.path import exists

framerate = 0.3 # in seconds
usage = "Usage: ./run.sh video video-file.mp4"

def run(matrix, config):
    """play video file"""
    effect_dir = config['effect_dir']
    pixel_width = config['pixel_width']
    pixel_height = config['pixel_height']
    if len(config['argv']) != 1:
        print(usage)
        sys.exit()

    video_file = effect_dir + '/' + config['argv'][0]
    if not exists(video_file):
        print("Error: file not found")
        print(usage)
        sys.exit()

    vidcap = cv2.VideoCapture(video_file)

    def getFrame(sec):
        vidcap.set(cv2.CAP_PROP_POS_MSEC,sec * 1000)
        hasFrames,image = vidcap.read()
        if hasFrames:
            # convert data array to rgb image
            rgb_image = Image.fromarray(image, mode="RGB")
            rgb_image = rgb_image.resize((pixel_width, pixel_height))

            # swap the R & B
            r, g, b = rgb_image.split()
            rgb_image = Image.merge('RGB', (b, g, r))

            # display frame
            matrix.image(rgb_image)
            matrix.show()

        return hasFrames

    while True:
        sec = 0
        count = 1
        success = getFrame(sec)

        while success:
            count = count + 1
            sec = sec + framerate
            sec = round(sec, 2)
            success = getFrame(sec)