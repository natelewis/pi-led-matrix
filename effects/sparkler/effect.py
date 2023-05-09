#
# Sparkler
# 25 July 2022
#

import random


# Accelerate the downward movement due to gravity
GRAVITY_PULL = 0.35

# Reduce the size of the particle as it moves
FIZZLE_OUT = 0.25

# Add more particles with each animation frame
ADD_PARTICLES = 3


def run(matrix, config):
	""" Sparkler """
	particles = []
	my = int(config['pixel_height'] / 2)
	mx = int(config['pixel_width'] / 2)
 
	while matrix.good_to_go():    
		matrix.reset()
		
		for i in range(ADD_PARTICLES):
			# Size of particle starts in the range of 2-4 pixels
			psize = random.randint(2, 4)

			# Initial velocity of pixel is in range of -3.5 to 3.5
			dx = random.randrange(-35, 35) / 10
			dy = random.randrange(-35, 35) / 10

			particles.append({'x': mx, 'y': my, 'dx': dx, 'dy': dy, 'psize': psize})

		for particle in particles:
			particle['x'] += particle['dx']
			particle['y'] += particle['dy']
			particle['psize'] -= FIZZLE_OUT
			particle['dy'] += GRAVITY_PULL
			pcolor = matrix.random_color()

			if particle['psize'] <= 0:
				# Particle fizzled out
				particles.remove(particle)
			else:
				# Move the particle in an arc and reduce size
				matrix.circle((int(particle['x']), int(particle['y'])), int(particle['psize']), pcolor, -1)
    
		matrix.show()
