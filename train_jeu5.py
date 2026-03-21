import os
import time
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv, VecNormalize
from stable_baselines3.common.monitor import Monitor

from hackathon_rl_envs.adaptive_traffic_racing import AdaptiveTrafficRacingEnv

def make_env():
    def _init():
        env = AdaptiveTrafficRacingEnv()
        return Monitor(env)
    return _init

if __name__ == "__main__":
    print("Début")
    num_cpu = 18
    env = SubprocVecEnv([make_env() for _ in range(num_cpu)])

    env = VecNormalize(env, norm_obs=True, norm_reward=True, clip_obs=10.)

    policy_kwargs = dict(net_arch=[128, 128])

    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        learning_rate=3e-4,
        n_steps=1024,
        batch_size=256,
        ent_coef=0.005,
        policy_kwargs=policy_kwargs
    )
    start_time = time.time()

    model.learn(total_timesteps=3000000)

    elapsed = time.time() - start_time
    print(f"{elapsed/60:.1f} minutes")

    os.makedirs("models", exist_ok=True)
    model.save("models/traffic_ppo_model")
    env.save("models/traffic_ppo_norm.pkl")

    env.close()

    print("✅ Modèle asynchrone sauvegardé !")