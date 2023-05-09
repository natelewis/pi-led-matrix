#
# Warp speed
#
# 25 July 2022 = Added black hole in center
# 21 July 2022 - Simple lines moving away from center using trig
#

from operator import itemgetter
import random
import math

def run(matrix, config):
	""" Warp speed effect """

	def new_star(mid_x, mid_y, dist):
		""" Create a new star """
		color = matrix.random_color()
		angle = 60 + random.randrange(720)

		return {"color": color, "x": mid_x, "y": mid_y, "angle": angle, "dist": dist}

	mid_y = int(config['pixel_height'] / 2)
	mid_x = int(config['pixel_width'] / 2)
	num_of_stars = 12

	galaxy = []
	# Create initial field of stars
	for star in range(num_of_stars):
		galaxy.append(new_star(mid_x, mid_y, 8 % (star + 1)))

	while matrix.good_to_go():
		matrix.reset()
		for star in range(len(galaxy)):
			x, y, angle, color, dist = itemgetter('x', 'y', 'angle', 'color', 'dist')(galaxy[star])

			x_old = x
			y_old = y
			dist += 1
			x = mid_x + int(dist *(math.cos(angle) * 360) / (2 * 3.14)/10)
			y = mid_y - int(dist *(math.sin(angle) * 360) / (2 * 3.14)/10)

			matrix.line((x_old, y_old), (x,y), color, 1)

			if dist >= 6:
				galaxy[star] = new_star(mid_x, mid_y, 0)
			else:
				galaxy[star] = {"color": color, "x": x, "y": y, "angle": angle, "dist": dist}

		matrix.circle((mid_x, mid_y), 2, (0,0,0), -1)
		matrix.show()
