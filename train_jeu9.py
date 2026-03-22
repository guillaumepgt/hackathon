import os
import time
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv, VecNormalize
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.callbacks import EvalCallback
from hackathon_rl_envs.lava_key_DoorMaze import LavaKeyDoorEnv

def make_env(rank):
    def _init():
        return Monitor(LavaKeyDoorEnv(seed=int(time.time()) + rank))
    return _init

if __name__ == "__main__":
    print("\n🚀 DÉMARRAGE DE L'ENTRAÎNEMENT JEU 9 (18 CŒURS)")
    num_cpu = 18

    env = SubprocVecEnv([make_env(i) for i in range(num_cpu)])
    env = VecNormalize(env, norm_obs=True, norm_reward=True, clip_obs=10.)

    eval_env = DummyVecEnv([lambda: Monitor(LavaKeyDoorEnv())])
    eval_env = VecNormalize(eval_env, norm_obs=True, norm_reward=False, clip_obs=10.)
    eval_env.training = False

    model = PPO("MlpPolicy", env, verbose=1, learning_rate=3e-4, n_steps=1024, batch_size=256)

    os.makedirs('./artifacts/jeu9_ppo/', exist_ok=True)
    eval_freq_per_cpu = max(10000 // num_cpu, 1)

    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path='./artifacts/jeu9_ppo/',
        eval_freq=eval_freq_per_cpu,
        deterministic=True
    )

    start_time = time.time()
    model.learn(total_timesteps=3000000, callback=eval_callback)

    model.save("artifacts/jeu9_ppo/final_model")
    env.save("artifacts/jeu9_ppo/vec_normalize.pkl")
    print(f"\n✅ Terminé en {(time.time() - start_time)/60:.1f} minutes !")