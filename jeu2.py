import time
from collections import deque
from players.shared_api_client import GameAPIClient

class CarRacingAutopilot:
    def __init__(self, api_client):
        self.api = api_client
        self.game_id = 2

    def get_best_action(self, state):
        current_pos = state["position"]
        current_lane = state["lane"]
        obstacles = state.get("upcoming_obstacles", [])

        # 1. On transforme la liste des obstacles en un dictionnaire ultra-rapide
        # {(step, lane): True}
        danger_zone = {(obs["step"], obs["lane"]) for obs in obstacles}

        # S'il n'y a aucun obstacle en vue, on reste au milieu (voie 1) par sécurité
        if not danger_zone:
            if current_lane == 0: return "move_right"
            if current_lane == 2: return "move_left"
            return "stay"

        # 2. Le Radar (BFS) : On calcule tous les futurs possibles
        # File d'attente : (position_simulée, voie_simulée, historique_des_actions)
        queue = deque([(current_pos, current_lane, [])])

        best_path = []
        max_survival_pos = current_pos

        while queue:
            p, l, path = queue.popleft()

            # On garde en mémoire le chemin qui va le plus loin possible
            if p > max_survival_pos:
                max_survival_pos = p
                best_path = path

            # Si on a réussi à simuler 10 pas en avant sans mourir, c'est un chemin parfait !
            if p - current_pos >= 10:
                return path[0] if path else "stay"

            # 3. On simule les 3 actions possibles pour le pas suivant
            next_p = p + 1
            moves = [
                ("move_left", l - 1),
                ("stay", l),
                ("move_right", l + 1)
            ]

            for action, next_l in moves:
                # Vérification : Est-ce qu'on reste sur la route (voie 0, 1 ou 2) ?
                if 0 <= next_l <= 2:
                    # Vérification : Est-ce qu'il y a un obstacle sur cette case ?
                    if (next_p, next_l) not in danger_zone:
                        queue.append((next_p, next_l, path + [action]))

        # 4. Si la boucle se termine sans trouver un chemin de 10 pas,
        # on prend au moins l'action du chemin qui nous fait survivre le plus longtemps.
        if best_path:
            return best_path[0]
        else:
            return "stay" # Crash inévitable

    def play_game(self):
        print("\n🏎️ Départ de la course (Jeu 2)...")
        session = self.api.start_game(self.game_id)
        session_id = session["gamesessionid"]

        state = session.get("state") or self.api.get_state(session_id)["state"]

        while True:
            # 1. L'algorithme analyse l'avenir et choisit la meilleure action
            action = self.get_best_action(state)

            print(f"  -> Pos: {state['position']:03d}/100 | Voie: {state['lane']} | Action: {action.upper()}")

            # 2. On envoie l'action au serveur
            result = self.api.act(session_id, action)
            status = result.get("status")

            # 3. Fin de la partie ?
            if status != "continue":
                if status == "win":
                    print("🏆 ARRIVÉE FRANCHIE ! +2 Points")
                else:
                    print(f"💥 CRASH ! Défaite ({status})")

                try:
                    self.api.stop_game(session_id, allow_missing=True)
                except:
                    pass
                return

            state = result["state"]

if __name__ == "__main__":
    TOKEN = "a729a0ed3b8f5ca37e5b8f95a9fa61d0"
    URL = "https://24hcode2026.plaiades.fr"

    # L'API est limitée. Un appel toutes les 0.95s max pour être tranquille.
    client = GameAPIClient(server_url=URL, token=TOKEN, max_calls_per_second=0.95)
    bot = CarRacingAutopilot(client)

    course = 1
    while True:
        print(f"\n===========================")
        print(f"   GRAND PRIX N°{course}")
        print(f"===========================")
        try:
            bot.play_game()
        except Exception as e:
            print(f"⚠️ Erreur serveur : {e}")
            time.sleep(2)

        course += 1
        time.sleep(0.5) # Petite pause avant de relancer