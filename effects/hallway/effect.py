ceiling_height = 10

def tunnel_rectangle(config, matrix, offset):
    """create individual rectangle"""
    center_width = config['pixel_width'] / 2
    height = config['pixel_height']
    matrix.rectangle(
		(int(center_width - offset), int(height - offset - ceiling_height)),
		(int(center_width + offset), int(height + offset)),
		(90, 0, 0),
		1,
	)

def run(matrix, config):
	"""hallway coming towards you"""
	wall_offsets = [0, 10, 20, 30]
	while True:
			matrix.reset((0,0,0))
			for idx, offset in enumerate(wall_offsets):
				offset = offset + 1
				if offset > config['pixel_height']:
					offset = 0
				wall_offsets[idx] = offset
				tunnel_rectangle(config, matrix, offset)

			matrix.show()
