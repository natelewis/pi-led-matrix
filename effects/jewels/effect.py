#
# Jewels
# 6 January 2023
#

import random

# Number of seconds between screen updates
# set PAUSE to 0 for an old timey static effect.
PAUSE = 5

def run(matrix, config):
	""" Jewels """
	min_y = 2
	min_x = 2
	max_y = config['pixel_height'] - 2
	max_x = config['pixel_width'] - 2

	rainbow = [ matrix.color('red'), matrix.color('green'), matrix.color('blue'), matrix.color('purple'), matrix.color('yellow'), matrix.color('cyan') ]

	background_color = matrix.color('black')
	match_colot = matrix.color('white')

	jewels = {}

	for x in range(min_x, max_x, 2):
		for y in range(min_y, max_y, 2):
			jewels[(x, y - max_y)] = random.choice(rainbow)

	while True:    
		matrix.reset(background_color)

		new_jewels = {}

		for coord, color in jewels.items():
			x, y = coord
			if y < (max_y - 2) and (x, y + 2) not in jewels:
				coord = (x, y + 2)
			matrix.pixel(coord, color)
			new_jewels[coord] = color

		jewels = new_jewels.copy()

		matrix.show()
