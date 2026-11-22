#
# Broadway Lights
# 3 January 2023
#

from PIL import ImageFont

FONT_FILE = "dosis.ttf"


def build_border(max_x, max_y):
    """generate evenly spaced symmetric border coordinates"""
    margin = max(2, min(max_x, max_y) // 16)
    step = 2

    left = margin
    right = max_x - 1 - margin
    top = margin
    bottom = max_y - 1 - margin

    # align spans to multiples of step so all four corners meet cleanly
    right -= (right - left) % step
    bottom -= (bottom - top) % step

    coords = []
    for x in range(left, right, step):
        coords.append((x, top))
    for y in range(top, bottom, step):
        coords.append((right, y))
    for x in range(right, left, -step):
        coords.append((x, bottom))
    for y in range(bottom, top, -step):
        coords.append((left, y))
    return coords, (left, top, right, bottom)


def fit_font_size(text, max_w, max_h, font_path):
    """pick the largest font size that fits inside max_w x max_h"""
    best = 4
    for size in range(4, max(5, max_h * 2)):
        bbox = ImageFont.truetype(font_path, size).getbbox(text)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        if width <= max_w and height <= max_h:
            best = size
        else:
            break
    return best


def layout_text(bounds, max_x, max_y):
    """compute font sizes and centered positions for 'The BEVERLY'"""
    left, top, right, bottom = bounds
    pad = max(2, min(max_x, max_y) // 12)
    inner_w = max(8, (right - left) - 2 * pad)
    inner_h = max(8, (bottom - top) - 2 * pad)

    font_path = "./fonts/" + FONT_FILE
    title_size = fit_font_size("BEVERLY", inner_w, int(inner_h * 0.65), font_path)
    sub_fit = fit_font_size("The", inner_w, int(inner_h * 0.3), font_path)
    sub_size = max(4, min(title_size // 2, sub_fit))

    sub_box = ImageFont.truetype(font_path, sub_size).getbbox("The")
    title_box = ImageFont.truetype(font_path, title_size).getbbox("BEVERLY")
    gap = max(1, inner_h // 16)
    total_h = (sub_box[3] - sub_box[1]) + gap + (title_box[3] - title_box[1])

    center_x = (left + right) // 2
    start_y = (top + bottom - total_h) // 2
    sub_pos = (
        center_x - (sub_box[2] - sub_box[0]) // 2 - sub_box[0],
        start_y - sub_box[1],
    )
    title_pos = (
        center_x - (title_box[2] - title_box[0]) // 2 - title_box[0],
        start_y + (sub_box[3] - sub_box[1]) + gap - title_box[1],
    )
    return (sub_pos, sub_size), (title_pos, title_size)


def run(matrix, config):
    """Broadway Lights"""
    max_y = config["pixel_height"]
    max_x = config["pixel_width"]

    rainbow = [
        matrix.color("red"),
        matrix.color("green"),
        matrix.color("purple"),
        matrix.color("yellow"),
        matrix.color("white"),
    ]

    border_coords, bounds = build_border(max_x, max_y)
    (sub_pos, sub_size), (title_pos, title_size) = layout_text(bounds, max_x, max_y)

    color_offset = 0
    background_color = matrix.color("black")
    white = matrix.color("white")

    while matrix.ready():
        matrix.reset(background_color)

        for idx, coord in enumerate(border_coords):
            matrix.pixel(coord, rainbow[(idx + color_offset) % len(rainbow)])
        color_offset = (color_offset + 1) % len(rainbow)

        matrix.text("The", sub_pos, sub_size, white, FONT_FILE)
        matrix.text("BEVERLY", title_pos, title_size, white, FONT_FILE)
        matrix.show()
