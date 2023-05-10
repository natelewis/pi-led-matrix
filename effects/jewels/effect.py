#
# Jewels
# 9 January 2023
#

import random


def run(matrix, config):
	""" Jewels """
	min_y = 2
	min_x = 2
	max_y = config['pixel_height'] - 2
	max_x = config['pixel_width'] - 2

	rainbow = [ matrix.color('red'), matrix.color('green'), matrix.color('blue'), matrix.color('yellow') ]

	background_color = matrix.color('black')
	match_color = matrix.color('white')

	jewels = {}

	# Check the adjacent jewels for matches, needs to be at least 3 jewels of the same color
	def find_matches(jewels, coord):
		matches = [coord, ]
		target = jewels[coord]
		x, y = coord
		direction = [(0, -2), (0, 2), (-2, 0), (2, 0)]
		
		for delta_x, delta_y in direction:
			current_color = target
			while (current_color == target):
				current_coord = (x + delta_x, y + delta_y)
				if current_coord in jewels and jewels[current_coord] == target:
					matches.append(current_coord)
					delta_x += delta_x
					delta_y += delta_y
				else:
					current_color = None
			if len(matches) > 2:
				return matches
			else:
				matches = [coord, ]

		return matches.copy()

	stable_jewels = 0

	while matrix.ready():    
		matrix.reset(background_color)

		new_jewels = {}

		# Add new jewels if there are any missing in the top row
		added_jewels = 0
		for x in range(min_x, max_x, 2):
			if (x, min_y) not in jewels:
				jewels[(x, min_y)] = random.choice(rainbow)
				added_jewels += 1

		# If the jewel field is stable (no new jewels added), do a short wait and then clear the field
		if added_jewels == 0:
			stable_jewels += 1
		else:
			stable_jewels = 0
		if stable_jewels > 10:
			jewels = {}

		# Check for jewels that need to fall
		for coord, color in jewels.items():
			x, y = coord
			if y < (max_y - 2) and (x, y + 2) not in jewels:
				coord = (x, y + 2)
			matrix.pixel(coord, color)

			# Remove jewels that match at least 3 in a row
			if color != match_color:
				new_jewels[coord] = color

		jewels = new_jewels.copy()

		# Change the color of jewels to white when 3 or more of the same color are in a row
		for coord, color in jewels.items():
			matches = find_matches(jewels, coord)
			if len(matches) > 1:
				for j in matches:
					new_jewels[j] = match_color

		jewels = new_jewels.copy()

		matrix.show()
