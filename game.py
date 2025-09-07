import random
from utils import generate_obstacles, generate_portal_pair

BOARD_SIZE = 10

class Game:
    def __init__(self, user_id, username):
        self.user_id = user_id
        self.username = username
        self.level = 1
        self.level_names = {1: "Пещера 🕳️", 2: "Равнина 🌾", 3: "Лес 🌲"}
        self.level_name = self.level_names[self.level]
        self.snake = [(5, 5)]
        self.direction = "right"
        self.score = 0
        self.is_alive = True

        # Создаём структуры
        self.obstacles = generate_obstacles(self.level)
        self.mobs = []
        self.bonus = None
        self.bonus_type = None
        self.bonus_timer = 0
        self.portal1 = None
        self.portal2 = None
        self.mobs_eaten = 0
        self.bonuses_collected = set()

        # Спавним объекты
        self.food = self.spawn_food()
        self.spawn_bonus()
        self.spawn_portal()
        self.spawn_mobs()

    def spawn_food(self):
        for _ in range(100):  # 🔥 ФИКС: защита от бесконечного цикла
            x = random.randint(0, BOARD_SIZE - 1)
            y = random.randint(0, BOARD_SIZE - 1)
            pos = (x, y)
            if (pos not in self.snake and pos not in self.obstacles and
                pos != self.bonus and pos != self.portal1 and
                pos != self.portal2 and pos not in self.mobs):
                return pos
        # Если не нашли — возвращаем безопасную позицию
        return (0, 0)

    def spawn_bonus(self):
        if random.random() < 0.3 and not self.bonus:
            bonus_types = ["speed_up", "grow", "invincibility", "score_x2", "clear_path", "reverse", "teleport"]
            self.bonus_type = random.choice(bonus_types)
            self.bonus = self.spawn_food()
            self.bonus_timer = 10

    def spawn_portal(self):
        if random.random() < 0.2:
            try:
                self.portal1, self.portal2 = generate_portal_pair(self.snake, self.obstacles, self.food, BOARD_SIZE)
            except:
                self.portal1 = self.portal2 = None  # 🔥 ФИКС: защита от ошибки

    def spawn_mobs(self):
        mob_count = {1: 1, 2: 2, 3: 3}[self.level]
        for _ in range(mob_count):
            for _ in range(50):  # 🔥 ФИКС: защита от бесконечного цикла
                x = random.randint(0, BOARD_SIZE - 1)
                y = random.randint(0, BOARD_SIZE - 1)
                pos = (x, y)
                if (pos not in self.snake and pos not in self.obstacles and
                    pos != self.food and pos != self.bonus and
                    pos != self.portal1 and pos != self.portal2 and
                    pos not in self.mobs):
                    self.mobs.append(pos)
                    break

    def move(self, direction):
        if not self.is_alive:
            return

        self.direction = direction
        head_x, head_y = self.snake[0]

        if direction == "up":
            new_head = (head_x - 1, head_y)
        elif direction == "down":
            new_head = (head_x + 1, head_y)
        elif direction == "left":
            new_head = (head_x, head_y - 1)
        elif direction == "right":
            new_head = (head_x, head_y + 1)
        else:
            return

        # Проверки
        if not (0 <= new_head[0] < BOARD_SIZE and 0 <= new_head[1] < BOARD_SIZE):
            self.is_alive = False
            return

        if new_head in self.snake[1:]:  # 🔥 ФИКС: не проверяем голову
            self.is_alive = False
            return

        if new_head in self.obstacles:
            self.is_alive = False
            return

        # Порталы
        if self.portal1 and self.portal2:
            if new_head == self.portal1:
                new_head = self.portal2
            elif new_head == self.portal2:
                new_head = self.portal1

        ate_food = False
        if new_head == self.food:
            self.score += 1
            ate_food = True
            self.food = self.spawn_food()
            self.spawn_bonus()
            self.spawn_portal()
            if self.score % 10 == 0 and self.level < 3:
                self.level += 1
                self.level_name = self.level_names[self.level]
                self.obstacles = generate_obstacles(self.level)
                self.spawn_mobs()

        if new_head == self.bonus and self.bonus:
            self.apply_bonus()
            self.bonus = None
            self.bonus_type = None

        if new_head in self.mobs and len(self.snake) >= 5:
            mob_points = random.randint(1, 3)
            self.score += mob_points
            self.mobs_eaten += 1
            self.mobs.remove(new_head)
            self.spawn_mobs()

        self.snake.insert(0, new_head)
        if not ate_food:
            self.snake.pop()

        if self.bonus:
            self.bonus_timer -= 1
            if self.bonus_timer <= 0:
                self.bonus = None
                self.bonus_type = None

    def apply_bonus(self):
        if self.bonus_type:
            self.bonuses_collected.add(self.bonus_type)

        bonus_effects = {
            "speed_up": lambda: setattr(self, 'score', self.score + 2),
            "grow": lambda: (self.snake.append(self.snake[-1]), setattr(self, 'score', self.score + 3)),
            "invincibility": lambda: setattr(self, 'score', self.score + 5),
            "score_x2": lambda: setattr(self, 'score', self.score + 4),
            "clear_path": lambda: (
                [self.obstacles.pop(0) for _ in range(min(3, len(self.obstacles)))],
                setattr(self, 'score', self.score + 5)
            ),
            "reverse": lambda: (self.snake.reverse(), setattr(self, 'score', self.score + 2)),
            "teleport": self._teleport_head
        }

        effect = bonus_effects.get(self.bonus_type)
        if effect:
            effect()

    def _teleport_head(self):
        for _ in range(50):
            x = random.randint(0, BOARD_SIZE - 1)
            y = random.randint(0, BOARD_SIZE - 1)
            pos = (x, y)
            if pos not in self.obstacles and pos != self.food and pos not in self.mobs:
                self.snake[0] = pos
                self.score += 3
                return

    def render_board(self):
        board = [["⬜" for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]

        # Препятствия
        obstacle_icons = {1: "🪨", 2: "🌿", 3: "🌳"}
        for obs in self.obstacles:
            board[obs[0]][obs[1]] = obstacle_icons.get(self.level, "🪨")

        # Объекты
        if self.food:
            fx, fy = self.food
            board[fx][fy] = "🍎"

        bonus_icons = {
            "speed_up": "⚡",
            "grow": "💊",
            "invincibility": "🛡️",
            "score_x2": "💰",
            "clear_path": "🧨",
            "reverse": "🔄",
            "teleport": "🌀"
        }
        if self.bonus and self.bonus_type:
            bx, by = self.bonus
            board[bx][by] = bonus_icons.get(self.bonus_type, "🎁")

        if self.portal1:
            px, py = self.portal1
            board[px][py] = "🔵"
        if self.portal2:
            px, py = self.portal2
            board[px][py] = "🔴"

        for mob in self.mobs:
            mx, my = mob
            board[mx][my] = "👾"

        # Змея
        for i, (x, y) in enumerate(self.snake):
            if i == 0:
                board[x][y] = "🟢"
            else:
                board[x][y] = "🟩"

        return "\n".join("".join(row) for row in board)
