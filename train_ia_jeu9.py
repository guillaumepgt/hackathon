import time
from collections import deque
from players.shared_api_client import GameAPIClient

class UltimateMazeSolver:
    def __init__(self, api_client):
        self.api = api_client
        self.game_id = 9

    def play_game(self):
        session = self.api.start_game(self.game_id)
        session_id = session["gamesessionid"]
        state = session.get("state") or self.api.get_state(session_id)["state"]

        actions = self.solve_bfs(state)

        if not actions:
            print("❌ Aucun chemin possible (Bloqué !)")
            try: self.api.stop_game(session_id)
            except: pass
            return False

        for action in actions:
            res = self.api.act(session_id, action)
            status = res.get("status")
            if status in ["win", "lose"]:
                print(f"🏁 Fin de partie : {status.upper()} | Mouvements : {len(actions)}")
                return status == "win"

        return False

    def solve_bfs(self, state):
        grid = state["grid"]
        start_pos = (state["player_pos"][0], state["player_pos"][1])
        start_has_key = state.get("has_key", False)

        queue = deque([(start_pos, start_has_key, "")])
        visited = {(start_pos[0], start_pos[1], start_has_key)}

        height = len(grid)
        moves = [("up", 0, -1), ("down", 0, 1), ("left", -1, 0), ("right", 1, 0)]

        while queue:
            (x, y), has_key, path = queue.popleft()

            if grid[y][x] == 'E':
                return path.split(",") if path else []

            for name, dx, dy in moves:
                nx, ny = x + dx, y + dy

                if 0 <= ny < height and 0 <= nx < len(grid[ny]):
                    cell = grid[ny][nx]

                    if cell in ['#', 'L']: continue
                    if cell == 'D' and not has_key: continue

                    new_has_key = has_key or (cell == 'K')
                    state_id = (nx, ny, new_has_key)

                    if state_id not in visited:
                        visited.add(state_id)
                        new_path = f"{path},{name}" if path else name
                        queue.append(((nx, ny), new_has_key, new_path))

        return None

if __name__ == "__main__":
    TOKEN = "a729a0ed3b8f5ca37e5b8f95a9fa61d0"
    URL = "https://24hcode2026.plaiades.fr"

    client = GameAPIClient(server_url=URL, token=TOKEN, max_calls_per_second=0.95)
    bot = UltimateMazeSolver(client)

    partie = 1
    while True:
        try:
            print(f"\n--- Infiltration Finale N°{partie} ---")
            bot.play_game()
        except Exception as e:
            print(f"Erreur : {e}")

        partie += 1
        time.sleep(0.5)