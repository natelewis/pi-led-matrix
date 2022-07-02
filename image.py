import sys
from PIL import Image
from os.path import exists
from led_matrix import framebuffer, enhance_image, pixel_height, pixel_width, delay

usage = "Usage: sudo image.py image-name.png"
if len(sys.argv) != 2:
    print(usage)
    sys.exit()

image_file = sys.argv[1]
if not exists(image_file):
    print("Error: file not found")
    print(usage)
    sys.exit()

# black image background in RGBA Mode
image = Image.new("RGBA", (pixel_width, pixel_height))

# The actual image
image_layer = Image.open(image_file)

# alpha blend the icon onto the background
image.alpha_composite(image_layer)

# correct the color
enhanced_image = enhance_image(image)

# send the image to framebuffer while converting it to RGB mode
framebuf = framebuffer()
framebuf.image(enhanced_image.convert("RGB"))
framebuf.display()

# in virtual env this lets the image hang out for 5 seconds
delay(5000)