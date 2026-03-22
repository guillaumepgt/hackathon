import os
import time
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv, VecNormalize
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.callbacks import EvalCallback

# Import de ton environnement local
from hackathon_rl_envs.Key_DoorMaze import KeyDoorEnv

def make_env(rank):
    def _init():
        env = KeyDoorEnv(seed=int(time.time()) + rank)
        return Monitor(env)
    return _init

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 DÉMARRAGE DE L'ENTRAÎNEMENT KEY-DOOR (18 CŒURS)")
    print("="*60)

    num_cpu = 18

    # 1. Cluster d'entraînement
    env = SubprocVecEnv([make_env(i) for i in range(num_cpu)])
    # On normalise les données
    env = VecNormalize(env, norm_obs=True, norm_reward=True, clip_obs=10.)

    # 2. Environnement d'évaluation (avec la même structure de normalisation)
    eval_env = DummyVecEnv([lambda: Monitor(KeyDoorEnv())])
    eval_env = VecNormalize(eval_env, norm_obs=True, norm_reward=False, clip_obs=10.)
    eval_env.training = False

    # 3. Agent PPO
    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        learning_rate=3e-4,
        n_steps=1024,
        batch_size=256,
        tensorboard_log="./logs_key_door/"
    )

    os.makedirs('./artifacts/key_door_ppo/', exist_ok=True)

    # 4. Évaluateur
    eval_freq_per_cpu = max(10000 // num_cpu, 1)
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path='./artifacts/key_door_ppo/',
        log_path='./logs_key_door/',
        eval_freq=eval_freq_per_cpu,
        deterministic=True,
        render=False
    )

    print("\n🔥 Décollage pour 3 000 000 d'étapes !")
    start_time = time.time()

    model.learn(total_timesteps=3000000, callback=eval_callback)

    # 5. Sauvegarde
    model.save("artifacts/key_door_ppo/final_model")
    env.save("artifacts/key_door_ppo/vec_normalize.pkl")
    env.close()

    elapsed = time.time() - start_time
    print(f"\n✅ Entraînement terminé en {elapsed/60:.1f} minutes !")