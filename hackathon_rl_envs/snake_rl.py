"""Snake core simulator and local Gym-like environment for RL."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .common import make_step_rng, system_seed
from .compat import BaseEnv, spaces


@dataclass(frozen=True)
class SnakeConfig:
    grid_size: int = 20
    max_steps: int = 500
    target_length: int = 40
    step_reward: float = 0.01
    food_reward: float = 1.0
    death_reward: float = -1.0
    win_reward: float = 3.0


class SnakeCore:
    ACTIONS = {
        "up": "Move up",
        "down": "Move down",
        "left": "Move left",
        "right": "Move right",
    }
    ACTION_ORDER = ("up", "down", "left", "right")
    VECTORS = {
        "up": (0, -1),
        "down": (0, 1),
        "left": (-1, 0),
        "right": (1, 0),
    }
    OPPOSITE = {"up": "down", "down": "up", "left": "right", "right": "left"}

    OBSERVATION_SCHEMA = (
        "danger_up",
        "danger_down",
        "danger_left",
        "danger_right",
        "food_up",
        "food_down",
        "food_left",
        "food_right",
        "dir_up",
        "dir_down",
        "dir_left",
        "dir_right",
    )

    def __init__(self, seed=None, config=None):
        self.default_seed = seed
        self.config = config or SnakeConfig()

    def get_actions(self):
        return dict(self.ACTIONS)

    def reset(self, seed=None):
        episode_seed = self.default_seed if seed is None else seed
        if episode_seed is None:
            episode_seed = system_seed()

        g = self.config.grid_size
        cx, cy = g // 2, g // 2
        snake = [(cx, cy), (cx - 1, cy), (cx - 2, cy)]

        state = {
            "seed": int(episode_seed),
            "step": 0,
            "snake": snake,
            "direction": "right",
            "food": None,
            "score": 0,
            "done": False,
            "result": None,
        }
        state["food"] = self._place_food(state)
        return state

    def normalize_state(self, state):
        normalized = dict(state)
        normalized.setdefault("seed", self.default_seed or 0)
        normalized.setdefault("step", 0)
        normalized.setdefault("snake", [])
        normalized.setdefault("direction", "right")
        normalized.setdefault("food", None)
        normalized.setdefault("score", 0)
        normalized.setdefault("done", False)
        normalized.setdefault("result", None)
        normalized["snake"] = [tuple(p) for p in normalized["snake"]]
        if normalized["food"] is not None:
            normalized["food"] = tuple(normalized["food"])
        return normalized

    def _collision(self, pos, snake):
        x, y = pos
        g = self.config.grid_size
        if x < 0 or x >= g or y < 0 or y >= g:
            return True
        return pos in snake

    def _place_food(self, state):
        snake = set(state["snake"])
        g = self.config.grid_size
        free_cells = [(x, y) for y in range(g) for x in range(g) if (x, y) not in snake]
        if not free_cells:
            return None
        rng = make_step_rng(state["seed"], state["step"], "snake_food")
        return free_cells[rng.randrange(len(free_cells))]

    def is_valid_action(self, action, state):
        if action not in self.ACTIONS:
            return False
        if state.get("done", False):
            return False
        return self.OPPOSITE.get(action) != state.get("direction")

    def observe(self, state):
        s = self.normalize_state(state)
        snake = s["snake"]
        head = snake[0]
        body = set(snake[1:])
        food = s["food"]
        direction = s["direction"]

        def coll(x, y):
            return self._collision((x, y), body)

        hx, hy = head
        danger_up = 1.0 if coll(hx, hy - 1) else 0.0
        danger_down = 1.0 if coll(hx, hy + 1) else 0.0
        danger_left = 1.0 if coll(hx - 1, hy) else 0.0
        danger_right = 1.0 if coll(hx + 1, hy) else 0.0

        if food is None:
            food_up = food_down = food_left = food_right = 0.0
        else:
            fx, fy = food
            food_up = 1.0 if fy < hy else 0.0
            food_down = 1.0 if fy > hy else 0.0
            food_left = 1.0 if fx < hx else 0.0
            food_right = 1.0 if fx > hx else 0.0

        dir_up = 1.0 if direction == "up" else 0.0
        dir_down = 1.0 if direction == "down" else 0.0
        dir_left = 1.0 if direction == "left" else 0.0
        dir_right = 1.0 if direction == "right" else 0.0

        return np.asarray(
            [
                danger_up,
                danger_down,
                danger_left,
                danger_right,
                food_up,
                food_down,
                food_left,
                food_right,
                dir_up,
                dir_down,
                dir_left,
                dir_right,
            ],
            dtype=np.float32,
        )

    def step(self, state, action):
        s = self.normalize_state(state)
        if s["done"]:
            return s, 0.0

        if isinstance(action, int):
            if 0 <= action < len(self.ACTION_ORDER):
                action_name = self.ACTION_ORDER[action]
            else:
                action_name = s["direction"]
        else:
            action_name = str(action).lower().strip()

        # Reverse move ignored => keep current direction
        if not self.is_valid_action(action_name, s):
            action_name = s["direction"]

        dx, dy = self.VECTORS[action_name]
        hx, hy = s["snake"][0]
        new_head = (hx + dx, hy + dy)

        s["step"] += 1
        s["direction"] = action_name

        body_without_tail = s["snake"][:-1]
        if self._collision(new_head, set(body_without_tail)):
            s["done"] = True
            s["result"] = "lose"
            return s, float(self.config.death_reward)

        new_snake = [new_head] + s["snake"]

        reward = float(self.config.step_reward)
        if s["food"] is not None and new_head == tuple(s["food"]):
            s["score"] += 1
            reward = float(self.config.food_reward)
            if len(new_snake) >= self.config.target_length:
                s["snake"] = new_snake
                s["done"] = True
                s["result"] = "win"
                return s, float(self.config.win_reward)
            s["snake"] = new_snake
            s["food"] = self._place_food(s)
        else:
            new_snake.pop()
            s["snake"] = new_snake

        if s["step"] >= self.config.max_steps:
            s["done"] = True
            s["result"] = "max_steps"

        return s, reward

    def terminal_points(self, result, state):
        if result == "win":
            return 3.0
        if result == "lose":
            return -1.0
        return 0.0

    def summary(self, state):
        s = self.normalize_state(state)
        return {
            "step": int(s["step"]),
            "length": int(len(s["snake"])),
            "score": int(s["score"]),
            "direction": s["direction"],
            "done": bool(s["done"]),
            "result": s["result"],
        }


class SnakeEnv(BaseEnv):
    """Gym-like environment for Snake."""

    metadata = {"render_modes": []}

    def __init__(self, seed=None):
        self.core = SnakeCore(seed=seed)
        self.action_space = spaces.Discrete(4)
        self.observation_space = spaces.Box(low=0.0, high=1.0, shape=(12,), dtype=np.float32)
        self._state = None

    def reset(self, *, seed=None, options=None):
        try:
            super().reset(seed=seed, options=options)
        except TypeError:
            super().reset(seed=seed)
        self._state = self.core.reset(seed=seed)
        obs = self.core.observe(self._state)
        info = {
            "action_mask": self._action_mask(),
            "result": None,
            "score": int(self._state["score"]),
            "length": len(self._state["snake"]),
        }
        return obs, info

    def _action_mask(self):
        if self._state is None:
            return [1, 1, 1, 1]
        direction = self._state.get("direction", "right")
        opposite = self.core.OPPOSITE.get(direction)
        return [0 if a == opposite else 1 for a in self.core.ACTION_ORDER]

    def step(self, action):
        if self._state is None:
            self.reset()

        self._state, reward = self.core.step(self._state, int(action))
        obs = self.core.observe(self._state)

        result = self._state.get("result")
        terminated = bool(result in {"win", "lose"})
        truncated = bool(result == "max_steps")

        info = {
            "action_mask": self._action_mask(),
            "result": result,
            "score": int(self._state["score"]),
            "length": len(self._state["snake"]),
            "step": int(self._state["step"]),
        }
        return obs, float(reward), terminated, truncated, info

    def render(self):
        if self._state is None:
            return
        g = self.core.config.grid_size
        board = [["." for _ in range(g)] for _ in range(g)]
        for i, (x, y) in enumerate(self._state["snake"]):
            board[y][x] = "H" if i == 0 else "o"
        food = self._state.get("food")
        if food is not None:
            fx, fy = food
            board[fy][fx] = "*"
        print("\n".join("".join(row) for row in board))
        print(self.core.summary(self._state))