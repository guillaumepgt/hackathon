import time
from collections import deque
from players.shared_api_client import GameAPIClient

class PartialVisibilitySolver:
    def __init__(self, api_client):
        self.api = api_client
        self.game_id = 6
        self.grid_size = 10
        self.memory_map = [["?" for _ in range(self.grid_size)] for _ in range(self.grid_size)]

    def play_game(self):
        print("\n🔦 Démarrage de l'exploration (Jeu 6)...")
        session = self.api.start_game(self.game_id)
        session_id = session["gamesessionid"]
        self.memory_map = [["?" for _ in range(self.grid_size)] for _ in range(self.grid_size)]

        while True:
            payload = self.api.get_state(session_id)
            state = payload["state"]
            self.update_internal_map(state["grid"])

            curr_pos = (state["player_pos"][0], state["player_pos"][1])
            exit_pos = state.get("exit_pos")

            if exit_pos:
                target = (exit_pos[0], exit_pos[1])
                print(f"🎯 Sortie vue en {target} ! On y va.")
            else:
                target = self.find_nearest_frontier(curr_pos)
                if not target:
                    print("❓ Plus rien à explorer...")
                    break

            path = self.get_path_to_target(curr_pos, target)

            if not path:
                print("🚧 Chemin bloqué, recherche d'une autre zone...")
                self.memory_map[target[1]][target[0]] = "#"
                continue

            action = path[0]
            print(f"  -> Exploration : {action}")
            res = self.api.act(session_id, action)

            if res.get("status") == "win":
                print("🏆 VICTOIRE ! +7 Points !")
                return True
            elif res.get("status") == "lose":
                return False

    def update_internal_map(self, visible_grid):
        """Fusionne ce qu'on voit avec notre carte en mémoire."""
        for y in range(self.grid_size):
            for x in range(self.grid_size):
                char = visible_grid[y][x]
                if char != "?":
                    self.memory_map[y][x] = char

    def find_nearest_frontier(self, start_pos):
        """Trouve la case '?' la plus proche accessible."""
        queue = deque([start_pos])
        visited = {start_pos}

        while queue:
            x, y = queue.popleft()
            if self.memory_map[y][x] == "?":
                return (x, y)

            for dx, dy in [(0,1), (0,-1), (1,0), (-1,0)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.grid_size and 0 <= ny < self.grid_size:
                    if (nx, ny) not in visited and self.memory_map[ny][nx] != "#":
                        visited.add((nx, ny))
                        queue.append((nx, ny))
        return None

    def get_path_to_target(self, start, target):
        """BFS classique pour aller d'un point A à un point B sur la carte connue."""
        queue = deque([(start, [])])
        visited = {start}
        moves = {"up": (0,-1), "down": (0,1), "left": (-1,0), "right": (1,0)}

        while queue:
            (x, y), path = queue.popleft()
            if (x, y) == target: return path

            for name, (dx, dy) in moves.items():
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.grid_size and 0 <= ny < self.grid_size:
                    cell = self.memory_map[ny][nx]
                    if (nx, ny) == target or cell in [".", "S", "E"]:
                        if (nx, ny) not in visited:
                            visited.add((nx, ny))
                            queue.append(((nx, ny), path + [name]))
        return None

if __name__ == "__main__":
    TOKEN = "a729a0ed3b8f5ca37e5b8f95a9fa61d0"
    URL = "https://24hcode2026.plaiades.fr"
    client = GameAPIClient(server_url=URL, token=TOKEN, max_calls_per_second=0.9)
    bot = PartialVisibilitySolver(client)
    while True:
        try: bot.play_game()
        except Exception as e: print(f"Erreur : {e}")
        time.sleep(1)