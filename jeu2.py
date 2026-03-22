import time
from players.shared_api_client import GameAPIClient

# Configuration
SERVER_URL = "https://24hcode2026.plaiades.fr/"
TOKEN = "a729a0ed3b8f5ca37e5b8f95a9fa61d0"

# On passe à 0.8 pour être ultra safe sur le quota de requêtes
client = GameAPIClient(SERVER_URL, TOKEN, max_calls_per_second=0.8)

game_id = 2

def get_action_reflex(state):
    """Analyse l'état actuel et renvoie UNE SEULE action"""
    pos = state.get('position', 0)
    lane = state.get('lane', 1)
    obstacles = state.get('upcoming_obstacles', [])

    # On repère le danger sur chaque voie (5 = pas de danger)
    danger = [5, 5, 5]
    for obs in obstacles:
        dist = obs['step'] - pos
        if 0 <= dist <= 5:
            if dist < danger[obs['lane']]:
                danger[obs['lane']] = dist

    if danger[lane] == 1: # Si obstacle imminent sur ma voie
        print(f"Danger détecté ! Voie 0: {danger[0]}, Voie 1: {danger[1]}, Voie 2: {danger[2]}")
        
        if lane == 1 and danger[0] == 0 and danger[2] == 0: # On est au milieu
            client.stop_game(session_id)
        elif lane == 0 and danger[1] == 0: # On est à gauche
            client.stop_game(session_id)
        elif lane == 2 and danger[1] == 0: # On est à droite
            client.stop_game(session_id)

    # LOGIQUE DE DÉCISION
    if danger[lane] <= 2: # Si obstacle imminent sur ma voie
        print(f"Danger détecté ! Voie 0: {danger[0]}, Voie 1: {danger[1]}, Voie 2: {danger[2]}")
        
        if lane == 1: # On est au milieu
            if danger[0] == 0 and danger[2] == 0:
                client.stop_game(session_id)
            return "move_left" if danger[0] >= danger[2] else "move_right"
        elif lane == 0: # On est à gauche
            if danger[1] == 0:
                client.stop_game(session_id)
            return "move_right"
        else: # On est à droite
            if danger[1] == 0:
                client.stop_game(session_id)
            return "move_left"
            
    return "stay"

# --- Lancement ---
while True:
    try:
        game_info = client.start_game(game_id)
        session_id = game_info['gamesessionid']

        print(f"Course lancée ! Session: {session_id}")

        # Boucle de jeu réelle
        for i in range(105): # Un peu plus de 100 pour être sûr d'arriver
            # 1. ACTUALISER la vision à chaque pas
            data = client.get_state(session_id)
            state = data.get('state', {})
            
            if state.get('done') or data.get('status') in client.TERMINAL_STATUSES:
                print(f"Terminé ! Status: {data.get('status')}")
                break

            # 2. DECIDER selon la vue actuelle
            action = get_action_reflex(state)
            
            # 3. AGIR
            print(f"Pos: {state.get('position')} | Voie: {state.get('lane')} | Action: {action}")
            client.act(session_id, action)

        time.sleep(0.8)

    except Exception as e:
        print(f"Erreur : {e}")