#
# Jewels
# 3 January 2023
#


def run(matrix, config):
	""" Jewels """
	min_y = 0
	min_x = 0
	max_y = config['pixel_height']
	max_x = config['pixel_width']

	rainbow = [ matrix.color('red'), matrix.color('green'), matrix.color('purple'), matrix.color('yellow'), matrix.color('white') ]
	# dots = { (4, 4): 0, (6, 4): 1, (8, 4): 2, (10, 4): 3, (12, 4): 4, (14, 4): 0, (16, 4): 1}

	def get_color(num):
		num = color
		num += 1
		if num >= len(rainbow):
			num = 0
		return num

	dots = {}
	color = 0
	for i in range(4, max_x - 4, 2):
		dots[(i, 4)] = color
		color = get_color(color)
	for i in range(max_y - 6, 4, -2):
		dots[(4, i)] = color
		color = get_color(color)
	for i in range(max_x - 6, 4, -2):
		dots[(i, max_y - 6)] = color
		color = get_color(color)
	for i in range(6, max_y - 6, 2):
		dots[(max_x - 6, i)] = color
		color = get_color(color)

	background_color = matrix.color('black')

	while True:    
		matrix.reset(background_color)
		
		new_dots = {}
		for coord, color in dots.items():
			matrix.pixel(coord, rainbow[color])
			new_color = color + 1
			if new_color >= len(rainbow):
				new_color = 0
			new_dots[coord] = new_color
		dots = new_dots

		matrix.show()
