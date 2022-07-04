import sys

# marquee
delay = 1 # in ms
font_thickness = 1
font_scaling = 1
top_padding = 9
font_color= (255,0,0)

usage = 'Usage: ./run.sh marquee "my message"'

def run(matrix, config):
    sys.argv.pop(0) # remove loader arg
    if len(sys.argv) != 2:
        print(usage)
        sys.exit()

    message = sys.argv[1]
    message_length = len(message);
    marquee_size = message_length * font_scaling * 10;

    def display_text(x, y):
        y = (10 * font_scaling) + top_padding
        matrix.fill(0,0,0)
        matrix.text(message, (x, y), font_scaling, font_color, font_thickness)
        matrix.show()

    while True:
        for x in range(marquee_size, -marquee_size, -1):
            display_text(x, top_padding)
            matrix.delay(delay)
