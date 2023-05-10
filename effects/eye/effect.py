#
# eye looking at you
# 22 July 2022 - Simple eyes with random movement
#
# Brown Eyes: 45 percent
# Blue Eyes: 28 percent
# Hazel Eyes: 18 percent (Note: Hazel eyes consist of shades of brown and green.  Sometimes called forestgreen)
# Green Eyes: 9 percent
#

import random

    
def run(matrix, config):
    """ eyes looking at you """
    eye_color = random.choices([matrix.color('brown'), matrix.color('blue'), matrix.color('forestgreen'), matrix.color('green')], weights=[45, 28, 18, 9])[0]

    while matrix.ready():
        x_dir, y_dir = random.choices([(0,0), (5, 0), (-5, 0), (0, 5), (0, -5), (5, -5), (5, 5), (-5, 5), (-5, -5)], weights=[60, 5, 5, 5, 5, 5, 5, 5, 5])[0]
        matrix.reset()
        for eye in [15, 45]:
            matrix.circle((eye, 15), 12, matrix.color('white'),  -1)
            matrix.circle((eye + x_dir, 15 + y_dir), 5, eye_color, -1)
            matrix.circle((eye + x_dir, 15 + y_dir), 2, matrix.color('black'), -1)
        matrix.show()
        matrix.delay(3000)
