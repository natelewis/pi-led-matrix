#
# pacman
# 18 July 2022
#

color_yellow = (255, 255, 0)
color_black = (0, 0, 0)

# Use the same sprite for pacman but change the color coding to animate frame by frame
color_key = [
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

# Reuse the right facing pacman, reverse the image to create left facing pacman
pacman_left = [line[::-1] for line in pacman_right]

def run(matrix, config):
    """ pacman """

    animate_frame = 0
    x = -len(pacman_right)
    y = 8
    pacman_face = pacman_right
    pacman_direction = 1

    while True:
        matrix.reset()
        matrix.sprite(pacman_face, (x, y), color_key[animate_frame % len(color_key)])
        matrix.show()
        animate_frame += 1
        x += pacman_direction
        
        if pacman_face == pacman_right and x >= config['pixel_width'] - len(pacman_face):
            pacman_direction = -1
            pacman_face = pacman_left
        if pacman_face == pacman_left and x <= 0:
            pacman_direction = 1
            pacman_face = pacman_right

