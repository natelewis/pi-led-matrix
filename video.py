import sys
import cv2
from PIL import Image
from os.path import exists
from config import enhance_image, framebuffer, pixel_height, pixel_width, framerate


usage = "Usage: sudo video.py video-file.png"
if len(sys.argv) != 2:
    print(usage)
    sys.exit()

video_file = sys.argv[1]
if not exists(video_file):
    print("Error: file not found")
    print(usage)
    sys.exit()

framebuf = framebuffer();
vidcap = cv2.VideoCapture(video_file)

def getFrame(sec):
    vidcap.set(cv2.CAP_PROP_POS_MSEC,sec*1000)
    hasFrames,image = vidcap.read()
    if hasFrames:
        # convert data array to rgb image
        rgb_image = Image.fromarray(image, mode="RGB")
        rgb_image = rgb_image.resize((pixel_width, pixel_height))

        # swap the R & B
        r, g, b = rgb_image.split()
        rgb_image = Image.merge('RGB', (b, g, r))

        # fix the color a bit
        enhanced_image = enhance_image(rgb_image);

        # display frame
        framebuf.image(enhanced_image)
        framebuf.display()
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



