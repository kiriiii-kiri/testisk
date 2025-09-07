import random
from utils import generate_obstacles, generate_portal_pair

BOARD_SIZE = 10

class Game:
    def __init__(self, user_id, username):
        self.user_id = user_id
        self.username = username
        self.level = 1  # 1=Пещера, 2=Равнина, 3=Лес
        self.level_names = {1: "Пещера 🕳️", 2: "Равнина 🌾", 3: "Лес 🌲"}
        self.level_name = self.level_names[self.level]
        self.snake = [(5, 5)]  # начальная позиция
        self.direction = "right"
        self.score = 0
        self.is_alive = True
        self.food = self.spawn_food()
        self.bonus = None
        self.bonus_type = None
        self.bonus_timer = 0
        self.portal1 = None
        self.portal2 = None
        self.mobs = []
        self.obstacles = generate_obstacles(self.level)
        self.mobs_eaten = 0
        self.bonuses_collected = set()
        self.spawn_bonus()
        self.spawn_portal()
        self.spawn_mobs()

    def spawn_food(self):
        while True:
            x = random.randint(0, BOARD_SIZE - 1)
            y = random.randint(0, BOARD_SIZE - 1)
            pos = (x, y)
            if pos not in self.snake and pos not in self.obstacles and pos != self.bonus and pos != self.portal1 and pos != self.portal2 and pos not in self.mobs:
                return pos

    def spawn_bonus(self):
        if random.random() < 0.3 and not self.bonus:
            bonus_types = ["speed_up", "grow", "invincibility", "score_x2", "clear_path", "reverse", "teleport"]
            self.bonus_type = random.choice(bonus_types)
            self.bonus = self.spawn_food()
            self.bonus_timer = 10  # исчезнет через 10 ходов

    def spawn_portal(self):
        if random.random() < 0.2:
            self.portal1, self.portal2 = generate_portal_pair(self.snake, self.obstacles, self.food, BOARD_SIZE)

    def spawn_mobs(self):
        mob_count = {1: 1, 2: 2, 3: 3}[self.level]
        for _ in range(mob_count):
            while True:
                x = random.randint(0, BOARD_SIZE - 1)
                y = random.randint(0, BOARD_SIZE - 1)
                pos = (x, y)
                if pos not in self.snake and pos not in self.obstacles and pos != self.food and pos != self.bonus and pos != self.portal1 and pos != self.portal2 and pos not in self.mobs:
                    self.mobs.append(pos)
                    break

    def move(self, direction):
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

        # Проверка выхода за границы
        if not (0 <= new_head[0] < BOARD_SIZE and 0 <= new_head[1] < BOARD_SIZE):
            self.is_alive = False
            return

        # Проверка столкновения с собой
        if new_head in self.snake:
            self.is_alive = False
            return

        # Проверка столкновения с препятствием
        if new_head in self.obstacles:
            self.is_alive = False
            return

        # Порталы
        if new_head == self.portal1 and self.portal2:
            new_head = self.portal2
        elif new_head == self.portal2 and self.portal1:
            new_head = self.portal1

        # Съел еду?
        ate_food = False
        if new_head == self.food:
            self.score += 1
            ate_food = True
            self.food = self.spawn_food()
            self.spawn_bonus()
            self.spawn_portal()
            # Повышение уровня каждые 10 очков
            if self.score % 10 == 0 and self.level < 3:
                self.level += 1
                self.level_name = self.level_names[self.level]
                self.obstacles = generate_obstacles(self.level)
                self.spawn_mobs()

        # Съел бонус?
        if new_head == self.bonus and self.bonus:
            self.apply_bonus()
            self.bonus = None
            self.bonus_type = None

        # Съел моба?
        if new_head in self.mobs:
            if len(self.snake) >= 5:  # Только если длина >= 5
                mob_points = random.randint(1, 3)
                self.score += mob_points
                self.mobs_eaten += 1
                self.mobs.remove(new_head)
                self.spawn_mobs()  # Респавн моба

        # Двигаем змею
        self.snake.insert(0, new_head)
        if not ate_food:
            self.snake.pop()

        # Таймер бонуса
        if self.bonus:
            self.bonus_timer -= 1
            if self.bonus_timer <= 0:
                self.bonus = None
                self.bonus_type = None

    def apply_bonus(self):
        self.bonuses_collected.add(self.bonus_type)
        if self.bonus_type == "speed_up":
            # Визуально не влияет — можно добавить скорости в будущем
            self.score += 2
        elif self.bonus_type == "grow":
            self.snake.append(self.snake[-1])  # удлиняем на 1
            self.score += 3
        elif self.bonus_type == "invincibility":
            # Защита на 5 ходов — MVP: просто очки
            self.score += 5
        elif self.bonus_type == "score_x2":
            self.score += 4  # бонус за активацию
        elif self.bonus_type == "clear_path":
            # Убираем 3 случайных препятствия
            for _ in range(min(3, len(self.obstacles))):
                if self.obstacles:
                    self.obstacles.pop(0)
            self.score += 5
        elif self.bonus_type == "reverse":
            self.snake.reverse()
            self.score += 2
        elif self.bonus_type == "teleport":
            # Телепортируем голову в случайное место
            while True:
                x = random.randint(0, BOARD_SIZE - 1)
                y = random.randint(0, BOARD_SIZE - 1)
                pos = (x, y)
                if pos not in self.obstacles and pos != self.food and pos not in self.mobs:
                    self.snake[0] = pos
                    break
            self.score += 3

    def render_board(self):
        board = [["⬜" for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]

        # Препятствия по уровням
        for obs in self.obstacles:
            if self.level == 1:
                board[obs[0]][obs[1]] = "🪨"  # Пещера — камни
            elif self.level == 2:
                board[obs[0]][obs[1]] = "🌿"  # Равнина — кусты
            elif self.level == 3:
                board[obs[0]][obs[1]] = "🌳"  # Лес — деревья

        # Еда
        if self.food:
            fx, fy = self.food
            board[fx][fy] = "🍎"

        # Бонус
        if self.bonus:
            bx, by = self.bonus
            if self.bonus_type == "speed_up":
                board[bx][by] = "⚡"
            elif self.bonus_type == "grow":
                board[bx][by] = "💊"
            elif self.bonus_type == "invincibility":
                board[bx][by] = "🛡️"
            elif self.bonus_type == "score_x2":
                board[bx][by] = "💰"
            elif self.bonus_type == "clear_path":
                board[bx][by] = "🧨"  # Взрыв!
            elif self.bonus_type == "reverse":
                board[bx][by] = "🔄"
            elif self.bonus_type == "teleport":
                board[bx][by] = "🌀"  # Портал-бонус (отдельно от парных порталов)

        # Порталы
        if self.portal1:
            px, py = self.portal1
            board[px][py] = "🔵"
        if self.portal2:
            px, py = self.portal2
            board[px][py] = "🔴"

        # Мобы
        for mob in self.mobs:
            mx, my = mob
            board[mx][my] = "👾"

        # Змея
        for i, (x, y) in enumerate(self.snake):
            if i == 0:
                board[x][y] = "🟢"  # Голова
            else:
                board[x][y] = "🟩"  # Тело

        return "\n".join("".join(row) for row in board)
