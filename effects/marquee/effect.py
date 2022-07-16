import sys
import numpy as np

# marquee
delay = 1 # in ms
font_scaling = 1
top_padding = 5
font_color= (255,0,0)

usage = 'Usage: ./run.sh marquee "my message"'

def run(matrix, config):
    """scroll large marquee text"""# remove loader arg
    if len(config['argv']) != 1:
        print(usage)
        sys.exit()

    message = config['argv'][0]
    message_length = len(message)
    marquee_size = message_length * font_scaling * 10

    def display_text(x, y):
        y = top_padding
        matrix.reset()
        matrix.text(message, (x, y), 16, font_color)

    while True:
        for x in range(marquee_size, -marquee_size, -1):
            display_text(x, top_padding)
            # skip frames that have no pixels lit up
            if not np.all(matrix.frame == 0):
                matrix.show()
                matrix.delay(delay)

