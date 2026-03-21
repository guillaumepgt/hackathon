import time
from collections import deque
from players.shared_api_client import GameAPIClient

class KeyDoorSolver:
    def __init__(self, api_client):
        self.api = api_client
        self.game_id = 8

    def play_game(self):
        print("\n🔑 Démarrage du Labyrinthe à Clé (Jeu 8)...")
        session = self.api.start_game(self.game_id)
        session_id = session["gamesessionid"]

        etat_brut = self.api.get_state(session_id)
        state = etat_brut["state"]

        print("🧠 Calcul du chemin optimal...")
        actions = self.solve_bfs(state)

        if not actions:
            print("❌ Impossible de trouver la sortie !")
            self.api.stop_game(session_id)
            return False

        print(f"✅ Chemin trouvé ({len(actions)} pas).")

        for action in actions:
            res = self.api.act(session_id, action)
            if res.get("status") == "win":
                print("🏆 VICTOIRE ! +9 Points !")
                return True
            elif res.get("status") == "lose":
                print("💀 Défaite.")
                self.api.stop_game(session_id)
                return False
        return False

    def solve_bfs(self, state):
        grid = state["grid"]
        # Format API : [x, y]
        start_pos = (state["player_pos"][0], state["player_pos"][1], state["has_key"])

        queue = deque([(start_pos, [])])
        visited = {start_pos}

        moves = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}

        while queue:
            (x, y, has_key), path = queue.popleft()

            # On vérifie si on est sur la case de sortie 'E'
            if grid[y][x] == 'E':
                return path

            for name, (dx, dy) in moves.items():
                nx, ny = x + dx, y + dy

                if 0 <= ny < len(grid) and 0 <= nx < len(grid[0]):
                    cell = grid[ny][nx]

                    if cell == '#': continue # Mur
                    if cell == 'D' and not has_key: continue # Porte fermée

                    n_key = has_key or (cell == 'K')
                    next_state = (nx, ny, n_key)

                    if next_state not in visited:
                        visited.add(next_state)
                        queue.append((next_state, path + [name]))
        return None

if __name__ == "__main__":
    TOKEN = "a729a0ed3b8f5ca37e5b8f95a9fa61d0"
    URL = "https://24hcode2026.plaiades.fr"

    client = GameAPIClient(server_url=URL, token=TOKEN, max_calls_per_second=0.9)
    bot = KeyDoorSolver(client)

    compteur = 1
    while True:
        print(f"\n--- PARTIE {compteur} ---")
        try:
            bot.play_game()
        except Exception as e:
            print(f"Erreur : {e}")
        compteur += 1
        time.sleep(1)