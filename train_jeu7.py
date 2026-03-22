import os
import time
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import EvalCallback
from stable_baselines3.common.vec_env import SubprocVecEnv, VecNormalize, DummyVecEnv
from stable_baselines3.common.monitor import Monitor

from hackathon_rl_envs.lava_maze import LavaMazeEnv

def make_env(rank):
    def _init():
        env = LavaMazeEnv()
        return Monitor(env)
    return _init

if __name__ == "__main__":
    num_cpu = 18
    print(f"🚀 Lancement du cluster d'entraînement sur {num_cpu} cœurs...")

    env = SubprocVecEnv([make_env(i) for i in range(num_cpu)])

    env = VecNormalize(env, norm_obs=True, norm_reward=True, clip_obs=10.)

    eval_env = DummyVecEnv([lambda: Monitor(LavaMazeEnv())])
    eval_env = VecNormalize(eval_env, norm_obs=True, norm_reward=False, clip_obs=10.)

    eval_env.training = False

    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        learning_rate=3e-4,
        n_steps=1024,
        batch_size=256,
        tensorboard_log="./logs/lava_maze_ppo/"
    )

    os.makedirs('./artifacts/lava_maze_ppo/', exist_ok=True)

    eval_freq_per_cpu = max(10000 // num_cpu, 1)
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path='./artifacts/lava_maze_ppo/',
        log_path='./logs/lava_maze_ppo/',
        eval_freq=eval_freq_per_cpu,
        deterministic=True,
        render=False
    )

    print("🔥 Décollage pour 3 000 000 d'étapes...")
    start_time = time.time()

    model.learn(total_timesteps=3000000, callback=eval_callback)

    model.save("artifacts/lava_maze_ppo/final_model")
    env.save("artifacts/lava_maze_ppo/vec_normalize.pkl")

    env.close()

    elapsed = time.time() - start_time
    print(f"✅ Entraînement terminé en {elapsed/60:.1f} minutes !")