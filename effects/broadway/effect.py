#
# Broadway Lights
# 3 January 2023
#


def run(matrix, config):
	""" Broadway Lights """
	min_y = 0
	min_x = 0
	max_y = config['pixel_height']
	max_x = config['pixel_width']

	rainbow = [ matrix.color('red'), matrix.color('green'), matrix.color('purple'), matrix.color('yellow'), matrix.color('white') ]

	# Return the next color in the string
	def get_color(num):
		num = color
		num += 1
		if num >= len(rainbow):
			num = 0
		return num

	dots = {}
	color = 0
	# Generate the top row of lights
	for i in range(4, max_x - 4, 2):
		dots[(i, 4)] = color
		color = get_color(color)
	# Generate the left column of lights
	for i in range(max_y - 6, 4, -2):
		dots[(4, i)] = color
		color = get_color(color)
	# Generate the bottow row of lights
	for i in range(max_x - 6, 4, -2):
		dots[(i, max_y - 6)] = color
		color = get_color(color)
	# Generate the right colum of lights
	for i in range(6, max_y - 6, 2):
		dots[(max_x - 6, i)] = color
		color = get_color(color)

	background_color = matrix.color('black')

	while True:    
		matrix.reset(background_color)
		
		new_dots = {}
		for coord, color in dots.items():
			matrix.pixel(coord, rainbow[color])
			new_dots[coord] = get_color(color)
		dots = new_dots

		matrix.text("The", (9, 4), 6, matrix.color('white'), 'dosis.ttf')
		matrix.text("BEVERLY", (9, 8), 12, matrix.color('white'), 'dosis.ttf')
		matrix.show()
