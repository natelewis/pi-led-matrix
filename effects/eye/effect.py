#
# eye looking at you
# 22 July 2022 - Simple eyes with random movement
#
# Brown Eyes: 45 percent
# Blue Eyes: 28 percent
# Hazel Eyes: 18 percent (Note: Hazel eyes consist of shades of brown and green.)
# Green Eyes: 9 percent
#

import random

color_black = (0, 0, 0)
color_blue = (0, 0, 255)
color_white = (255, 255, 255)
color_brown = (165, 42, 42)
color_green = (0, 128, 0)
color_hazel = (34, 139, 34)

    
def run(matrix, config):
    """ eyes looking at you """
    eye_color = random.choices([color_brown, color_blue, color_hazel, color_green], weights=[45, 28, 18, 9])[0]

    while True:
        x_dir, y_dir = random.choices([(0,0), (5, 0), (-5, 0), (0, 5), (0, -5), (5, -5), (5, 5), (-5, 5), (-5, -5)], weights=[60, 5, 5, 5, 5, 5, 5, 5, 5])[0]
        matrix.reset()
        for eye in [15, 45]:
            matrix.circle((eye, 15), 12, color_white,  -1)
            matrix.circle((eye + x_dir, 15 + y_dir), 5, eye_color, -1)
            matrix.circle((eye + x_dir, 15 + y_dir), 2, color_black, -1)
        matrix.show()
        matrix.delay(3000)
