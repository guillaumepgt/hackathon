import os
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import EvalCallback
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.monitor import Monitor

from hackathon_rl_envs.noisy_moon_lander import NoisyMoonLanderLiteEnv

def make_env(rank):
    def _init():
        env = NoisyMoonLanderLiteEnv()
        return Monitor(env)
    return _init

if __name__ == "__main__":
    num_cpu = 18
    print(f"🚀 Lancement de l'entraînement massif sur {num_cpu} cœurs...")

    env = SubprocVecEnv([make_env(i) for i in range(num_cpu)])

    eval_env = Monitor(NoisyMoonLanderLiteEnv())

    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        learning_rate=3e-4,
        n_steps=1024,
        batch_size=256,
        gamma=0.99,
        gae_lambda=0.95,
        tensorboard_log="./logs/moonlander_ppo/"
    )
    os.makedirs('./artifacts/noisy_moonlander_ppo/', exist_ok=True)
    eval_freq_per_cpu = max(10000 // num_cpu, 1)

    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path='./artifacts/noisy_moonlander_ppo/',
        log_path='./logs/moonlander_ppo/',
        eval_freq=eval_freq_per_cpu,
        deterministic=True,
        render=False
    )

    print("🔥 Décollage ! Regarde les FPS s'envoler...")
    model.learn(total_timesteps=3000000, callback=eval_callback)
    model.save("artifacts/noisy_moonlander_ppo/final_model")
    env.close()
    print("✅ Mission terminée ! Modèle sauvegardé dans artifacts/")