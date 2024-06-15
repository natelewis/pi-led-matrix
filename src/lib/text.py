from PIL import Image, ImageDraw, ImageFont


def text(self, message, start, font_size, rgb_color, ttf_file):
    image = Image.fromarray(self.frame)
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("./fonts/" + ttf_file, font_size)
    draw.text(start, message, font=font, fill=rgb_color)
    self.image(image)
