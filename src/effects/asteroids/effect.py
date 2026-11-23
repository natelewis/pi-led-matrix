import random
import math

# Density of asteroids (higher = more asteroids)
ASTEROID_DENSITY = 0.001 

# Speed multiplier for the field
SPEED_MULTIPLIER = 1.0

# Background star density
STAR_DENSITY = 0.001

def run(matrix, config):
    """Moving asteroid field with starfield background"""
    width = config["pixel_width"]
    height = config["pixel_height"]
    
    # Scaling factor based on screen size
    scale = max(1, min(width, height) // 40)
    
    # Initialize stars (static/very slow background)
    stars = []
    num_stars = int(width * height * STAR_DENSITY)
    for _ in range(num_stars):
        stars.append({
            "x": random.randint(0, width - 1),
            "y": random.randint(0, height - 1),
            "brightness": random.randint(30, 100)
        })

    # Initialize asteroids
    asteroids = []
    num_asteroids = int(width * height * ASTEROID_DENSITY)
    for _ in range(max(3, num_asteroids)):
        radius = random.randint(2, 5) * scale
        # Velocity: random direction and speed
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(0.5, 2.0) * scale * SPEED_MULTIPLIER
        
        asteroids.append({
            "x": random.randint(0, width - 1),
            "y": random.randint(0, height - 1),
            "vx": math.cos(angle) * speed,
            "vy": math.sin(angle) * speed,
            "r": radius,
            "brightness": random.randint(150, 255),
            # We use an offset to make them look slightly "craggy"
            "crag_seed": random.random() 
        })

    while matrix.ready():
        matrix.reset()

        # 1. Draw Stars (Background)
        for star in stars:
            b = star["brightness"]
            matrix.pixel((star["x"], star["y"]), (b, b, b))

        # 2. Update and Draw Asteroids
        for ast in asteroids:
            # Update position
            ast["x"] += ast["vx"]
            ast["y"] += ast["vy"]

            # Screen Wrap (Toroidal geometry)
            if ast["x"] < -ast["r"]:
                ast["x"] = width + ast["r"]
            elif ast["x"] > width + ast["r"]:
                ast["x"] = -ast["r"]
                
            if ast["y"] < -ast["r"]:
                ast["y"] = height + ast["r"]
            elif ast["y"] > height + ast["r"]:
                ast["y"] = -ast["r"]

            # Draw Asteroid
            # To make them look less like perfect circles, we draw the main body
            # and then a few "craggy" pixels/dots around the edge
            color = (ast["brightness"], ast["brightness"], ast["brightness"])
            
            # Main body
            matrix.circle((int(ast["x"]), int(ast["y"])), ast["r"], color, -1)
            
            # Add a few "jagged" bits to break the circle silhouette
            # We use the crag_seed to ensure the "shape" stays relatively consistent
            # as it moves, preventing it from looking like it's "flickering"
            for i in range(5):
                angle = (ast["crag_seed"] * 10) + (i * (math.pi * 2 / 5))
                offset_x = int(math.cos(angle) * (ast["r"] + 1))
                offset_y = int(math.sin(angle) * (ast["r"] + 1))
                matrix.pixel(
                    (int(ast["x"]) + offset_x, int(ast["y"]) + offset_y), 
                    color
                )

        matrix.show()
