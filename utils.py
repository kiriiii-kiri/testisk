import random

def generate_obstacles(level):
    count = {1: 8, 2: 10, 3: 15}[level]
    obstacles = set()
    while len(obstacles) < count:
        x = random.randint(0, 9)
        y = random.randint(0, 9)
        obstacles.add((x, y))
    return list(obstacles)

def generate_portal_pair(snake, obstacles, food, size):
    positions = []
    for x in range(size):
        for y in range(size):
            pos = (x, y)
            if pos not in snake and pos not in obstacles and pos != food:
                positions.append(pos)

    if len(positions) < 2:
        return None, None

    p1 = random.choice(positions)
    positions.remove(p1)
    p2 = random.choice(positions)

    return p1, p2
