import os
import time
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.callbacks import EvalCallback

# Import de ton environnement Rush Hour
from hackathon_rl_envs.rushhour import RushHourEnv

def make_env(rank):
    def _init():
        # Chaque CPU reçoit un "seed" différent pour générer des puzzles uniques
        env = RushHourEnv(seed=int(time.time()) + rank)
        return Monitor(env)
    return _init

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 DÉMARRAGE DU MOTEUR RUSH HOUR (MODE 18 CŒURS)")
    print("="*60)

    num_cpu = 18
    print(f"Création de {num_cpu} environnements parallèles (Asynchrone)...")

    # 1. Création du cluster (18 instances du jeu en simultané)
    env = SubprocVecEnv([make_env(i) for i in range(num_cpu)])

    # 2. Environnement d'évaluation (Tourne sur 1 seul cœur pour tester proprement)
    eval_env = DummyVecEnv([lambda: Monitor(RushHourEnv(seed=42))])

    # 3. Configuration de PPO
    # L'architecture [256, 256] est idéale pour comprendre une grille 6x6 complexe
    policy_kwargs = dict(net_arch=[256, 256])

    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        learning_rate=3e-4,
        n_steps=1024,      # On récolte beaucoup de données avant de mettre à jour le cerveau
        batch_size=256,    # Bonne taille de lot pour lisser l'apprentissage
        ent_coef=0.01,     # On force l'IA à explorer un peu au début
        policy_kwargs=policy_kwargs,
        tensorboard_log="./logs_rush_hour/"
    )

    # Création des dossiers pour sauvegarder le champion
    os.makedirs('./artifacts/rush_hour_ppo/', exist_ok=True)

    # 4. Callback pour sauvegarder le MEILLEUR modèle automatiquement
    # eval_freq est divisé par 18 car chaque "step" fait avancer les 18 environnements d'un coup
    eval_freq_per_cpu = max(10000 // num_cpu, 1)

    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path='./artifacts/rush_hour_ppo/',
        log_path='./logs_rush_hour/',
        eval_freq=eval_freq_per_cpu,
        deterministic=True,
        render=False
    )

    print("\n🔥 Décollage pour 3 000 000 d'étapes ! (Environ 10-15 min sur 18 cœurs)")
    start_time = time.time()

    try:
        # 5. L'entraînement massif
        model.learn(total_timesteps=3000000, callback=eval_callback)
    except KeyboardInterrupt:
        print("\n🛑 Interruption manuelle. Sauvegarde d'urgence en cours...")

    # 6. Sauvegarde finale et fermeture propre
    model.save("artifacts/rush_hour_ppo/final_model")
    env.close()

    elapsed = time.time() - start_time
    print(f"\n✅ Entraînement terminé en {elapsed/60:.1f} minutes !")
    print("📁 Le meilleur modèle est dans : artifacts/rush_hour_ppo/best_model.zip")