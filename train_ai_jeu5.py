import time
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
from players.shared_api_client import GameAPIClient
from hackathon_rl_envs.adaptive_traffic_racing import AdaptiveTrafficRacingEnv

class TrafficAIPilot:
    def __init__(self, api_client):
        self.api = api_client
        self.game_id = 5
        self.actions = ["left", "right", "keep", "accelerate", "brake"]

        self.model = PPO.load("models/traffic_ppo_model")

        dummy_env = DummyVecEnv([lambda: AdaptiveTrafficRacingEnv()])
        self.vec_env = VecNormalize.load("models/traffic_ppo_norm.pkl", dummy_env)
        self.vec_env.training = False
        self.vec_env.norm_reward = False

    def play_game(self):
        start = self.api.start_game(self.game_id)
        session_id = start["gamesessionid"]

        while True:
            time.sleep(0.9)
            payload = self.api.get_state(session_id)
            state = payload["state"]
            obs_brut = state["observation"]

            obs_array = np.array([obs_brut], dtype=np.float32)
            obs_norm = self.vec_env.normalize_obs(obs_array)
            action_array, _ = self.model.predict(obs_norm, deterministic=True)
            action_idx = int(action_array.item())
            action_str = self.actions[action_idx]

            lane = state["lane"]
            speed = state["speed"]
            gaps = state["lane_gaps"]

            ahead_dist = gaps[lane]["ahead"] if gaps[lane]["ahead"] is not None else 999.0

            if action_str in ["keep", "brake"] and ahead_dist > 15.0:
                if speed < 4.8:
                    action_str = "accelerate"
            print(f"  -> Prog: {state.get('progress', 0):.1f}/130 | Vit: {speed:.1f} | Action: {action_str.upper()}")

            time.sleep(0.9)
            result = self.api.act(session_id, action_str)
            status = result.get("status")

            if status != "continue":
                print(f"FIN : {status}")
                try:
                    time.sleep(0.9)
                    self.api.stop_game(session_id, allow_missing=True)
                except:
                    pass
                break

if __name__ == "__main__":
    TOKEN = "a729a0ed3b8f5ca37e5b8f95a9fa61d0"
    URL = "https://24hcode2026.plaiades.fr"

    client = GameAPIClient(URL, TOKEN)
    bot = TrafficAIPilot(client)

    course = 1
    while True:
        print(f"\n=======================")
        print(f"    Partie : {course}")
        print(f"=======================")
        try:
            bot.play_game()
        except Exception as e:
            print(f"Erreur : {e}")
            time.sleep(2)
        course += 1
        time.sleep(0.5)