#
# pacman
# 19 July 2022 add ghost with movement
# 18 July 2022 start with pacman movement
#

color_yellow = (255, 255, 0)
color_black = (0, 0, 0)
color_red = (255, 0, 0)
color_blue = (0, 0, 255)
color_white = (255, 255, 255)

# Use the same sprite for pacman but change the color coding to animate frame by frame
pacman_color_key = [
    {'a': color_yellow, 'b': color_yellow, 'c': color_yellow},
    {'a': color_yellow, 'b': color_yellow, 'c': color_black},
    {'a': color_yellow, 'b': color_black, 'c': color_black},
    {'a': color_yellow, 'b': color_yellow, 'c': color_black},
]

# Draw a pacman facing right
pacman_right = [
    [' ', ' ', ' ', ' ', 'a', 'a', 'a', 'a', 'a', ' ', ' ', ' ', ' '],
    [' ', ' ', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'b', 'b', ' ', ' '],
    [' ', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'b', 'b', 'b', 'b', ' '],
    [' ', 'a', 'a', 'a', 'a', 'a', 'a', 'b', 'b', 'b', 'b', 'b', ' '],
    ['a', 'a', 'a', 'a', 'a', 'a', 'b', 'b', 'b', 'b', 'c', 'c', 'c'],
    ['a', 'a', 'a', 'a', 'a', 'b', 'b', 'c', 'c', 'c', 'c', 'c', 'c'],
    ['a', 'a', 'a', 'a', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c'],
    ['a', 'a', 'a', 'a', 'a', 'b', 'b', 'c', 'c', 'c', 'c', 'c', 'c'],
    ['a', 'a', 'a', 'a', 'a', 'a', 'b', 'b', 'b', 'b', 'c', 'c', 'c'],
    [' ', 'a', 'a', 'a', 'a', 'a', 'a', 'b', 'b', 'b', 'b', 'b', ' '],
    [' ', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'b', 'b', 'b', 'b', ' '],
    [' ', ' ', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'b', 'b', ' ', ' '],
    [' ', ' ', ' ', ' ', 'a', 'a', 'a', 'a', 'a', ' ', ' ', ' ', ' ']
]

# Use the same sprite for the ghost but change the colors to animate movement
ghost_color_key = [
    {'a': color_red, 'b': color_white, 'c': color_blue, 'd': color_black, 'e': color_black, 'f': color_red, 'g': color_black, 'h':color_blue},
    {'a': color_red, 'b': color_white, 'c': color_blue, 'd': color_black, 'e': color_red, 'f': color_black, 'g':color_blue, 'h': color_black},
]

# Draw an agressive ghost chasing pacman
ghost_agro = [
    [' ', ' ', ' ', ' ', ' ', 'a', 'a', 'a', 'a', ' ', ' ', ' ', ' ', ' '],
    [' ', ' ', ' ', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', ' ', ' ', ' '],
    [' ', ' ', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', ' ', ' '],
    [' ', 'a', 'a', 'a', 'b', 'b', 'a', 'a', 'a', 'a', 'b', 'b', 'a', ' '],
    [' ', 'a', 'a', 'b', 'b', 'b', 'b', 'a', 'a', 'b', 'b', 'b', 'b', ' '],
    [' ', 'a', 'a', 'b', 'b', 'c', 'c', 'a', 'a', 'b', 'b', 'c', 'c', ' '],
    ['a', 'a', 'a', 'b', 'b', 'c', 'c', 'a', 'a', 'b', 'b', 'c', 'c', 'a'],
    ['a', 'a', 'a', 'a', 'b', 'b', 'a', 'a', 'a', 'a', 'b', 'b', 'a', 'a'],
    ['a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a'],
    ['a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a'],
    ['a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a'],
    ['a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a'],
    ['a', 'a', 'e', 'a', 'f', 'a', 'e', 'e', 'a', 'f', 'a', 'e', 'a', 'a'],
    ['f', 'e', 'e', 'd', 'f', 'f', 'e', 'e', 'f', 'f', 'd', 'e', 'e', 'f']
]

# Draw a scared ghost running away from pacman
ghost_scared = [
    [' ', ' ', ' ', ' ', ' ', 'c', 'c', 'c', 'c', ' ', ' ', ' ', ' ', ' '],
    [' ', ' ', ' ', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', ' ', ' ', ' '],
    [' ', ' ', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', ' ', ' '],
    [' ', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', ' '],
    [' ', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', ' '],
    [' ', 'c', 'c', 'b', 'b', 'c', 'c', 'c', 'c', 'b', 'b', 'c', 'c', ' '],
    ['c', 'c', 'c', 'b', 'b', 'c', 'c', 'c', 'c', 'b', 'b', 'c', 'c', 'c'],
    ['c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c'],
    ['c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c'],
    ['c', 'c', 'b', 'b', 'c', 'c', 'b', 'b', 'c', 'c', 'b', 'b', 'c', 'c'],
    ['c', 'b', 'c', 'c', 'b', 'b', 'c', 'c', 'b', 'b', 'c', 'c', 'b', 'c'],
    ['c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c'],
    ['c', 'c', 'g', 'c', 'h', 'c', 'g', 'g', 'c', 'h', 'c', 'g', 'c', 'c'],
    ['h', 'g', 'g', 'd', 'h', 'h', 'g', 'g', 'h', 'h', 'd', 'g', 'g', 'h']
]

# Reuse the right facing pacman, reverse the image to create left facing pacman
pacman_left = [line[::-1] for line in pacman_right]

def run(matrix, config):
    """ pacman """

    animate_frame = 0
    x = -len(pacman_right)
    y = 8
    pacman_face = pacman_right
    pacman_direction = 1
    ghost_body = ghost_agro

    while matrix.good_to_go():
        matrix.reset()
        matrix.sprite(pacman_face, (x, y), pacman_color_key[animate_frame % len(pacman_color_key)])
        matrix.sprite(ghost_body, (x - 2 - len(ghost_agro), y), ghost_color_key[animate_frame % len(ghost_color_key)])
        matrix.show()
        animate_frame += 1
        x += pacman_direction

        if pacman_face == pacman_right and x >= config['pixel_width']:
            pacman_direction = -1
            pacman_face = pacman_left
            ghost_body = ghost_scared
        if pacman_face == pacman_left and x <= 0:
            pacman_direction = 1
            pacman_face = pacman_right
            ghost_body = ghost_agro
