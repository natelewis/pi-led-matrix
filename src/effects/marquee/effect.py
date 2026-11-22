import sys
import numpy as np

# marquee
DELAY = 1  # in ms
USAGE = (
    'Usage: make run effect=marquee config=\'{ "messages": '
    '[{ "left": 0, "right": 5, "r": 255, "g": 255, "b": 255, '
    '"message": "my message", "font": "optional_font.ttf"}]}\''
)


def run(matrix, config):
    """scroll large marquee text"""
    if not config["effect"]["messages"]:
        print(USAGE)
        sys.exit()

    default_font_size = max(8, round(config["pixel_height"] * 0.55))
    step = max(1, config["pixel_width"] // 60)

    messages = [
        [
            int(item["left"]) + config["pixel_width"],
            int(item["right"]),
            (int(item["r"]), int(item["g"]), int(item["b"])),
            item["message"],
            item["font"],
            int(item.get("font_size", default_font_size)),
        ]
        for item in config["effect"]["messages"]
    ]

    original_messages = [msg.copy() for msg in messages]
    reset_in_progress = False

    while matrix.ready():
        matrix.reset()
        for message in messages:
            message[0] -= step
            matrix.text(
                message[3],
                (message[0], message[1]),
                message[5],
                message[2],
                message[4],
            )

        # skip frames that have no pixels lit up
        if not np.all(matrix.frame == 0):
            matrix.show()
            matrix.delay(DELAY)
            reset_in_progress = False
        elif not reset_in_progress:
            # prevent an endless loop -- wait till we see things again before resetting again
            reset_in_progress = True
            messages = [msg.copy() for msg in original_messages]
