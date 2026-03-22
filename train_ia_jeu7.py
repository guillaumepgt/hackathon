import time
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
from hackathon_rl_envs.compat import BaseEnv, spaces
from players.shared_api_client import GameAPIClient

class CoquilleVideEnv(BaseEnv):
    def __init__(self):
        super().__init__()
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(8,), dtype=np.float32)
        self.action_space = spaces.Discrete(4)

class PpoLavaPlayer:
    def __init__(self, api_client):
        self.api = api_client
        self.game_id = 7
        self.actions = ["up", "down", "left", "right"]

        self.model = PPO.load("artifacts/lava_maze_ppo/final_model.zip")

        dummy = DummyVecEnv([lambda: CoquilleVideEnv()])
        self.vec_env = VecNormalize.load("artifacts/lava_maze_ppo/vec_normalize.pkl", dummy)
        self.vec_env.training = False
        self.vec_env.norm_reward = False

    def get_observation(self, state):
        grid = state["grid"]
        rows, cols = len(grid), len(grid[0])
        x, y = state["player_pos"]

        ex, ey = 0, 0
        for r in range(rows):
            for c in range(cols):
                if grid[r][c] == 'E': ex, ey = c, r

        def distance_mur(dx, dy):
            d, cx, cy = 0, x + dx, y + dy
            while 0 <= cy < rows and 0 <= cx < cols and grid[cy][cx] not in ('#', 'L'):
                d += 1
                cx += dx
                cy += dy
            return d

        # Création du vecteur de 8 valeurs exact
        return np.array([
            x / (cols - 1),
            y / (rows - 1),
            distance_mur(0, -1) / rows,
            distance_mur(0, 1) / rows,
            distance_mur(-1, 0) / cols,
            distance_mur(1, 0) / cols,
            (ex - x) / cols,
            (ey - y) / rows
        ], dtype=np.float32)

    def play_game(self):
        print("\n🔥 Lancement d'une partie...")
        session = self.api.start_game(self.game_id)
        session_id = session["gamesessionid"]

        state = session.get("state") or self.api.get_state(session_id)["state"]

        while True:
            obs_brut = self.get_observation(state)
            obs_norm = self.vec_env.normalize_obs(np.array([obs_brut], dtype=np.float32))

            action_idx = int(self.model.predict(obs_norm, deterministic=True)[0].item())
            action_str = self.actions[action_idx]

            print(f"  -> Position : {state['player_pos']} | Choix IA : {action_str.upper()}")

            result = self.api.act(session_id, action_str)
            status = result.get("status")

            if status != "continue":
                if status == "win": print("🏆 VICTOIRE !")
                else: print(f"💥 DÉFAITE ({status})")

                try: self.api.stop_game(session_id, allow_missing=True)
                except: pass
                return

            state = result["state"]

if __name__ == "__main__":
    TOKEN = "a729a0ed3b8f5ca37e5b8f95a9fa61d0"
    URL = "https://24hcode2026.plaiades.fr"

    client = GameAPIClient(server_url=URL, token=TOKEN, max_calls_per_second=0.95)
    bot = PpoLavaPlayer(client)

    partie = 1
    while True:
        print(f"\n--- PARTIE {partie} ---")
        try:
            bot.play_game()
        except Exception as e:
            print(f"Erreur : {e}")
            time.sleep(2)
        partie += 1
        time.sleep(1)