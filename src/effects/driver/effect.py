import math
import time
import numpy as np
import random

def run(matrix, config):
    """
    A pseudo-3D driving effect with an enriched sky (stars, moon, clouds, aircraft).
    """
    # 1. ROBUST CONFIGURATION PARSING
    if not isinstance(config, dict):
        config = {}

    width = config.get("pixel_width", 128)
    height = config.get("pixel_height", 64)
    
    effect_cfg = config.get("effect")
    if not isinstance(effect_cfg, dict):
        effect_cfg = {}

    speed = 1.0
    try:
        speed = float(effect_cfg.get("speed", 1.0))
    except (TypeError, ValueError):
        speed = 1.0

    # 2. COLOR SETTINGS
    color_sky = (5, 10, 25)      # Very dark night sky
    color_moon = (220, 220, 255)
    color_star = (200, 200, 255)
    color_cloud = (40, 40, 50)    # Dark, moody clouds
    color_aircraft = (255, 255, 255)
    color_aircraft_light = (255, 0, 0)
    
    color_road = (30, 30, 30)     
    color_stripe = (255, 255, 255) 
    color_car = (10, 10, 10)      
    color_taillight = (255, 0, 0) 
    color_grass = (5, 20, 5)      
    color_tree_trunk = (60, 40, 20)
    color_tree_leaves = (10, 60, 10)
    color_sign_post = (100, 100, 100)
    color_sign_face = (255, 255, 0)

    # 3. PRE-GENERATED SKY ELEMENTS
    # Stars: list of (x, y, phase)
    stars = []
    for _ in range(40):
        stars.append({
            'x': random.randint(0, width - 1),
            'y': random.randint(0, int(height * 0.4)),
            'phase': random.uniform(0, math.pi * 2)
        })

    # 4. PERSPECTIVE & ENTITY SETTINGS
    horizon_y = int(height * 0.45)
    road_top_width = width * 0.15
    road_bottom_width = width * 0.9
    
    # entities: handles trees (z-movement), clouds (x-movement), and aircraft (x-movement)
    entities = []
    start_time = time.monotonic()

    def get_poly(points):
        return [np.array(points, dtype=np.int32)]

    while matrix.ready():
        t = (time.monotonic() - start_time) * speed
        matrix.reset() 

        # --- SPAWN LOGIC ---
        # Spawn Roadside Objects (Trees/Signs)
        if random.random() < 0.02 * speed:
            side = random.choice([-1, 1])
            etype = random.choice(['tree', 'sign'])
            entities.append({'type': 'roadside', 'subtype': etype, 'side': side, 'z': 0.0})

        # Spawn Clouds (Horizontal movement)
        if random.random() < 0.005 * speed:
            entities.append({'type': 'cloud', 'x': -30, 'y': random.randint(5, horizon_y - 10), 'w': random.randint(20, 40)})

        # Spawn Aircraft (Horizontal movement)
        if random.random() < 0.001 * speed:
            entities.append({'type': 'aircraft', 'x': -10, 'y': random.randint(5, horizon_y - 15)})

        # --- DRAW SKY (Layered) ---
        # 1. Sky Base
        matrix.polyfill(get_poly([(0, 0), (width, 0), (width, horizon_y), (0, horizon_y)]), color_sky)
        
        # 2. Moon
        matrix.circle((int(width * 0.8), int(height * 0.15)), 8, color_moon, -1)
        
        # 3. Stars (Twinkling)
        for s in stars:
            brightness = 0.5 + 0.5 * math.sin(t * 2 + s['phase'])
            # We use a simple line or a tiny dot for stars
            star_col = [int(c * brightness) for c in color_star]
            matrix.line((s['x'], s['y']), (s['x'], s['y']), star_col, 1)

        # 4. Clouds (Drawn before road/trees)
        for ent in entities:
            if ent['type'] == 'cloud':
                ent['x'] += 0.2 * speed # Slow drift
                if ent['x'] > width + 40:
                    # Re-spawn cloud on the left
                    ent['x'] = -40
                    ent['y'] = random.randint(5, horizon_y - 10)
                
                # Draw a "cloudy" cluster of circles
                cx, cy = int(ent['x']), ent['y']
                matrix.circle((cx, cy), ent['w']//3, color_cloud, -1)
                matrix.circle((cx + 10, cy + 5), ent['w']//4, color_cloud, -1)
                matrix.circle((cx - 10, cy + 5), ent['w']//4, color_cloud, -1)

            elif ent['type'] == 'aircraft':
                ent['x'] += 1.5 * speed # Faster fly-by
                if ent['x'] > width + 20:
                    ent['x'] = -20
                    ent['y'] = random.randint(5, horizon_y - 15)
                
                # Draw a tiny aircraft (a line and a blinking light)
                ax, ay = int(ent['x']), ent['y']
                matrix.line((ax-4, ay), (ax+4, ay), color_aircraft, 1) # Body
                matrix.line((ax, ay-2), (ax, ay+2), color_aircraft, 1) # Wings
                
                # Blinking light
                if int(t * 10) % 2 == 0:
                    matrix.circle((ax, ay), 1, color_aircraft_light, -1)

        # --- DRAW ROAD & ROADSIDE ---
        # Grass
        matrix.polyfill(get_poly([(0, horizon_y), (int(width * 0.4), horizon_y), (0, height)]), color_grass)
        matrix.polyfill(get_poly([(int(width * 0.6), horizon_y), (width, horizon_y), (width, height)]), color_grass)

        # Road
        r_lt, r_rt = int((width // 2) - (road_top_width // 2)), int((width // 2) + (road_top_width // 2))
        r_lb, r_rb = int((width // 2) - (road_bottom_width // 2)), int((width // 2) + (road_bottom_width // 2))
        matrix.polyfill(get_poly([(r_lt, horizon_y), (r_rt, horizon_y), (r_rb, height), (r_lb, height)]), color_road)

        # Road Stripes
        num_stripes = 6
        for i in range(num_stripes):
            z_s = ((i / num_stripes) + (t * 0.5) % (1.0 / num_stripes)) % 1.0
            y_p = horizon_y + int((z_s**2) * (height - horizon_y))
            s_h, s_w = max(1, int((z_s**2) * 15)), max(1, int((z_s**2) * (road_bottom_width * 0.08)))
            x1, x2 = int((width // 2) - (s_w // 2)), int((width // 2) + (s_w // 2))
            if y_p < height:
                matrix.polyfill(get_poly([(x1, y_p), (x2, y_p), (x2, min(height, y_p+s_h)), (x1, min(height, y_p+s_h))]), color_stripe)

        # --- DRAW ROADSIDE ENTITIES (Trees/Signs) ---
        for i in range(len(entities) - 1, -1, -1):
            ent = entities[i]
            if ent['type'] != 'roadside': continue # Skip clouds/planes here
            
            ent['z'] += 0.01 * speed
            if ent['z'] >= 1.0:
                entities.pop(i)
                continue

            z = ent['z']
            scale = z**2 
            cur_road_w = road_top_width + z * (road_bottom_width - road_top_width)
            r_left_x = (width // 2) - (cur_road_w / 2)
            r_right_x = (width // 2) + (cur_road_w / 2)
            
            margin = 10
            obj_x = r_left_x - (margin * z) if ent['side'] == -1 else r_right_x + (margin * z)
            obj_y = horizon_y + int((z**2) * (height - horizon_y))

            if ent['subtype'] == 'tree':
                tw, th = max(1, int(3 * scale)), max(1, int(10 * scale))
                matrix.polyfill(get_poly([(int(obj_x), obj_y), (int(obj_x+tw), obj_y), (int(obj_x+tw), obj_y-th), (int(obj_x), obj_y-th)]), color_tree_trunk)
                lw, lh = max(1, int(8 * scale)), max(1, int(12 * scale))
                lx_c = int(obj_x + (tw/2))
                matrix.polyfill(get_poly([(lx_c - lw, obj_y), (lx_c + lw, obj_y), (lx_c, obj_y - th - lh)]), color_tree_leaves)
            elif ent['subtype'] == 'sign':
                ph = max(1, int(12 * scale))
                px = int(obj_x + (2 * scale))
                matrix.line((px, obj_y), (px, obj_y - ph), color_sign_post, 1)
                sw, sh = max(1, int(6 * scale)), max(1, int(5 * scale))
                matrix.polyfill(get_poly([(px-sw, obj_y-ph), (px+sw, obj_y-ph), (px+sw, obj_y-ph-sh), (px-sw, obj_y-ph-sh)]), color_sign_face)

        # --- DRAW CAR ---
        cw, ch = width // 2, height // 5
        cx, cy = (width // 2) - (cw // 2), height - ch - 5
        matrix.polyfill(get_poly([(cx, cy), (cx + cw, cy), (cx + cw, cy + ch), (cx, cy + ch)]), color_car)
        l_w, l_h = cw // 6, ch // 3
        matrix.polyfill(get_poly([(cx + 5, cy + 5), (cx + 5 + l_w, cy + 5), (cx + 5 + l_w, cy + 5 + l_h), (cx + 5, cy + 5 + l_h)]), color_taillight)
        matrix.polyfill(get_poly([(cx + cw - 5 - l_w, cy + 5), (cx + cw - 5, cy + 5), (cx + cw - 5, cy + 5 + l_h), (cx + cw - 5 - l_w, cy + 5 + l_h)]), color_taillight)

        matrix.show()
