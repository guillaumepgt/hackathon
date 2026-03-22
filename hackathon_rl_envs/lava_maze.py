import numpy as np
from collections import deque
from hackathon_rl_envs.compat import BaseEnv, spaces

GRID_STR = [
    "##########",
    "#.#...L..#",
    "#....LL..#",
    "#.L....L##",
    "##.#LL..L#",
    "#..S.....#",
    "#L.#.#LL.#",
    "#....E..##",
    "##L.L#L..#",
    "##########",
]

class LavaMazeEnv(BaseEnv):
    metadata = {"render_modes": []}
    ACTION_NAMES = ["up", "down", "left", "right"]
    MOVES = [(0, -1), (0, 1), (-1, 0), (1, 0)]

    def __init__(self, seed=None):
        super().__init__()
        self.grid = [list(row) for row in GRID_STR]
        self.rows = len(self.grid)
        self.cols = len(self.grid[0])
        self.max_steps = 50

        self.start_pos = self.exit_pos = None
        for y, row in enumerate(self.grid):
            for x, cell in enumerate(row):
                if cell == 'S': self.start_pos = (x, y)
                if cell == 'E': self.exit_pos  = (x, y)

        self.action_space = spaces.Discrete(len(self.ACTION_NAMES))
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(8,), dtype=np.float32
        )
        self.player_pos = self.start_pos
        self.steps = 0

    def _dist(self, x, y, dx, dy):
        d, cx, cy = 0, x + dx, y + dy
        while 0 <= cy < self.rows and 0 <= cx < self.cols:
            if self.grid[cy][cx] in ('#', 'L'):
                break
            d += 1
            cx += dx
            cy += dy
        return d

    def _get_obs(self):
        x, y = self.player_pos
        ex, ey = self.exit_pos
        return np.array([
            x  / (self.cols - 1),
            y  / (self.rows - 1),
            self._dist(x, y,  0, -1) / self.rows,
            self._dist(x, y,  0,  1) / self.rows,
            self._dist(x, y, -1,  0) / self.cols,
            self._dist(x, y,  1,  0) / self.cols,
            (ex - x) / self.cols,
            (ey - y) / self.rows,
            ], dtype=np.float32)

    def _bfs_dist(self):
        queue = deque([(self.player_pos, 0)])
        visited = {self.player_pos}
        while queue:
            (x, y), d = queue.popleft()
            if (x, y) == self.exit_pos:
                return d
            for dx, dy in self.MOVES:
                nx, ny = x + dx, y + dy
                if (0 <= ny < self.rows and 0 <= nx < self.cols
                        and self.grid[ny][nx] not in ('#', 'L')
                        and (nx, ny) not in visited):
                    visited.add((nx, ny))
                    queue.append(((nx, ny), d + 1))
        return self.rows + self.cols

    def step(self, action):
        action_name = action if isinstance(action, str) else self.ACTION_NAMES[int(action)]
        dx, dy = self.MOVES[self.ACTION_NAMES.index(action_name)]
        x, y = self.player_pos
        nx, ny = x + dx, y + dy
        self.steps += 1

        if not (0 <= ny < self.rows and 0 <= nx < self.cols) or self.grid[ny][nx] == '#':
            truncated = self.steps >= self.max_steps
            return self._get_obs(), -5.0, False, truncated, {}

        cell = self.grid[ny][nx]
        self.player_pos = (nx, ny)

        if cell == 'L':
            return self._get_obs(), -50.0, True, False, {
                "result": "lose", "score_points": 0
            }

        if cell == 'E':
            speed_bonus = max(0, (self.max_steps - self.steps) * 0.5)
            return self._get_obs(), 100.0 + speed_bonus, True, False, {
                "result": "win", "score_points": 10
            }

        dist_before = self._prev_dist if hasattr(self, '_prev_dist') else self._bfs_dist()
        dist_after  = self._bfs_dist()
        self._prev_dist = dist_after

        shaping = (dist_before - dist_after) * 2.0 - 0.1

        truncated = self.steps >= self.max_steps
        info = {"result": "timeout", "score_points": 0} if truncated else {}
        return self._get_obs(), shaping, False, truncated, info

    def reset(self, *, seed=None, options=None):
        self.player_pos = self.start_pos
        self.steps = 0
        self._prev_dist = self._bfs_dist()
        return self._get_obs(), {"action_names": self.ACTION_NAMES}