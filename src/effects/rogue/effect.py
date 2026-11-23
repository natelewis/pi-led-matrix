import random
import math
from collections import deque

# Constants
TILE_SIZE = 4 
VISION_RADIUS = 5  

# Tile types
WALL, FLOOR, PLAYER, ENEMY = "#", ".", "@", "E"

def run(matrix, config):
    """Turn-based ASCII Dungeon Crawler - FIXED MOVEMENT & COMBAT"""
    width, height = config["pixel_width"], config["pixel_height"]
    cols, rows = width // TILE_SIZE, height // TILE_SIZE
    
    # --- 1. DUNGEON GENERATION ---
    game_map = [[1 for _ in range(cols)] for _ in range(rows)]
    rooms = []

    def create_room():
        w, h = random.randint(3, 6), random.randint(3, 5)
        x, y = random.randint(1, cols-w-1), random.randint(1, rows-h-1)
        return {"x": x, "y": y, "w": w, "h": h, "cx": x + w//2, "cy": y + h//2, "visited": False}

    for _ in range(15):
        new_room = create_room()
        overlap = False
        for r in rooms:
            if (new_room["x"] < r["x"] + r["w"] + 1 and new_room["x"] + new_room["w"] + 1 > r["x"] and
                new_room["y"] < r["y"] + r["h"] + 1 and new_room["y"] + new_room["h"] + 1 > r["y"]):
                overlap = True; break
        if not overlap:
            for ry in range(new_room["y"], new_room["y"] + new_room["h"]):
                for rx in range(new_room["x"], new_room["x"] + new_room["w"]):
                    game_map[ry][rx] = 0
            if rooms:
                p, t = rooms[-1], new_room
                for x in range(min(p["cx"], t["cx"]), max(p["cx"], t["cx"]) + 1): game_map[p["cy"]][x] = 0
                for y in range(min(p["cy"], t["cy"]), max(p["cy"], t["cy"]) + 1): game_map[y][t["cx"]] = 0
            rooms.append(new_room)

    # --- 2. PATHFINDING (BFS) ---
    def find_path(start, target):
        if start == target: return []
        queue = deque([(start, [])])
        visited = {tuple(start)}
        while queue:
            (cx, cy), path = queue.popleft()
            if (cx, cy) == tuple(target): return path
            for dx, dy in [(0,1), (0,-1), (1,0), (-1,0)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < cols and 0 <= ny < rows and game_map[ny][nx] == 0 and (nx, ny) not in visited:
                    visited.add((nx, ny)); queue.append(((nx, ny), path + [(nx, ny)]))
        return None

    # --- 3. INITIALIZE STATE ---
    player_pos = [rooms[0]["cx"], rooms[0]["cy"]]
    enemy_pos = [rooms[-1]["cx"], rooms[-1]["cy"]]
    
    player_hp, enemy_hp = 100, 50

    explored_map = [[False for _ in range(cols)] for _ in range(rows)]
    color_wall, color_floor, color_dim = matrix.color("white"), matrix.color("black"), matrix.color("gray")
    color_player, color_enemy = matrix.color("cyan"), matrix.color("red")

    def draw_tile(tx, ty, char, color_override=None):
        px, py = tx * TILE_SIZE, ty * TILE_SIZE
        color = color_override if color_override else (color_wall if char == WALL else color_floor)
        if char == WALL:
            for x in range(TILE_SIZE):
                for y in range(TILE_SIZE): matrix.pixel((px + x, py + y), color)
        elif char == FLOOR:
            matrix.pixel((px + TILE_SIZE//2, py + TILE_SIZE//2), color)
        elif char == PLAYER:
            for i in range(TILE_SIZE):
                matrix.pixel((px + i, py + TILE_SIZE//2), color_player)
                matrix.pixel((px + TILE_SIZE//2, py + i), color_player)
        elif char == ENEMY:
            for x in range(TILE_SIZE):
                for y in range(TILE_SIZE): matrix.pixel((px + x, py + y), color_enemy)

    # --- 4. MAIN LOOP ---
    while matrix.ready():
        # A. FOG OF WAR & ROOM VISITING
        px, py = player_pos
        for dy in range(-VISION_RADIUS, VISION_RADIUS + 1):
            for dx in range(-VISION_RADIUS, VISION_RADIUS + 1):
                if dx*dx + dy*dy <= VISION_RADIUS*VISION_RADIUS:
                    nx, ny = px + dx, py + dy
                    if 0 <= nx < cols and 0 <= ny < rows:
                        explored_map[ny][nx] = True
                        for r in rooms:
                            if r["x"] <= px < r["x"] + r["w"] and r["y"] <= py < r["y"] + r["h"]:
                                r["visited"] = True

        # B. DRAWING
        matrix.reset(matrix.color("black"))
        for y in range(rows):
            for x in range(cols):
                if explored_map[y][x]:
                    dist = math.sqrt((x - px)**2 + (y - py)**2)
                    is_vis = dist <= VISION_RADIUS
                    if game_map[y][x] == 1:
                        draw_tile(x, y, WALL, color_override=color_wall if is_vis else color_dim)
                    else:
                        if is_vis: draw_tile(x, y, FLOOR)
                        else: draw_tile(x, y, ".", color_override=matrix.color("black"))

        if math.sqrt((enemy_pos[0]-px)**2 + (enemy_pos[1]-py)**2) <= VISION_RADIUS:
            draw_tile(enemy_pos[0], enemy_pos[1], ENEMY)
        draw_tile(px, py, PLAYER)
        matrix.show()

        # C. COMBAT (NO COOLDOWN)
        if player_pos == enemy_pos:
            player_hp -= 25  
            enemy_hp -= 30   
            
            # KNOCKBACK: Push the enemy away
            push_x, push_y = random.choice([(1,0), (-1,0), (0,1), (0,-1)])
            new_ex, new_ey = enemy_pos[0] + push_x, enemy_pos[1] + push_y
            
            if 0 <= new_ex < cols and 0 <= new_ey < rows and game_map[new_ey][new_ex] == 0:
                enemy_pos = [new_ex, new_ey]
            else:
                enemy_pos[0] = (enemy_pos[0] + 1) % cols
            
            matrix.reset(matrix.color("red"))
            matrix.show()
            matrix.delay(50)

        # Handle Death/Respawn
        if enemy_hp <= 0:
            other_rooms = [r for r in rooms if not (r["x"] <= enemy_pos[0] < r["x"] + r["w"] and r["y"] <= enemy_pos[1] < r["y"] + r["h"])]
            r = random.choice(other_rooms if other_rooms else rooms)
            enemy_pos = [r["cx"], r["cy"]]
            enemy_hp = 50
            
        if player_hp <= 0:
            player_pos = [rooms[0]["cx"], rooms[0]["cy"]]
            player_hp = 100
        
        # D. PLAYER MOVEMENT (Hunter/Explorer)
        target_pos = None
        if enemy_hp > 0:
            target_pos = [enemy_pos[0], enemy_pos[1]] 
        else:
            min_dist = float('inf')
            target_room = None
            for r in rooms:
                if not r["visited"]:
                    d = math.sqrt((r["cx"]-px)**2 + (r["cy"]-py)**2)
                    if d < min_dist:
                        min_dist = d; target_room = r
            if target_room: target_pos = [target_room["cx"], target_room["cy"]]

        next_player_step = None
        if target_pos:
            path = find_path(player_pos, target_pos)
            if path:
                next_player_step = path[0]
            elif player_pos == target_pos:
                next_player_step = player_pos # STAY on target
        else:
            # EXPLORATION: Wander randomly
            dx, dy = random.choice([(0,1),(0,-1),(1,0),(-1,0)])
            if 0 <= px+dx < cols and 0 <= py+dy < rows and game_map[py+dy][px+dx] == 0:
                next_player_step = [px+dx, py+dy]
        
        if next_player_step:
            player_pos[0], player_pos[1] = next_player_step[0], next_player_step[1]

        # E. ENEMY MOVEMENT (Smart Chase)
        next_enemy_step = None
        if enemy_hp > 0:
            # Enemy targets player
            enemy_path = find_path(enemy_pos, player_pos)
            if enemy_path:
                next_enemy_step = enemy_path[0]
            elif enemy_pos == player_pos:
                next_enemy_step = enemy_pos # STAY on player

        if next_enemy_step:
            enemy_pos[0], enemy_pos[1] = next_enemy_step[0], next_enemy_step[1]

        matrix.delay(150)
