import time
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
from players.shared_api_client import GameAPIClient
from hackathon_rl_envs.adaptive_traffic_racing import AdaptiveTrafficRacingEnv
import requests

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

    def _safe_request(self, fn, *args, **kwargs):
        delay = 1.5
        for attempt in range(5):
            try:
                return fn(*args, **kwargs)
            except requests.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code == 429:
                    print(f"  [429] Attente {delay:.1f}s...")
                    time.sleep(delay)
                    delay *= 2
                else:
                    raise
        raise RuntimeError("Trop de tentatives échouées (429)")

    def _override_action(self, action_str, state):
        lane = state["lane"]
        speed = state["speed"]
        gaps = state["lane_gaps"]
        num_lanes = len(gaps)

        ahead = gaps[lane]["ahead"] if gaps[lane]["ahead"] is not None else 999.0

        # Danger immédiat → freiner
        if ahead < 5.0:
            return "brake"

        # Force accélération jusqu'à vitesse 10 si voie libre
        if ahead > 15.0 and speed < 10.0:
            return "accelerate"

        # Empêcher sortie de route ou changement dangereux
        if action_str == "left":
            if lane == 0: return "keep"
            if (gaps[lane-1]["behind"] or 999.0) < 3.0: return "keep"
        if action_str == "right":
            if lane == num_lanes - 1: return "keep"
            if (gaps[lane+1]["behind"] or 999.0) < 3.0: return "keep"

        return action_str

    def play_game(self):
        start = self._safe_request(self.api.start_game, self.game_id)
        session_id = start["gamesessionid"]

        state = start.get("state")
        if state is None:
            payload = self._safe_request(self.api.get_state, session_id)
            state = payload["state"]

        while True:
            obs_norm = self.vec_env.normalize_obs(
                np.array([state["observation"]], dtype=np.float32)
            )
            action_idx = int(self.model.predict(obs_norm, deterministic=True)[0].item())
            action_str = self._override_action(self.actions[action_idx], state)

            print(f"  -> Prog: {state.get('progress', 0):.1f}/130 | "
                  f"Vit: {state['speed']:.1f} | Action: {action_str.upper()}")

            time.sleep(1.1)
            result = self._safe_request(self.api.act, session_id, action_str)
            status = result.get("status")

            if status != "continue":
                print(f"FIN : {status}")
                try:
                    self.api.stop_game(session_id, allow_missing=True)
                except:
                    pass
                return

            state = result["state"]

if __name__ == "__main__":
    TOKEN = "a729a0ed3b8f5ca37e5b8f95a9fa61d0"
    URL = "https://24hcode2026.plaiades.fr"

    client = GameAPIClient(URL, TOKEN)
    bot = TrafficAIPilot(client)

    course = 1
    while True:
        print(f"\n===== Partie {course} =====")
        try:
            bot.play_game()
        except Exception as e:
            print(f"Erreur : {e}")
            time.sleep(3)
        course += 1
        time.sleep(1.2)