import sys
from os.path import exists

from PIL import Image


def run(matrix, config):
    """show an png image"""
    effect_dir = config["effect_dir"]
    usage = "Usage: make run effect=image config='{file: 'image-name.png'}"

    image_file = effect_dir + "/" + config["effect"]["file"]
    if not exists(image_file):
        print("Error: file not found")
        print(usage)
        sys.exit()

    # The actual image
    image = Image.open(image_file)

    # send the image to matrix
    matrix.image(image)
    matrix.show()

    # in virtual env this lets the image hang out for 5 seconds
    matrix.delay(5000)
