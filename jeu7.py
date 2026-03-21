import time
from collections import deque
from players.shared_api_client import GameAPIClient

class LavaMazeSolver:
    def __init__(self, api_client):
        self.api = api_client
        self.game_id = 7

    def play_game(self):
        session = self.api.start_game(self.game_id)
        session_id = session["gamesessionid"]

        time.sleep(0.8)
        etat_brut = self.api.get_state(session_id)
        state = etat_brut["state"]

        print("🧠 Calcul du chemin sécurisé...")
        actions = self.solve_bfs(state)

        if not actions:
            print("❌ Aucun chemin sûr trouvé (bloqué par la lave) !")
            time.sleep(0.8)
            self.api.stop_game(session_id)
            return False

        print(f"✅ Chemin trouvé ({len(actions)} pas).")

        for action in actions:
            time.sleep(1)
            res = self.api.act(session_id, action)
            status = res.get("status")
            if status == "win":
                print("🏆 VICTOIRE ! +8 Points !")
                return True
            elif status == "lose":
                print("perdu")
                self.api.stop_game(session_id)
                return False
        return False

    def solve_bfs(self, state):
        grid = state["grid"]
        start_pos = (state["player_pos"][0], state["player_pos"][1])

        queue = deque([(start_pos, [])])
        visited = {start_pos}

        moves = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}

        while queue:
            (x, y), path = queue.popleft()
            if grid[y][x] == 'E':
                return path
            for name, (dx, dy) in moves.items():
                nx, ny = x + dx, y + dy
                if 0 <= ny < len(grid) and 0 <= nx < len(grid[0]):
                    cell = grid[ny][nx]
                    if cell == '#' or cell == 'L':
                        continue
                    next_state = (nx, ny)
                    if next_state not in visited:
                        visited.add(next_state)
                        queue.append((next_state, path + [name]))
        return None

if __name__ == "__main__":
    TOKEN = "a729a0ed3b8f5ca37e5b8f95a9fa61d0"
    URL = "https://24hcode2026.plaiades.fr"

    client = GameAPIClient(server_url=URL, token=TOKEN)
    bot = LavaMazeSolver(client)

    compteur = 1
    while True:
        print(f"\n--- PARTIE {compteur} ---")
        try:
            bot.play_game()
        except Exception as e:
            print(f"Erreur : {e}")
        compteur += 1
        time.sleep(1)