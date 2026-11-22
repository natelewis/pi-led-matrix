# Simple test to confirm color
# Red... Green... Blue... (Repeat)

from PIL import ImageFont

FONT_FILE = "dosis.ttf"
LABELS = [
    ("R E D", (255, 0, 0)),
    ("G R E E N", (0, 255, 0)),
    ("B L U E", (0, 0, 255)),
]


def fit_font_size(text, max_w, max_h, font_path):
    """pick the largest font size that fits inside max_w x max_h"""
    best = 6
    for size in range(6, max(7, max_h * 2)):
        bbox = ImageFont.truetype(font_path, size).getbbox(text)
        if (bbox[2] - bbox[0]) <= max_w and (bbox[3] - bbox[1]) <= max_h:
            best = size
        else:
            break
    return best


def centered_pos(text, font_size, width, height, font_path):
    """return top-left draw position so text is centered on the matrix"""
    bbox = ImageFont.truetype(font_path, font_size).getbbox(text)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    return ((width - text_w) // 2 - bbox[0], (height - text_h) // 2 - bbox[1])


def run(matrix, config):
    """red, green, blue, repeat"""
    width = config["pixel_width"]
    height = config["pixel_height"]
    font_path = "./fonts/" + FONT_FILE
    font_size = fit_font_size(
        "G R E E N", int(width * 0.9), int(height * 0.8), font_path
    )
    positions = [
        (label, color, centered_pos(label, font_size, width, height, font_path))
        for label, color in LABELS
    ]

    while matrix.ready():
        for label, color, pos in positions:
            matrix.reset()
            matrix.text(label, pos, font_size, color, FONT_FILE)
            matrix.show()
            matrix.delay(1000)
