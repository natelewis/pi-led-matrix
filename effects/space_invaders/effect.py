#
# space invaders
# 30 August 2022
#

squid = [
    [' ', ' ', ' ', ' ', ' ', ' ', 'a', 'a', 'a', 'a', ' ', ' ', ' ', ' ', ' ', ' '],
    [' ', ' ', ' ', ' ', ' ', ' ', 'a', 'a', 'a', 'a', ' ', ' ', ' ', ' ', ' ', ' '],
    [' ', ' ', ' ', ' ', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', ' ', ' ', ' ', ' '],
    [' ', ' ', ' ', ' ', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', ' ', ' ', ' ', ' '],
    [' ', ' ', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', ' ', ' '],
    [' ', ' ', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', ' ', ' '],
    ['a', 'a', 'a', 'a', ' ', ' ', 'a', 'a', 'a', 'a', ' ', ' ', 'a', 'a', 'a', 'a'],
    ['a', 'a', 'a', 'a', ' ', ' ', 'a', 'a', 'a', 'a', ' ', ' ', 'a', 'a', 'a', 'a'],
    ['a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a'],
    ['a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a'],
    [' ', ' ', 'b', 'b', 'c', 'c', 'b', 'b', 'b', 'b', 'c', 'c', 'b', 'b', ' ', ' '],
    [' ', ' ', 'b', 'b', 'c', 'c', 'b', 'b', 'b', 'b', 'c', 'c', 'b', 'b', ' ', ' '],
    ['b', 'b', 'c', 'c', ' ', ' ', 'c', 'c', 'c', 'c', ' ', ' ', 'c', 'c', 'b', 'b'],
    ['b', 'b', 'c', 'c', ' ', ' ', 'c', 'c', 'c', 'c', ' ', ' ', 'c', 'c', 'b', 'b'],
    ['c', 'c', 'b', 'b', 'c', 'c', ' ', ' ', ' ', ' ', 'c', 'c', 'b', 'b', 'c', 'c'],
    ['c', 'c', 'b', 'b', 'c', 'c', ' ', ' ', ' ', ' ', 'c', 'c', 'b', 'b', 'c', 'c']
]

crab = [
    [' ', ' ', ' ', ' ', 'a', 'a', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', 'a', 'a', ' ', ' ', ' ', ' '],
    [' ', ' ', ' ', ' ', 'a', 'a', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', 'a', 'a', ' ', ' ', ' ', ' '],
    [' ', ' ', ' ', ' ', ' ', ' ', 'a', 'a', ' ', ' ', ' ', ' ', 'a', 'a', ' ', ' ', ' ', ' ', ' ', ' '],
    [' ', ' ', ' ', ' ', ' ', ' ', 'a', 'a', ' ', ' ', ' ', ' ', 'a', 'a', ' ', ' ', ' ', ' ', ' ', ' '],
    ['c', 'c', ' ', ' ', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', ' ', ' ', 'c', 'c'],
    ['c', 'c', ' ', ' ', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', ' ', ' ', 'c', 'c'],
    ['c', 'c', 'a', 'a', 'a', ' ', ' ', 'a', 'a', 'a', 'a', 'a', 'a', ' ', ' ', 'a', 'a', 'a', 'c', 'c'],
    ['c', 'c', 'a', 'a', 'a', ' ', ' ', 'a', 'a', 'a', 'a', 'a', 'a', ' ', ' ', 'a', 'a', 'a', 'c', 'c'],
    ['a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a'],
    ['a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a'],
    ['b', 'b', ' ', ' ', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', ' ', ' ', 'b', 'b'],
    ['b', 'b', ' ', ' ', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', ' ', ' ', 'b', 'b'],
    ['b', 'b', ' ', ' ', 'a', 'a', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', 'a', 'a', ' ', ' ', 'b', 'b'],
    ['b', 'b', ' ', ' ', 'a', 'a', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', 'a', 'a', ' ', ' ', 'b', 'b'],
    [' ', ' ', 'c', 'c', ' ', ' ', 'b', 'b', 'b', ' ', ' ', 'b', 'b', 'b', ' ', ' ', 'c', 'c', ' ', ' '],
    [' ', ' ', 'c', 'c', ' ', ' ', 'b', 'b', 'b', ' ', ' ', 'b', 'b', 'b', ' ', ' ', 'c', 'c', ' ', ' ']
]

octopus = [
    [' ', ' ', ' ', ' ', ' ', ' ', ' ', 'a', 'a', 'a', 'a', 'a', 'a', ' ', ' ', ' ', ' ', ' ', ' ', ' '],
    [' ', ' ', ' ', ' ', ' ', ' ', ' ', 'a', 'a', 'a', 'a', 'a', 'a', ' ', ' ', ' ', ' ', ' ', ' ', ' '],
    [' ', ' ', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', ' ', ' '],
    [' ', ' ', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', ' ', ' '],
    ['a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a'],
    ['a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a'],
    ['a', 'a', 'a', 'a', 'a', ' ', ' ', ' ', 'a', 'a', 'a', 'a', ' ', ' ', ' ', 'a', 'a', 'a', 'a', 'a'],
    ['a', 'a', 'a', 'a', 'a', ' ', ' ', ' ', 'a', 'a', 'a', 'a', ' ', ' ', ' ', 'a', 'a', 'a', 'a', 'a'],
    ['a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a'],
    ['a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a'],
    [' ', ' ', ' ', ' ', ' ', 'a', 'a', 'a', ' ', ' ', ' ', ' ', 'a', 'a', 'a', ' ', ' ', ' ', ' ', ' '],
    [' ', ' ', ' ', ' ', ' ', 'a', 'a', 'a', ' ', ' ', ' ', ' ', 'a', 'a', 'a', ' ', ' ', ' ', ' ', ' '],
    [' ', ' ', ' ', 'a', 'a', 'a', ' ', ' ', 'a', 'a', 'a', 'a', ' ', ' ', 'a', 'a', 'a', ' ', ' ', ' '],
    [' ', ' ', ' ', 'a', 'a', 'a', ' ', ' ', 'a', 'a', 'a', 'a', ' ', ' ', 'a', 'a', 'a', ' ', ' ', ' '],
    ['b', 'b', 'b', ' ', 'c', 'c', 'c', ' ', ' ', ' ', ' ', ' ', ' ', 'c', 'c', 'c', ' ', 'b', 'b', 'b'],
    ['b', 'b', 'b', ' ', 'c', 'c', 'c', ' ', ' ', ' ', ' ', ' ', ' ', 'c', 'c', 'c', ' ', 'b', 'b', 'b']
]

def run(matrix, config):
    """ space invaders """

    # Change the color of the aliens and/or background if too intense on LED screen
    alien_color = matrix.color('white')
    background_color = matrix.color('black')

    # This color key applies to all aliens.  Switch colors to animate sprite.
    squid_color_key = [
        {'a': alien_color, 'b': alien_color, 'c': background_color},
        {'a': alien_color, 'b': background_color, 'c': alien_color},
    ]

    animate_frame = 0
    x = 0
    init_y = -50
    max_y = config['pixel_height']
    y = init_y
    direction = 1

    while True:
        matrix.reset(background_color)

        # draw squids
        matrix.sprite(squid, (x + 2 - 24, y), squid_color_key[animate_frame])
        matrix.sprite(squid, (x + 2, y), squid_color_key[animate_frame])
        matrix.sprite(squid, (x + 2 + 24, y), squid_color_key[animate_frame])

        # Draw crabs
        matrix.sprite(crab, (x - 24, y + 20), squid_color_key[animate_frame])
        matrix.sprite(crab, (x, y + 20), squid_color_key[animate_frame])
        matrix.sprite(crab, (x + 24, y + 20), squid_color_key[animate_frame])

        # Draw octopuses
        matrix.sprite(octopus, (x - 24, y + 40), squid_color_key[animate_frame])
        matrix.sprite(octopus, (x, y + 40), squid_color_key[animate_frame])
        matrix.sprite(octopus, (x + 24, y + 40), squid_color_key[animate_frame])

        matrix.show()

        matrix.delay(10)

        # change color of legs, alternating between black and white gives illusion of animation
        if animate_frame == 0:
            animate_frame = 1
        else:
            animate_frame = 0

        # When middle aliens reach end of screen, drop and change direction
        x += direction
        if x >= 40 or x <= 0:
            y += 5
            direction *= -1

        # Start all over again from the virtual top when top alient reaches the bottom
        if y >= max_y:
            y = init_y
