from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from .common import system_seed
from .compat import BaseEnv, spaces


@dataclass(frozen=True)
class RushHourConfig:
    grid_size: int = 6
    max_steps: int = 200
    num_vehicles: int = 22


class RushHourCore:
    """Core simulator for Rush Hour that mirrors the API behavior."""

    OBSERVATION_SCHEMA = (
        "red_car_row",
        "red_car_col",
        "red_car_steps_to_exit",
        "num_vehicles",
        "grid_flat",
    )

    def __init__(self, seed=None, config=None):
        self.default_seed = seed
        self.config = config or RushHourConfig()

    def reset(self, seed=None):
        episode_seed = self.default_seed if seed is None else seed
        if episode_seed is None:
            episode_seed = system_seed()

        np.random.seed(int(episode_seed) % (2**32))
        vehicles = self._generate_random_puzzle()

        return {
            "seed": int(episode_seed),
            "step": 0,
            "vehicles": vehicles,
            "done": False,
            "result": None,
            "grid_size": self.config.grid_size,
        }

    def _generate_random_puzzle(self):
        """Generate a random but solvable Rush Hour puzzle."""
        grid_size = self.config.grid_size
        grid = [[False for _ in range(grid_size)] for _ in range(grid_size)]
        vehicles = []

        # Place red car X at random position on row 2, with length 2
        x_col = np.random.randint(0, grid_size - 2)
        vehicles.append({
            "id": "X",
            "pos": [2, x_col],
            "orientation": "h",
            "length": 2
        })
        grid[2][x_col] = True
        grid[2][x_col + 1] = True

        # Add other vehicles randomly
        vehicle_ids = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        placed_count = 1
        max_vehicles = min(self.config.num_vehicles, 22)

        attempts = 0
        while placed_count < max_vehicles and attempts < 100:
            attempts += 1
            vehicle_id = vehicle_ids[placed_count]
            is_horizontal = np.random.choice([True, False])
            length = np.random.randint(2, 4)

            if is_horizontal:
                col = np.random.randint(0, grid_size - length + 1)
                row = np.random.randint(0, grid_size)

                if not any(grid[row][col + i] for i in range(length)):
                    for i in range(length):
                        grid[row][col + i] = True
                    vehicles.append({
                        "id": vehicle_id,
                        "pos": [row, col],
                        "orientation": "h",
                        "length": length
                    })
                    placed_count += 1
            else:
                row = np.random.randint(0, grid_size - length + 1)
                col = np.random.randint(0, grid_size)

                if not any(grid[row + i][col] for i in range(length)):
                    for i in range(length):
                        grid[row + i][col] = True
                    vehicles.append({
                        "id": vehicle_id,
                        "pos": [row, col],
                        "orientation": "v",
                        "length": length
                    })
                    placed_count += 1

        return vehicles

    def normalize_state(self, state):
        normalized = dict(state)
        normalized.setdefault("seed", self.default_seed or 0)
        normalized.setdefault("step", 0)
        normalized.setdefault("done", False)
        normalized.setdefault("result", None)
        normalized.setdefault("grid_size", self.config.grid_size)
        return normalized

    def is_winning(self, state):
        """Check if red car X has exited the grid."""
        for v in state["vehicles"]:
            if v["id"] == "X":
                col = v["pos"][1]
                length = v["length"]
                exit_col = state.get("grid_size", self.config.grid_size)
                if col + length >= exit_col + 1:
                    return True
        return False

    def get_valid_moves(self, state):
        """Get all valid moves for the current state."""
        vehicles = state["vehicles"]
        grid_size = state.get("grid_size", self.config.grid_size)

        # Build occupancy grid
        grid = [[False for _ in range(grid_size)] for _ in range(grid_size)]
        for v in vehicles:
            row, col = v["pos"]
            if v["orientation"] == "h":
                for i in range(v["length"]):
                    if col + i < grid_size:
                        grid[row][col + i] = True
            else:
                for i in range(v["length"]):
                    if row + i < grid_size:
                        grid[row + i][col] = True

        valid_moves = []
        vehicle_id_map = {v["id"]: idx for idx, v in enumerate(vehicles)}

        for vehicle_id in vehicle_id_map:
            idx = vehicle_id_map[vehicle_id]
            v = vehicles[idx]
            row, col = v["pos"]

            if v["orientation"] == "h":
                # Try move left
                if col > 0 and not grid[row][col - 1]:
                    valid_moves.append((idx, "left", f"move_{vehicle_id}_left"))
                # Try move right
                if col + v["length"] < grid_size and not grid[row][col + v["length"]]:
                    valid_moves.append((idx, "right", f"move_{vehicle_id}_right"))
                elif vehicle_id == "X" and col + v["length"] == grid_size:
                    # Special case: red car can exit
                    valid_moves.append((idx, "right", f"move_{vehicle_id}_right"))
            else:
                # Try move up
                if row > 0 and not grid[row - 1][col]:
                    valid_moves.append((idx, "up", f"move_{vehicle_id}_up"))
                # Try move down
                if row + v["length"] < grid_size and not grid[row + v["length"]][col]:
                    valid_moves.append((idx, "down", f"move_{vehicle_id}_down"))

        return valid_moves

    def step(self, state, action_idx):
        """Execute an action (action_idx is index into get_valid_moves())."""
        normalized = self.normalize_state(state)

        if normalized["done"]:
            return normalized, -1.0, True, {"error": "Game over"}

        valid_moves = self.get_valid_moves(normalized)

        if action_idx < 0 or action_idx >= len(valid_moves):
            return normalized, -0.5, False, {"error": "Invalid action"}

        vehicle_idx, direction, action_name = valid_moves[action_idx]
        vehicles = [dict(v) for v in normalized["vehicles"]]
        v = vehicles[vehicle_idx]
        row, col = v["pos"]

        # Apply move
        if direction == "left":
            v["pos"] = [row, col - 1]
        elif direction == "right":
            v["pos"] = [row, col + 1]
        elif direction == "up":
            v["pos"] = [row - 1, col]
        elif direction == "down":
            v["pos"] = [row + 1, col]

        new_state = {
            **normalized,
            "step": normalized["step"] + 1,
            "vehicles": vehicles,
        }

        # Calculate reward
        reward = -0.1
        done = False
        info = {"action_name": action_name}

        # Reward for moving the red car
        old_red_car = None
        new_red_car = None
        for v_old in normalized["vehicles"]:
            if v_old["id"] == "X":
                old_red_car = v_old
        for v_new in new_state["vehicles"]:
            if v_new["id"] == "X":
                new_red_car = v_new

        if old_red_car and new_red_car:
            if new_red_car["pos"][1] > old_red_car["pos"][1]:
                reward += 0.5

        # Check win condition
        if self.is_winning(new_state):
            done = True
            new_state["result"] = "win"
            reward = 100.0
            info["result"] = "win"
        elif new_state["step"] >= self.config.max_steps:
            done = True
            new_state["result"] = "max_steps"
            reward = -5.0
            info["result"] = "max_steps"

        new_state["done"] = done

        return new_state, float(reward), done, info

    def observe(self, state):
        """Create observation vector."""
        normalized = self.normalize_state(state)
        grid_size = normalized.get("grid_size", self.config.grid_size)

        # Find red car X
        red_car = None
        for v in normalized["vehicles"]:
            if v["id"] == "X":
                red_car = v
                break

        observation = []

        if red_car:
            row, col = red_car["pos"]
            observation.append(float(row) / (grid_size - 1) if grid_size > 1 else 0.5)
            observation.append(float(col) / grid_size)

            # Distance to exit
            steps_to_exit = max(0, grid_size - (col + red_car["length"]))
            observation.append(float(steps_to_exit) / grid_size)
        else:
            observation.extend([0.0, 0.0, 0.0])

        # Number of vehicles (normalized)
        observation.append(float(len(normalized["vehicles"])) / self.config.num_vehicles)

        # Occupancy grid (flattened)
        grid = [[0.0 for _ in range(grid_size)] for _ in range(grid_size)]
        for v in normalized["vehicles"]:
            v_row, v_col = v["pos"]
            if v["orientation"] == "h":
                for i in range(v["length"]):
                    if v_col + i < grid_size:
                        grid[v_row][v_col + i] = 1.0
            else:
                for i in range(v["length"]):
                    if v_row + i < grid_size:
                        grid[v_row + i][v_col] = 1.0

        for row in grid:
            observation.extend(row)

        return observation


class RushHourEnv(BaseEnv):
    """Gym-like environment for Rush Hour."""

    metadata = {"render_modes": []}

    def __init__(self, seed=None):
        self.core = RushHourCore(seed=seed)
        grid_size = self.core.config.grid_size

        # Observation: [red_row, red_col, steps_to_exit, num_vehicles, grid_36]
        obs_size = 4 + (grid_size * grid_size)

        self.observation_space = spaces.Box(
            low=0.0,
            high=1.0,
            shape=(obs_size,),
            dtype=np.float32,
        )

        # Action space will be determined dynamically
        self.action_space = spaces.Discrete(200)

        self.state = None
        self._valid_moves = []

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed, options=options)
        self.state = self.core.reset(seed=seed)
        self._valid_moves = self.core.get_valid_moves(self.state)
        observation = np.asarray(self.core.observe(self.state), dtype=np.float32)
        return observation, {}

    def step(self, action):
        action_idx = int(np.clip(action, 0, len(self._valid_moves) - 1)) if self._valid_moves else 0

        self.state, reward, done, info = self.core.step(self.state, action_idx)
        self._valid_moves = self.core.get_valid_moves(self.state)

        observation = np.asarray(self.core.observe(self.state), dtype=np.float32)
        truncated = info.get("result") == "max_steps"
        terminated = done and not truncated

        return observation, float(reward), terminated, truncated, info

    def render(self):
        return self.core.normalize_state(self.state or self.core.reset())