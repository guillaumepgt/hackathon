"""Tic-Tac-Toe core simulator and local Gym-like environment for RL."""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from .common import make_step_rng, system_seed
from .compat import BaseEnv, spaces


@dataclass(frozen=True)
class TicTacToeConfig:
    size: int = 3
    max_steps: int = 9
    opponent_mistake_prob: float = 0.15  # "IA optimale avec quelques erreurs"


class TicTacToeCore:
    ACTIONS = {
        "00": "Place at row 0 col 0",
        "01": "Place at row 0 col 1",
        "02": "Place at row 0 col 2",
        "10": "Place at row 1 col 0",
        "11": "Place at row 1 col 1",
        "12": "Place at row 1 col 2",
        "20": "Place at row 2 col 0",
        "21": "Place at row 2 col 1",
        "22": "Place at row 2 col 2",
    }
    OBSERVATION_SCHEMA = [f"cell_{r}{c}" for r in range(3) for c in range(3)] + ["turn_flag"]

    def __init__(self, seed=None, config=None):
        self.default_seed = seed
        self.config = config or TicTacToeConfig()

    def get_actions(self):
        return dict(self.ACTIONS)

    def reset(self, seed=None):
        episode_seed = self.default_seed if seed is None else seed
        if episode_seed is None:
            episode_seed = system_seed()
        return {
            "seed": int(episode_seed),
            "step": 0,
            "board": [["", "", ""], ["", "", ""], ["", "", ""]],
            "current_player": "X",  # agent
            "done": False,
            "result": None,
        }

    def normalize_state(self, state):
        normalized = dict(state)
        normalized.setdefault("seed", self.default_seed or 0)
        normalized.setdefault("step", 0)
        normalized.setdefault("board", [["", "", ""], ["", "", ""], ["", "", ""]])
        normalized.setdefault("current_player", "X")
        normalized.setdefault("done", False)
        normalized.setdefault("result", None)
        return normalized

    def _winner(self, board):
        lines = list(board)
        lines.extend([[board[0][c], board[1][c], board[2][c]] for c in range(3)])
        lines.append([board[0][0], board[1][1], board[2][2]])
        lines.append([board[0][2], board[1][1], board[2][0]])
        for line in lines:
            if line[0] and line[0] == line[1] == line[2]:
                return line[0]
        return None

    def _available_actions(self, board):
        return [f"{r}{c}" for r in range(3) for c in range(3) if board[r][c] in ("", None)]

    def _apply(self, board, action, player):
        r, c = int(action[0]), int(action[1])
        new_board = [row[:] for row in board]
        new_board[r][c] = player
        return new_board

    def _choose_opponent_action(self, board, seed, step):
        rng = make_step_rng(seed, step, "tictactoe_opponent")
        actions = self._available_actions(board)
        if not actions:
            return None

        # Mistake path
        if rng.random() < self.config.opponent_mistake_prob:
            return rng.choice(actions)

        # Try win as O
        for a in actions:
            if self._winner(self._apply(board, a, "O")) == "O":
                return a

        # Block X
        for a in actions:
            if self._winner(self._apply(board, a, "X")) == "X":
                return a

        # Heuristic fallback
        if "11" in actions:
            return "11"
        corners = [a for a in ("00", "02", "20", "22") if a in actions]
        if corners:
            return rng.choice(corners)
        return rng.choice(actions)

    def is_valid_action(self, action, state):
        if state.get("done", False):
            return False
        if action not in self.ACTIONS:
            return False
        r, c = int(action[0]), int(action[1])
        return state["board"][r][c] in ("", None)

    def observe(self, state):
        normalized = self.normalize_state(state)
        mapping = {"X": 1.0, "O": -1.0, "": 0.0, None: 0.0}
        obs = [mapping.get(normalized["board"][r][c], 0.0) for r in range(3) for c in range(3)]
        turn_flag = 1.0 if normalized.get("current_player") == "X" else -1.0
        obs.append(turn_flag)
        return obs

    def step(self, state, action):
        s = self.normalize_state(state)

        if not self.is_valid_action(action, s):
            s["done"] = True
            s["result"] = "lose"
            return s, -1.0, True, {"result": "lose", "error": "Invalid action"}

        # Agent move (X)
        board = self._apply(s["board"], action, "X")
        s["step"] += 1

        w = self._winner(board)
        if w == "X":
            s.update({"board": board, "done": True, "result": "win"})
            return s, 1.0, True, {"result": "win"}

        actions_left = self._available_actions(board)
        if not actions_left or s["step"] >= self.config.max_steps:
            s.update({"board": board, "done": True, "result": "tie"})
            return s, 1.0, True, {"result": "tie"}

        # Opponent move (O)
        opp_action = self._choose_opponent_action(board, s["seed"], s["step"])
        if opp_action is not None:
            board = self._apply(board, opp_action, "O")
            s["step"] += 1

        w = self._winner(board)
        if w == "O":
            s.update({"board": board, "done": True, "result": "lose"})
            return s, -1.0, True, {"result": "lose"}

        actions_left = self._available_actions(board)
        if not actions_left or s["step"] >= self.config.max_steps:
            s.update({"board": board, "done": True, "result": "tie"})
            return s, 1.0, True, {"result": "tie"}

        s.update({"board": board, "current_player": "X", "done": False, "result": None})
        return s, -0.01, False, {}  # léger coût de pas

    def terminal_points(self, result, state):
        if result == "win":
            return 1
        if result == "tie":
            return 1
        if result == "lose":
            return -1
        return 0

    def summary(self, state):
        s = self.normalize_state(state)
        return {
            "board": s["board"],
            "step": s["step"],
            "done": s["done"],
            "result": s.get("result"),
            "observation": self.observe(s),
            "observation_schema": list(self.OBSERVATION_SCHEMA),
            "action_list": self._available_actions(s["board"]),
        }


class TicTacToeEnv(BaseEnv):
    """Gym-like environment for Tic-Tac-Toe with built-in opponent."""

    metadata = {"render_modes": []}

    def __init__(self, seed=None):
        self.core = TicTacToeCore(seed=seed)
        self.action_names = list(self.core.get_actions().keys())
        self.observation_schema = list(self.core.OBSERVATION_SCHEMA)
        self.action_space = spaces.Discrete(len(self.action_names))
        self.observation_space = spaces.Box(
            low=-1.0,
            high=1.0,
            shape=(len(self.observation_schema),),
            dtype=np.float32,
        )
        self.state = None

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed, options=options)
        self.state = self.core.reset(seed=seed)
        observation = np.asarray(self.core.observe(self.state), dtype=np.float32)
        return observation, {
            "action_names": list(self.action_names),
            "observation_schema": list(self.observation_schema),
            "action_mask": self._action_mask(),
        }

    def _action_mask(self):
        available = set(self.core.summary(self.state)["action_list"])
        return np.asarray([1 if a in available else 0 for a in self.action_names], dtype=np.int8)

    def step(self, action):
        action_name = action if isinstance(action, str) else self.action_names[int(action)]
        self.state, reward, done, info = self.core.step(self.state, action_name)
        observation = np.asarray(self.core.observe(self.state), dtype=np.float32)
        truncated = False
        terminated = done and not truncated
        info = {
            **info,
            "action_mask": self._action_mask(),
        }
        if done and "result" in info:
            info["score_points"] = self.core.terminal_points(info["result"], self.state)
        return observation, float(reward), terminated, truncated, info

    def render(self):
        return self.core.summary(self.state or self.core.reset())