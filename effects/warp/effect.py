#
# Warp speed
# 21 July 2022
#

from operator import itemgetter
import random
import math


def new_star(mid_x, mid_y, dist):
	""" Create a new star """
	color_r = random.randrange(256)
	color_g = random.randrange(256)
	color_b = random.randrange(256)
	x = mid_x
	y = mid_y
	angle = 60 + random.randrange(720)

	return {"color_r": color_r, "color_g": color_g, "color_b": color_b, "x": mid_x, "y": mid_y, "angle": angle, "dist": dist}


def run(matrix, config):
	""" Warp speed effect """
	mid_y = int(config['pixel_height'] / 2)
	mid_x = int(config['pixel_width'] / 2)
	num_of_stars = 12

	galaxy = []
	# Create initial field of stars
	for star in range(num_of_stars):
		galaxy.append(new_star(mid_x, mid_y, 8 % (star + 1)))

	while True:
		matrix.reset()
		for star in range(len(galaxy)):
			x, y, angle, color_r, color_g, color_b, dist = itemgetter('x', 'y', 'angle', 'color_r', 'color_g', 'color_b', 'dist')(galaxy[star])

			x_old = x
			y_old = y
			dist += 1
			x = mid_x + int(dist *(math.cos(angle) * 360) / (2 * 3.14)/10)
			y = mid_y - int(dist *(math.sin(angle) * 360) / (2 * 3.14)/10)

			matrix.line((x_old, y_old), (x,y), (color_r, color_g, color_b), 1)

			if dist >= 6:
				galaxy[star] = new_star(mid_x, mid_y, 0)
			else:
				galaxy[star] = {"color_r": color_r, "color_g": color_g, "color_b": color_b, "x": x, "y": y, "angle": angle, "dist": dist}

		matrix.show()
