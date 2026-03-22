import time
import json
import random
import os
from players.shared_api_client import GameAPIClient

# ==========================================
# PARTIE 1 : L'ENVIRONNEMENT LOCAL (SIMULATEUR)
# ==========================================
class CarRacingLocalEnv:
    def __init__(self):
        self.actions = ["move_left", "move_right", "stay"]
        self.reset()

    def reset(self):
        self.position = 0
        self.lane = 1
        self.done = False
        self.obstacles = []
        # Génère des obstacles aléatoires réalistes (tous les 4 à 8 pas)
        for p in range(5, 110, random.randint(3, 6)):
            self.obstacles.append({'step': p, 'lane': random.randint(0, 2)})
        return self.get_state()

    def get_state(self):
        # Vision limitée à 10 pas (comme l'API)
        visible = [o for o in self.obstacles if 0 <= o['step'] - self.position <= 10]
        return {
            'position': self.position,
            'lane': self.lane,
            'upcoming_obstacles': visible,
            'done': self.done
        }

    def step(self, action):
        if self.done: return self.get_state(), 0, True

        # 1. On applique le mouvement latéral (Changement de voie)
        if action == "move_left" and self.lane > 0:
            self.lane -= 1
        elif action == "move_right" and self.lane < 2:
            self.lane += 1

        # 2. On avance la position (Le temps passe de +1)
        self.position += 1

        # 3. Vérification de la collision à la NOUVELLE position
        # L'IA survit si elle arrive sur une case vide au moment T+1
        reward = 1  # Récompense de base pour chaque pas survécu
        
        for o in self.obstacles:
            # On ne meurt que si l'obstacle est à (nouvelle_pos, nouvelle_lane)
            if o['step'] == self.position and o['lane'] == self.lane:
                self.done = True
                return self.get_state(), -10000, True # Grosse punition pour collision

        # 4. Condition de victoire
        if self.position >= 100:
            self.done = True
            return self.get_state(), 2000, True # Bonus massif pour la ligne d'arrivée

        return self.get_state(), reward, self.done

# ==========================================
# PARTIE 2 : L'AGENT IA (Q-LEARNING)
# ==========================================
class QLearningAgent:
    def __init__(self, actions, learning_rate=0.2, discount_factor=0.95):
        self.q_table = {}
        self.actions = actions
        self.lr = learning_rate
        self.gamma = discount_factor
        self.epsilon = 0.1 # Par défaut pour le jeu (peu d'exploration)

    def get_state_key(self, state):
        lane = state.get('lane', 1)
        pos = state.get('position', 0)
        obs = state.get('upcoming_obstacles', [])
        
        dangers = [8, 8, 8] 
        for o in obs:
            dist = (o['step'] - pos) - 1
            # On inclut 0 ! Si dist = 0, l'obstacle est au même niveau X que nous
            if 0 <= dist <= 8: 
                if dist < dangers[o['lane']]:
                    dangers[o['lane']] = dist
        
        return f"L{lane}_D{dangers[0]}{dangers[1]}{dangers[2]}"

    # def choose_action(self, state_key, train=False):
    #     # Si l'état est inconnu, on initialise des valeurs à 0.0
    #     if state_key not in self.q_table:
    #         self.q_table[state_key] = {a: 0.0 for a in self.actions}
            
    #     if random.random() < self.epsilon:
    #         return random.choice(self.actions)
        
    #     state_qs = self.q_table[state_key]
    #     return max(state_qs, key=state_qs.get)

    def choose_action(self, state_key, train=False):
        if state_key not in self.q_table:
            self.q_table[state_key] = {a: 0.0 for a in self.actions}
            
        # PENDANT L'ENTRAÎNEMENT : On force une exploration plus forte (30%)
        # PENDANT LE JEU : On suit epsilon (1%)
        act_epsilon = 0.3 if train else self.epsilon
        
        if random.random() < act_epsilon:
            return random.choice(self.actions)
        
        state_qs = self.q_table[state_key]
        return max(state_qs, key=state_qs.get)

    def learn(self, state, action, reward, next_state):
        s_key = self.get_state_key(state)
        ns_key = self.get_state_key(next_state)
        
        # Initialisation si état inconnu
        self.q_table.setdefault(s_key, {a: 0.0 for a in self.actions})
        self.q_table.setdefault(ns_key, {a: 0.0 for a in self.actions})

        # Formule de Bellman (Mise à jour de la Q-Table)
        old_value = self.q_table[s_key][action]
        next_max = max(self.q_table[ns_key].values())
        
        new_value = old_value + self.lr * (reward + self.gamma * next_max - old_value)
        self.q_table[s_key][action] = new_value

    def save_brain(self, filename="cerveau_auto.json"):
        with open(filename, "w") as f:
            json.dump(self.q_table, f)
        print(f"💾 Cerveau sauvegardé ({len(self.q_table)} états appris).")

    def load_brain(self, filename="cerveau_auto.json"):
        if os.path.exists(filename):
            with open(filename, "r") as f:
                # CORRECTION : On utilise json.load pour LIRE le fichier
                self.q_table = json.load(f) 
            print(f"🧠 Cerveau chargé ({len(self.q_table)} états connus).")
            self.epsilon = 0.01 # On réduit le hasard pour la compétition
            return True
        return False

# ==========================================
# PARTIE 3 : FONCTIONS D'EXÉCUTION
# ==========================================
def entrainer_ia_local(agent, env, episodes=1000000):
    print(f"\n🏋️‍♂️ Démarrage de l'entraînement flash ({episodes} parties)...")
    start_time = time.time()
    
    for ep in range(episodes):
        state = env.reset()
        while not env.done:
            state_key = agent.get_state_key(state)
            # train=True force l'exploration pour mieux apprendre
            action = agent.choose_action(state_key, train=True)
            next_state, reward, done = env.step(action)
            agent.learn(state, action, reward, next_state)
            state = next_state
            
        #if ep % 2000 == 0:
         #   print(f"   -> Épisode {ep}/{episodes}...")

    print(f"✅ Entraînement terminé en {time.time() - start_time:.1f}s.")
    agent.save_brain()

def jouer_sur_serveur(agent):
    print("\n🏁 Démarrage de la compétition sur le serveur Plaiades...")
    
    # Configuration API
    URL = "https://24hcode2026.plaiades.fr/"
    TOKEN = "a729a0ed3b8f5ca37e5b8f95a9fa61d0"
    GAME_ID = 2 # Car Racing
    
    # On force le rate limit à 0.9 pour être safe
    client = GameAPIClient(URL, TOKEN, max_calls_per_second=0.45)
    
    # Chargement impératif du cerveau entraîné
    if not agent.load_brain():
        print("❌ ERREUR : Aucun cerveau trouvé. Lance l'entraînement d'abord !")
        return

    while True:
        try:
            print("\nConnexion API et création de session...")
            game_info = client.start_game(GAME_ID)
            session_id = game_info['gamesessionid']
            print(f"Partie lancée ! Session ID: {session_id}")

            # Initialisation avant d'entrer dans la boucle des pas
            last_pos = -1
            stuck_count = 0

            for step_num in range(120): # Un peu plus de marge
                # 1. Voir (Récupérer l'état réel)
                data = client.get_state(session_id)
                state = data.get('state', {})
                
                # Vérifier fin de partie
                if state.get('done') or data.get('status') in client.TERMINAL_STATUSES:
                    print(f"🏆 Partie terminée ! Status: {data.get('status')}")
                    break

                current_pos = state.get('position', 0)
                current_lane = state.get('lane', 1)

                # --- GESTION DU BLOCAGE ---
                if current_pos == last_pos:
                    stuck_count += 1
                else:
                    stuck_count = 0
                    last_pos = current_pos

                # 2. Décider (Avec sécurité anti-stuck)
                if stuck_count > 3:
                    print(f"⚠️ BLOQUÉ à la pos {current_pos} ({stuck_count}). Force 'stay'...")
                    action = "stay" 
                    if stuck_count > 10:
                        print("❌ Échec critique. On change de session.")
                        break 
                else:
                    state_key = agent.get_state_key(state)
                    action = agent.choose_action(state_key)

                # Sécurité supplémentaire : Ne pas demander de foncer dans un mur latéral
                if action == "move_left" and current_lane == 0: 
                    action = "stay"
                if action == "move_right" and current_lane == 2: 
                    action = "stay"

                # 3. Agir
                print(f"Pas {step_num} | Pos: {current_pos} | Voie: {current_lane} | Action: {action}")
                client.act(session_id, action)

            # Petite pause entre deux parties
            time.sleep(2)

        except Exception as e:
            print(f"⚠️ Erreur rencontrée : {e}")
            if "429" in str(e):
                print("🚫 Limitation détectée. Pause de 15 secondes...")
                time.sleep(15) # On attend vraiment que la limite expire
            else:
                time.sleep(5)

# ==========================================
# PARTIE 4 : POINT D'ENTRÉE
# ==========================================
if __name__ == "__main__":
    actions_possibles = ["move_left", "move_right", "stay"]
    agent_ia = QLearningAgent(actions_possibles)
    env_local = CarRacingLocalEnv()

    # CHOIX 1 : ENTRAÎNER (À faire une seule fois)
    #entrainer_ia_local(agent_ia, env_local, episodes=1000000)

    # CHOIX 2 : JOUER (Désactive l'entraînement au-dessus)
    jouer_sur_serveur(agent_ia)