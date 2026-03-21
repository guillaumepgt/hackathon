import time
from collections import deque
from players.shared_api_client import GameAPIClient

class RushHourSolver:
    def __init__(self, api_client):
        self.api = api_client
        self.game_id = 4
        self.grid_size = 6

    def play_game(self):
        print("\n🚗 Démarrage d'une nouvelle partie de Rush Hour...")
        session = self.api.start_game(self.game_id)
        session_id = session["gamesessionid"]

        etat_brut = self.api.get_state(session_id)

        print("🧠 Recherche de la solution (BFS) en cours...")
        actions_a_jouer = self.solve_bfs(etat_brut["state"])

        if actions_a_jouer is None:
            print("❌ Grille IMPOSSIBLE ! Arrêt immédiat.")
            self.api.stop_game(session_id)
            return False

        print(f"✅ Solution trouvée en {len(actions_a_jouer)} coups ! Envoi à l'API...")

        if len(actions_a_jouer) == 0:
            print("🏆 Grille déjà résolue.")
            self.api.stop_game(session_id)
            return True

        for action in actions_a_jouer:
            print(f"  -> Joue : {action}")
            resultat = self.api.act(session_id, action)

            status = resultat.get("status")
            if status == "win":
                print("🏆 VICTOIRE ! +4 Points !")
                return True
            elif status == "lose":
                print("💀 Défaite inattendue...")
                self.api.stop_game(session_id)
                return False

        print("⚠️ Actions terminées mais pas de victoire confirmée par l'API.")
        self.api.stop_game(session_id)
        return False

    def solve_bfs(self, initial_state):
        start_state = self.parse_state(initial_state)

        queue = deque([(start_state, [])])
        visited = {start_state}

        while queue:
            current_state, path = queue.popleft()

            if self.is_winning(current_state):
                return path

            for action, next_state in self.get_possible_moves(current_state):
                if next_state not in visited:
                    visited.add(next_state)
                    queue.append((next_state, path + [action]))

        return None

    def parse_state(self, state_json):
        vehicules = []
        for v in state_json.get("vehicles", []):
            vehicules.append((
                v["id"],
                v["pos"][0],
                v["pos"][1],
                v["orientation"],
                v["length"]
            ))
        return tuple(sorted(vehicules))

    def is_winning(self, state):
        for v in state:
            v_id, row, col, orientation, length = v
            if v_id == 'X' and col + length - 1 >= self.grid_size:
                return True
        return False

    def get_possible_moves(self, state):
        moves = []

        grid = [[False for _ in range(self.grid_size)] for _ in range(self.grid_size)]

        for v in state:
            v_id, row, col, orientation, length = v
            for i in range(length):
                if orientation == 'h':
                    grid[row][col + i] = True
                else:
                    grid[row + i][col] = True

        for i, v in enumerate(state):
            v_id, row, col, orientation, length = v
            state_list = list(state)

            if orientation == 'h':
                if col > 0 and not grid[row][col - 1]:
                    new_v = (v_id, row, col - 1, orientation, length)
                    state_list[i] = new_v
                    moves.append((f"move_{v_id}_left", tuple(sorted(state_list))))

                if col + length < self.grid_size and not grid[row][col + length]:
                    new_v = (v_id, row, col + 1, orientation, length)
                    state_list[i] = new_v
                    moves.append((f"move_{v_id}_right", tuple(sorted(state_list))))

                elif v_id == 'X' and col + length == self.grid_size:
                    new_v = (v_id, row, col + 1, orientation, length)
                    state_list[i] = new_v
                    moves.append((f"move_{v_id}_right", tuple(sorted(state_list))))

            elif orientation == 'v':
                if row > 0 and not grid[row - 1][col]:
                    new_v = (v_id, row - 1, col, orientation, length)
                    state_list[i] = new_v
                    moves.append((f"move_{v_id}_up", tuple(sorted(state_list))))

                if row + length < self.grid_size and not grid[row + length][col]:
                    new_v = (v_id, row + 1, col, orientation, length)
                    state_list[i] = new_v
                    moves.append((f"move_{v_id}_down", tuple(sorted(state_list))))

        return moves

if __name__ == "__main__":
    TOKEN = "a729a0ed3b8f5ca37e5b8f95a9fa61d0"
    URL = "https://24hcode2026.plaiades.fr"

    client = GameAPIClient(server_url=URL, token=TOKEN, max_calls_per_second=0.9)
    bot = RushHourSolver(client)

    compteur = 1
    while True:
        print(f"\n--- PARTIE {compteur} ---")
        try:
            bot.play_game()
        except Exception as e:
            print(f"Erreur lors de la partie : {e}")
        compteur += 1
        time.sleep(1)