#
# futbol
# 28 August 2022
#

import random

def run(matrix, config):
    """ futbol """

    x_max = config['pixel_width']
    y_max = config['pixel_height']
    play_start = True

    red_pos = [(24, 12), (28, 12), (32, 12), (36, 12), (4, 12), (8, 8), (13, 6), (54, 12), (48, 10), (30, 8), (40, 9)]

    blue_pos = [(24, 18), (28, 18), (32, 18), (36, 18), (30, 23), (26, 23), (55, 23), (44, 20), (32, 26), (8, 22), (12, 24)]

    while matrix.ready():
        # Draw a green football field
        matrix.reset((0,20,0))

        # Draw yard line
        matrix.line((0, int(y_max/2)), (x_max, int(y_max/2)), matrix.color('white'), 1) 

        # Draw tick marks (sorry the math is a little messy)
        for tick in range(1, 8):
            matrix.line((int(x_max/3)-3, int(y_max/8 * tick)), (int(x_max/3), int(y_max/8 * tick)), matrix.color('white'), 1)
            matrix.line((int(x_max - (x_max/3)), int(y_max/8 * tick)), (int(x_max - (x_max/3) + 3), int(y_max/8 * tick)), matrix.color('white'), 1)
        
        # Draw Team Red
        for x, y in red_pos:
            matrix.pixel((x, y), matrix.color('red'))

        # Draw Team Blue
        for x, y in blue_pos:
            matrix.pixel((x, y), matrix.color('blue'))

        matrix.show()

        # Hut hut hut!
        if play_start is True:
            play_start = False
            matrix.delay(3000)

        # Move red player but do not collide with other players
        for player in range(len(red_pos)):
            x, y = red_pos[player]
            x += random.randint(-1, 1)
            y += random.randint(-1, 1)
            if (x, y) not in blue_pos and (x, y) not in red_pos:
                red_pos[player] = (x, y)

        # Move blue player but do not collide with other players
        for player in range(len(blue_pos)):
            x, y = blue_pos[player]
            x += random.randint(-1, 1)
            y += random.randint(-1, 1)
            if (x, y) not in blue_pos and (x, y) not in red_pos:
                blue_pos[player] = (x, y)
