import os
import time
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv, VecNormalize
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.callbacks import EvalCallback

from hackathon_rl_envs.Partial_Visibility import FogMazeEnv

def make_env(rank):
    def _init():
        env = FogMazeEnv(seed=int(time.time()) + rank)
        return Monitor(env)
    return _init

if __name__ == "__main__":
    print("\n🚀 DÉMARRAGE DE L'ENTRAÎNEMENT JEU 6 : BROUILLARD (18 CŒURS)")
    num_cpu = 18

    env = SubprocVecEnv([make_env(i) for i in range(num_cpu)])
    env = VecNormalize(env, norm_obs=True, norm_reward=True, clip_obs=10.)

    eval_env = DummyVecEnv([lambda: Monitor(FogMazeEnv(seed=42))])
    eval_env = VecNormalize(eval_env, norm_obs=True, norm_reward=False, clip_obs=10.)
    eval_env.training = False

    policy_kwargs = dict(net_arch=[256, 256])

    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        learning_rate=3e-4,
        n_steps=1024,
        batch_size=256,
        ent_coef=0.02,
        policy_kwargs=policy_kwargs,
        tensorboard_log="./logs_fog_maze/"
    )

    os.makedirs('./artifacts/fog_maze_ppo/', exist_ok=True)
    eval_freq_per_cpu = max(10000 // num_cpu, 1)

    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path='./artifacts/fog_maze_ppo/',
        eval_freq=eval_freq_per_cpu,
        deterministic=True
    )

    print("\n🔥 Décollage pour 3 000 000 d'étapes !")
    start_time = time.time()

    try:
        model.learn(total_timesteps=3000000, callback=eval_callback)
    except KeyboardInterrupt:
        print("\n🛑 Interruption manuelle. Sauvegarde d'urgence...")

    model.save("artifacts/fog_maze_ppo/final_model")
    env.save("artifacts/fog_maze_ppo/vec_normalize.pkl")
    env.close()

    print(f"\n✅ Terminé en {(time.time() - start_time)/60:.1f} minutes !")