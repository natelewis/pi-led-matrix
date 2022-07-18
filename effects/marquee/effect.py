import sys
import numpy as np

# marquee
DELAY = 1 # in ms
USAGE = 'Usage: ./run.sh marquee left_padding right_padding r g b "my message" ..repeat'

def run(matrix, config):
    """scroll large marquee text"""# remove loader arg
    if len(config['argv']) % 6:
        print(USAGE)
        sys.exit()

    line_count = len(config['argv']) / 6

    # reshape and clean up data
    mmm = np.reshape(config['argv'], ( int(line_count), 6))
    messages = []
    for idx, m in enumerate(mmm):
        messages.append([
            int(m[0]) + config['pixel_width'],
            int(m[1]),
            int(m[2]),
            int(m[3]),
            int(m[4]),
            m[5]
        ])

    original_messages = messages.copy()
    reset_in_progress = False

    def display_text(x, y, text, font_color):
        matrix.text(text, (x, y), 16, font_color)

    while True:
        matrix.reset()
        for idx, message in enumerate(messages):
            x, y, r, g, b, text = message
            x = int(x)
            y = int(y)
            r = int(r)
            g = int(g)
            b = int(b)
            x = x - 1
            display_text(x, y, text, (r, g, b))
            messages[idx] = [x, y, r, g, b, text]

        # skip frames that have no pixels lit up
        if not np.all(matrix.frame == 0):

            matrix.show()
            matrix.delay(DELAY)
            reset_in_progress = False
        else:
            if not reset_in_progress:
                # prevent an endless loop -- wait till we see things again before resetting again
                reset_in_progress = True
                messages = original_messages.copy()
