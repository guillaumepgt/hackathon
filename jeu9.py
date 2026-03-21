import time
from collections import deque
from players.shared_api_client import GameAPIClient

class MazeSolver:
    def __init__(self, api_client):
        self.api = api_client
        self.game_id = 9  # ID du jeu Lava + Key & Door Maze

    def play_game(self):
        print("\n🧙 Démarrage d'une nouvelle partie de Labyrinthe (Jeu 9)...")
        session = self.api.start_game(self.game_id)
        session_id = session["gamesessionid"]

        etat_brut = self.api.get_state(session_id)
        state = etat_brut["state"]

        print("🧠 Recherche du chemin parfait (BFS) en cours...")
        actions_a_jouer = self.solve_bfs(state)

        if actions_a_jouer is None:
            print("❌ Labyrinthe IMPOSSIBLE ! Arrêt immédiat pour ne pas perdre 1 point.")
            self.api.stop_game(session_id)
            return False

        print(f"✅ Chemin trouvé en {len(actions_a_jouer)} étapes ! Envoi à l'API...")

        for action in actions_a_jouer:
            print(f"  -> Se déplace : {action}")
            resultat = self.api.act(session_id, action)

            status = resultat.get("status")
            if status == "win":
                print("🏆 VICTOIRE ! +10 Points !")
                return True
            elif status == "lose":
                print("💀 Défaite inattendue (Tombé dans la lave ou Timeout)...")
                self.api.stop_game(session_id)
                return False

        print("⚠️ Actions terminées mais pas de victoire confirmée par l'API.")
        self.api.stop_game(session_id)
        return False

    def solve_bfs(self, state):
        grid = state["grid"]
        # Attention aux coordonnées : le JSON donne [colonne(x), ligne(y)]
        start_x, start_y = state["player_pos"][0], state["player_pos"][1]
        start_has_key = state["has_key"]

        # L'état pour le BFS est maintenant : (x, y, as_tu_la_clé)
        start_state = (start_x, start_y, start_has_key)

        queue = deque([(start_state, [])])
        visited = {start_state}

        # Dictionnaire pour mapper les directions
        directions = {
            "up": (0, -1),
            "down": (0, 1),
            "left": (-1, 0),
            "right": (1, 0)
        }

        while queue:
            current_state, path = queue.popleft()
            curr_x, curr_y, has_key = current_state

            # Vérifie si on a atteint la sortie
            if grid[curr_y][curr_x] == 'E':
                return path

            # Teste les 4 mouvements possibles
            for action_name, (dx, dy) in directions.items():
                next_x = curr_x + dx
                next_y = curr_y + dy

                # Vérifie qu'on ne sort pas de la carte (au cas où, bien que les murs '#' bloquent)
                if 0 <= next_y < len(grid) and 0 <= next_x < len(grid[0]):
                    cell = grid[next_y][next_x]

                    # Règle 1 : On ne marche pas dans les murs ni dans la lave
                    if cell == '#' or cell == 'L':
                        continue

                    # Règle 2 : On ne passe pas la porte sans la clé
                    if cell == 'D' and not has_key:
                        continue

                    # Règle 3 : Si on marche sur la clé, on met notre inventaire à jour
                    next_has_key = has_key
                    if cell == 'K':
                        next_has_key = True

                    next_state_tuple = (next_x, next_y, next_has_key)

                    # Si on n'a jamais été sur cette case dans cette condition (avec/sans clé)
                    if next_state_tuple not in visited:
                        visited.add(next_state_tuple)
                        queue.append((next_state_tuple, path + [action_name]))

        return None # Aucun chemin trouvé

if __name__ == "__main__":
    TOKEN = "a729a0ed3b8f5ca37e5b8f95a9fa61d0"
    URL = "https://24hcode2026.plaiades.fr"

    # Toujours garder une petite marge de sécurité pour les appels API
    client = GameAPIClient(server_url=URL, token=TOKEN, max_calls_per_second=0.9)
    bot = MazeSolver(client)

    compteur = 1
    while True:
        print(f"\n--- PARTIE {compteur} ---")
        try:
            bot.play_game()
        except Exception as e:
            print(f"Erreur lors de la partie : {e}")
        compteur += 1
        time.sleep(1)