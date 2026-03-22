import numpy as np
from collections import deque
from hackathon_rl_envs.compat import BaseEnv, spaces

GRID_STR = [
    "##########",
    "#.#.....##",
    "#........#",
    "#..S.....#",
    "##.#.....#",
    "#######D##",
    "#.......#",
    "#.......##",
    "##...#E..#",
    "##########",
]

class KeyDoorEnv(BaseEnv):
    metadata = {"render_modes": []}
    ACTION_NAMES = ["up", "down", "left", "right"]
    MOVES = [(0, -1), (0, 1), (-1, 0), (1, 0)]

    def __init__(self, seed=None):
        super().__init__()
        self.grid = [list(row) for row in GRID_STR]
        self.rows = len(self.grid)
        self.cols = max(len(row) for row in self.grid)

        for row in self.grid:
            while len(row) < self.cols:
                row.append('#')

        self.max_steps = 80
        self.start_pos = self.exit_pos = self.key_pos = None

        for y, row in enumerate(self.grid):
            for x, cell in enumerate(row):
                if cell == 'S': self.start_pos = (x, y)
                if cell == 'E': self.exit_pos  = (x, y)
                if cell == 'K': self.key_pos   = (x, y)

        self.action_space = spaces.Discrete(len(self.ACTION_NAMES))
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(10,), dtype=np.float32
        )
        self.player_pos = self.start_pos
        self.has_key = False
        self.steps = 0
        self._prev_dist = 0

    def _dist(self, x, y, dx, dy):
        d, cx, cy = 0, x + dx, y + dy
        while 0 <= cy < self.rows and 0 <= cx < self.cols:
            cell = self.grid[cy][cx]
            if cell == '#' or (cell == 'D' and not self.has_key):
                break
            d += 1
            cx += dx
            cy += dy
        return d

    def _get_obs(self):
        x, y = self.player_pos
        ex, ey = self.exit_pos
        kx = (self.key_pos[0] - x) / self.cols if self.key_pos and not self.has_key else 0.0
        ky = (self.key_pos[1] - y) / self.rows if self.key_pos and not self.has_key else 0.0

        return np.array([
            x  / (self.cols - 1),
            y  / (self.rows - 1),
            self._dist(x, y,  0, -1) / self.rows,
            self._dist(x, y,  0,  1) / self.rows,
            self._dist(x, y, -1,  0) / self.cols,
            self._dist(x, y,  1,  0) / self.cols,
            kx, ky,
            (ex - x) / self.cols,
            (ey - y) / self.rows,
            ], dtype=np.float32)

    def _bfs_dist(self):
        target = self.exit_pos if self.has_key else (self.key_pos or self.exit_pos)
        queue = deque([(self.player_pos, 0)])
        visited = {self.player_pos}

        while queue:
            (x, y), d = queue.popleft()
            if (x, y) == target: return d

            for dx, dy in self.MOVES:
                nx, ny = x + dx, y + dy
                if (0 <= ny < self.rows and 0 <= nx < self.cols):
                    cell = self.grid[ny][nx]
                    if cell == '#': continue
                    if cell == 'D' and not self.has_key: continue
                    if (nx, ny) not in visited:
                        visited.add((nx, ny))
                        queue.append(((nx, ny), d + 1))
        return self.rows + self.cols

    def reset(self, *, seed=None, options=None):
        self.player_pos = self.start_pos
        self.has_key = False
        self.steps = 0
        self._prev_dist = self._bfs_dist()
        return self._get_obs(), {"action_names": self.ACTION_NAMES}

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

        if cell == 'D' and not self.has_key:
            truncated = self.steps >= self.max_steps
            return self._get_obs(), -5.0, False, truncated, {}

        self.player_pos = (nx, ny)

        if cell == 'K' and not self.has_key:
            self.has_key = True
            self._prev_dist = self._bfs_dist()
            return self._get_obs(), +10.0, False, False, {}

        if cell == 'E':
            speed_bonus = max(0, (self.max_steps - self.steps) * 0.5)
            return self._get_obs(), 100.0 + speed_bonus, True, False, {"result": "win"}

        dist_after = self._bfs_dist()
        shaping = (self._prev_dist - dist_after) * 2.0 - 0.1
        self._prev_dist = dist_after

        truncated = self.steps >= self.max_steps
        info = {"result": "timeout"} if truncated else {}

        return self._get_obs(), shaping, False, truncated, info