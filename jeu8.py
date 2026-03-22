import time
import heapq
from players.shared_api_client import GameAPIClient

class KeyDoorSolver:
    def __init__(self, api_client):
        self.api = api_client
        self.game_id = 8

    def play_game(self):
        session = self.api.start_game(self.game_id)
        session_id = session["gamesessionid"]
        state = session.get("state") or self.api.get_state(session_id)["state"]

        actions = self.solve_astar(state)
        if not actions:
            self.api.stop_game(session_id)
            return False

        for action in actions:
            res = self.api.act(session_id, action)
            status = res.get("status")
            if status == "win": return True
            if status == "lose":
                self.api.stop_game(session_id)
                return False
        return False

    def solve_astar(self, state):
        grid = state["grid"]
        rows, cols = len(grid), len(grid[0])
        sx, sy = state["player_pos"]

        key_pos = exit_pos = None
        for y, row in enumerate(grid):
            for x, cell in enumerate(row):
                if cell == 'K': key_pos = (x, y)
                if cell == 'E': exit_pos = (x, y)

        if not exit_pos:
            return None

        def heuristic(x, y, has_key):
            if not has_key and key_pos:
                return (abs(x - key_pos[0]) + abs(y - key_pos[1]) +
                        abs(key_pos[0] - exit_pos[0]) + abs(key_pos[1] - exit_pos[1]))
            return abs(x - exit_pos[0]) + abs(y - exit_pos[1])

        start = (sx, sy, state["has_key"])
        heap = [(heuristic(sx, sy, state["has_key"]), 0, start)]
        parent = {start: None}
        g_score = {start: 0}
        moves = [("up", 0, -1), ("down", 0, 1), ("left", -1, 0), ("right", 1, 0)]

        while heap:
            f, g, (x, y, has_key) = heapq.heappop(heap)

            if grid[y][x] == 'E':
                path = []
                cur = (x, y, has_key)
                while parent[cur] is not None:
                    prev, action = parent[cur]
                    path.append(action)
                    cur = prev
                path.reverse()
                return path

            if g > g_score.get((x, y, has_key), float('inf')):
                continue

            for name, dx, dy in moves:
                nx, ny = x + dx, y + dy
                if 0 <= ny < rows and 0 <= nx < cols:
                    cell = grid[ny][nx]
                    if cell == '#' or (cell == 'D' and not has_key):
                        continue
                    nk = has_key or (cell == 'K')
                    ns = (nx, ny, nk)
                    ng = g + 1
                    if ng < g_score.get(ns, float('inf')):
                        g_score[ns] = ng
                        parent[ns] = ((x, y, has_key), name)
                        heapq.heappush(heap, (ng + heuristic(nx, ny, nk), ng, ns))
        return None

if __name__ == "__main__":
    TOKEN = "a729a0ed3b8f5ca37e5b8f95a9fa61d0"
    URL = "https://24hcode2026.plaiades.fr"

    client = GameAPIClient(server_url=URL, token=TOKEN, max_calls_per_second=0.85)
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