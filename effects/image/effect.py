import sys
from PIL import Image
from os.path import exists

def run(matrix, config):
    """show an png image"""
    effect_dir = config['effect_dir']
    usage = "Usage: ./run.sh image image-name.png"
    if len(config['argv']) != 1:
        print(usage)
        sys.exit()

    image_file = effect_dir + '/' + config['argv'][0]
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
