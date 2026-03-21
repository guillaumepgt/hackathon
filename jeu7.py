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

        etat_brut = self.api.get_state(session_id)
        state = etat_brut["state"]

        actions = self.solve_bfs(state)

        if not actions or len(actions) > 7:
            self.api.stop_game(session_id)
            return False

        for action in actions:
            res = self.api.act(session_id, action)
            status = res.get("status")
            if status in ["win", "lose"]:
                print(f"🏁 Fin de partie : {status.upper()} | Pas : {len(actions)}")
                return status == "win"

        return False

    def solve_bfs(self, state):
        grid = state["grid"]
        start_pos = (state["player_pos"][0], state["player_pos"][1])

        queue = deque([(start_pos, "")])
        visited = {start_pos}

        height = len(grid)
        width = len(grid[0])
        moves = [("up", 0, -1), ("down", 0, 1), ("left", -1, 0), ("right", 1, 0)]

        while queue:
            (x, y), path = queue.popleft()

            if grid[y][x] == 'E':
                return path.split(",") if path else []

            for name, dx, dy in moves:
                nx, ny = x + dx, y + dy

                if 0 <= ny < height and 0 <= nx < width:
                    cell = grid[ny][nx]
                    if cell != '#' and cell != 'L' and (nx, ny) not in visited:
                        visited.add((nx, ny))
                        new_path = f"{path},{name}" if path else name
                        queue.append(((nx, ny), new_path))
        return None

if __name__ == "__main__":
    TOKEN = "a729a0ed3b8f5ca37e5b8f95a9fa61d0"
    URL = "https://24hcode2026.plaiades.fr"

    client = GameAPIClient(server_url=URL, token=TOKEN, max_calls_per_second=0.9)
    bot = LavaMazeSolver(client)

    while True:
        try:
            bot.play_game()
        except Exception as e:
            print(f"Erreur : {e}")
        time.sleep(0.1)