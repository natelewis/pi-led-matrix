import sys
import json
import numpy as np

# marquee
DELAY = 1 # in ms
USAGE = 'Usage: ./run.sh marquee \'{ "messages": [{ "left": 0, "right": 5, "r": 255, "g": 255, "b": 255, "message": "my message", "font": "optional_font.ttf"}]}\''

def run(matrix, config):
    """scroll large marquee text"""# remove loader arg
    if len(config['argv']) != 1:
        print(USAGE)
        sys.exit()

    data = json.loads(config['argv'][0])

    messages = []
    for m in data['messages']:
        messages.append([
            m['left'] + config['pixel_width'],
            m['right'],
            m['r'],
            m['g'],
            m['b'],
            m['message'],
            m['font']
        ])

    original_messages = messages.copy()
    reset_in_progress = False

    def display_text(x, y, text, font_color, font):
        matrix.text(text, (x, y), 16, font_color, font)

    while matrix.good_to_go():
        matrix.reset()
        for idx, message in enumerate(messages):
            x, y, r, g, b, text, font = message
            x = int(x)
            y = int(y)
            r = int(r)
            g = int(g)
            b = int(b)
            x = x - 1
            display_text(x, y, text, (r, g, b), font)
            messages[idx] = [x, y, r, g, b, text, font]

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
