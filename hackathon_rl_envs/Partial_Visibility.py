import time
import pickle
import zipfile
import sys
import numpy as np
from pathlib import Path
from collections import deque

from players.shared_api_client import GameAPIClient
from hackathon_rl_envs.compat import BaseEnv, spaces
from hackathon_rl_envs.rl_common import (
    CrossEntropyTrainer, CrossEntropyConfig,
    RunningNormalizer, MLPSoftmaxPolicy
)

import random

def generate_maze(size=10, seed=None):
    rng = random.Random(seed)
    grid = [['#'] * size for _ in range(size)]

    def carve(x, y):
        dirs = [(0,2),(0,-2),(2,0),(-2,0)]
        rng.shuffle(dirs)
        for dx, dy in dirs:
            nx, ny = x+dx, y+dy
            if 0 < nx < size-1 and 0 < ny < size-1 and grid[ny][nx] == '#':
                grid[y+dy//2][x+dx//2] = '.'
                grid[ny][nx] = '.'
                carve(nx, ny)

    grid[1][1] = '.'
    carve(1, 1)
    grid[1][1] = 'S'
    candidates = [(x, y) for y in range(size-2, 0, -1)
                  for x in range(size-2, 0, -1)
                  if grid[y][x] == '.']
    if candidates:
        ex, ey = candidates[0]
        grid[ey][ex] = 'E'
    else:
        grid[size-2][size-2] = 'E'

    return grid


GRID_SIZE    = 10
VIEW_RADIUS  = 2
VIEW_SIDE    = VIEW_RADIUS * 2 + 1
OBS_GRID     = VIEW_SIDE * VIEW_SIDE
OBS_EXTRA    = 4
OBS_SIZE     = OBS_GRID + OBS_EXTRA

CELL_ENCODE = {
    '#': 0.0,   # mur
    '.': 1.0,   # sol
    'S': 1.0,   # départ
    'E': 2.0,   # sortie
    '?': -1.0,  # inconnu
}


class FogMazeEnv(BaseEnv):

    metadata = {"render_modes": []}
    ACTION_NAMES = ["up", "down", "left", "right"]
    MOVES = [(0, -1), (0, 1), (-1, 0), (1, 0)]

    def __init__(self, seed=None):
        super().__init__()
        self.size     = GRID_SIZE
        self.max_steps = 100
        self._seed    = seed

        self.action_space = spaces.Discrete(4)
        self.observation_space = spaces.Box(
            low=-1.0, high=2.0, shape=(OBS_SIZE,), dtype=np.float32
        )
        self.grid       = None
        self.player_pos = None
        self.exit_pos   = None
        self.steps      = 0
        self._prev_dist = 0
        self._visited   = set()

    def _find(self, char):
        for y, row in enumerate(self.grid):
            for x, cell in enumerate(row):
                if cell == char:
                    return (x, y)
        return None

    def _get_obs(self):
        x, y = self.player_pos
        ex, ey = self.exit_pos if self.exit_pos else (x, y)

        window = []
        for dy in range(-VIEW_RADIUS, VIEW_RADIUS+1):
            for dx in range(-VIEW_RADIUS, VIEW_RADIUS+1):
                nx, ny = x+dx, y+dy
                if 0 <= ny < self.size and 0 <= nx < self.size:
                    cell = self.grid[ny][nx]
                    window.append(CELL_ENCODE.get(cell, -1.0))
                else:
                    window.append(0.0)

        extra = [
            x  / (self.size - 1),
            y  / (self.size - 1),
            (ex - x) / self.size,
            (ey - y) / self.size,
            ]
        return np.array(window + extra, dtype=np.float32)

    def _bfs_dist(self):
        if not self.exit_pos:
            return self.size * 2
        queue = deque([(self.player_pos, 0)])
        visited = {self.player_pos}
        while queue:
            (cx, cy), d = queue.popleft()
            if (cx, cy) == self.exit_pos:
                return d
            for dx, dy in self.MOVES:
                nx, ny = cx+dx, cy+dy
                if (0 <= ny < self.size and 0 <= nx < self.size
                        and self.grid[ny][nx] != '#'
                        and (nx, ny) not in visited):
                    visited.add((nx, ny))
                    queue.append(((nx, ny), d+1))
        return self.size * 2

    def reset(self, *, seed=None, options=None):
        use_seed = seed if seed is not None else self._seed
        self.grid       = generate_maze(self.size, seed=use_seed)
        self.player_pos = self._find('S') or (1, 1)
        self.exit_pos   = self._find('E')
        self.steps      = 0
        self._visited   = {self.player_pos}
        self._prev_dist = self._bfs_dist()
        return self._get_obs(), {"action_names": self.ACTION_NAMES}

    def step(self, action):
        action_name = action if isinstance(action, str) else self.ACTION_NAMES[int(action)]
        dx, dy = self.MOVES[self.ACTION_NAMES.index(action_name)]
        x, y   = self.player_pos
        nx, ny = x+dx, y+dy
        self.steps += 1
        truncated = self.steps >= self.max_steps

        if not (0 <= ny < self.size and 0 <= nx < self.size) or self.grid[ny][nx] == '#':
            return self._get_obs(), -2.0, False, truncated, {}

        self.player_pos = (nx, ny)

        if self.grid[ny][nx] == 'E':
            speed_bonus = max(0, (self.max_steps - self.steps) * 0.3)
            return self._get_obs(), 100.0 + speed_bonus, True, False, {
                "result": "win", "score_points": 6
            }

        explore_bonus = 0.5 if (nx, ny) not in self._visited else 0.0
        self._visited.add((nx, ny))

        dist_after  = self._bfs_dist()
        shaping     = (self._prev_dist - dist_after) * 2.0 - 0.05
        self._prev_dist = dist_after

        reward = shaping + explore_bonus
        info   = {"result": "timeout", "score_points": 0} if truncated else {}
        return self._get_obs(), reward, False, truncated, info

    def render(self):
        grid_copy = [row[:] for row in self.grid]
        x, y = self.player_pos
        grid_copy[y][x] = 'P'
        return "\n".join("".join(row) for row in grid_copy)

def train_and_export():
    print("Entraînement CEM en cours...")

    probe    = FogMazeEnv()
    obs_size = probe.observation_space.shape[0]  # 29
    act_size = probe.action_space.n              # 4

    config = CrossEntropyConfig(
        population_size=128,
        elite_fraction=0.2,
        iterations=60,
        hidden_size=64,
        initial_std=0.5,
        min_std=0.02,
        normalizer_episodes_per_seed=3,
        normalizer_max_steps=100,
    )

    trainer = CrossEntropyTrainer(
        env_factory=FogMazeEnv,
        observation_size=obs_size,
        action_size=act_size,
        config=config,
    )

    seeds = list(range(50))
    best_policy, normalizer = trainer.train(seeds=seeds)

    print("Entraînement terminé.")

    Path("models").mkdir(exist_ok=True)
    best_policy.export_checkpoint("models/jeu6_policy.json")

    with open("models/jeu6_norm.pkl", "wb") as f:
        pickle.dump(normalizer.state_dict(), f)

    with zipfile.ZipFile("models/jeu6_model.zip", "w") as zf:
        zf.write("models/jeu6_policy.json", "jeu6_policy.json")
        zf.write("models/jeu6_norm.pkl",    "jeu6_norm.pkl")

    print("Exporté : models/jeu6_model.zip + models/jeu6_norm.pkl")
    return best_policy, normalizer

class FogMazeSolver:
    ACTION_NAMES = ["up", "down", "left", "right"]

    def __init__(self, api_client, policy=None, normalizer=None):
        self.api        = api_client
        self.game_id    = 6
        self.policy     = policy
        self.normalizer = normalizer
        self._env       = FogMazeEnv()

    def _state_to_obs(self, state):
        grid     = state["grid"]
        size     = len(grid)
        x, y     = state["player_pos"]
        exit_pos = state.get("exit_pos")
        ex, ey   = tuple(exit_pos) if exit_pos else (x, y)

        window = []
        for dy in range(-VIEW_RADIUS, VIEW_RADIUS+1):
            for dx in range(-VIEW_RADIUS, VIEW_RADIUS+1):
                nx, ny = x+dx, y+dy
                if 0 <= ny < size and 0 <= nx < size:
                    cell = grid[ny][nx]
                    window.append(CELL_ENCODE.get(cell, -1.0))
                else:
                    window.append(0.0)

        extra = [
            x  / (size - 1),
            y  / (size - 1),
            (ex - x) / size,
            (ey - y) / size,
            ]
        return np.array(window + extra, dtype=np.float32)

    def _fallback_action(self, state):
        """BFS sur les cases connues vers la frontier ou la sortie."""
        memory = {}
        grid   = state["grid"]
        size   = len(grid)
        for y, row in enumerate(grid):
            for x, char in enumerate(row):
                if char != '?':
                    memory[(x, y)] = char

        start    = tuple(state["player_pos"])
        exit_pos = state.get("exit_pos")
        target   = tuple(exit_pos) if exit_pos else None

        queue   = deque([(start, None)])
        visited = {start}

        while queue:
            pos, first_action = queue.popleft()
            cx, cy = pos

            if target and pos == target:
                return first_action
            if not target:
                for dx, dy in ((0,1),(0,-1),(1,0),(-1,0)):
                    if (cx+dx, cy+dy) not in memory:
                        return first_action

            for aname, dx, dy in (("up",0,-1),("down",0,1),("left",-1,0),("right",1,0)):
                nb = (cx+dx, cy+dy)
                if nb not in visited and memory.get(nb, '#') not in ('#', '?'):
                    visited.add(nb)
                    fa = first_action if first_action else aname
                    queue.append((nb, fa))
        return "up"

    def play_game(self):
        session    = self.api.start_game(self.game_id)
        session_id = session["gamesessionid"]
        state      = session.get("state") or self.api.get_state(session_id)["state"]

        for _ in range(150):
            if self.policy and self.normalizer:
                obs        = self.normalizer.normalize(self._state_to_obs(state))
                action_str = self.ACTION_NAMES[self.policy.act(obs)]
            else:
                action_str = self._fallback_action(state)

            res    = self.api.act(session_id, action_str)
            status = res.get("status")
            if status == "win":
                print("Victoire")
                return True
            if status == "lose":
                print("Défaite")
                return False
            state = res["state"]
        return False

if __name__ == "__main__":
    TOKEN = "a729a0ed3b8f5ca37e5b8f95a9fa61d0"
    URL   = "https://24hcode2026.plaiades.fr"

    if "--train" in sys.argv:
        train_and_export()

    else:
        policy = normalizer = None
        if Path("models/jeu6_policy.json").exists():
            policy = MLPSoftmaxPolicy.load_checkpoint("models/jeu6_policy.json")
            with open("models/jeu6_norm.pkl", "rb") as f:
                normalizer = RunningNormalizer.from_state_dict(pickle.load(f))
            print("Modèle IA chargé.")
        else:
            print("Pas de modèle, fallback BFS.")

        client = GameAPIClient(server_url=URL, token=TOKEN, max_calls_per_second=0.9)
        bot    = FogMazeSolver(client, policy, normalizer)

        partie = 1
        while True:
            print(f"\n===== Partie {partie} =====")
            try:
                bot.play_game()
            except Exception as e:
                print(f"Erreur : {e}")
            partie += 1
            time.sleep(0.5)