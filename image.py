import sys
from PIL import Image
from os.path import exists
from led_matrix import Matrix

usage = "Usage: sudo image.py image-name.png"
if len(sys.argv) != 2:
    print(usage)
    sys.exit()

image_file = sys.argv[1]
if not exists(image_file):
    print("Error: file not found")
    print(usage)
    sys.exit()

# The actual image
image = Image.open(image_file)

# send the image to matrix
matrix = Matrix()
matrix.image(image)
matrix.show()

# in virtual env this lets the image hang out for 5 seconds
matrix.delay(5000)
