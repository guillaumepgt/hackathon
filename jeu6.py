from collections import deque
from players.shared_api_client import GameAPIClient
import time

class PartialVisibilitySpeedrunner:
    def __init__(self, api_client):
        self.api = api_client
        self.game_id = 6
        self.memory_map = {}

    def play_game(self):
        print("\nMode Speedrun activé (Jeu 6)...")
        session = self.api.start_game(self.game_id)
        session_id = session["gamesessionid"]

        res = self.api.get_state(session_id)
        state = res["state"]
        self.memory_map = {}
        cached_path = []

        while True:
            curr_pos = tuple(state["player_pos"])
            self.update_internal_map(state["grid"], curr_pos)

            exit_pos = state.get("exit_pos")
            if exit_pos:
                target = tuple(exit_pos)
                cached_path = self.get_path_to_target(curr_pos, target) or []
            elif not cached_path:
                target = self.find_nearest_frontier(curr_pos)
                if not target:
                    break
                cached_path = self.get_path_to_target(curr_pos, target) or []
                if not cached_path:
                    self.memory_map[target] = "#"
                    continue

            if not cached_path:
                continue

            action = cached_path.pop(0)
            res = self.api.act(session_id, action)

            status = res.get("status")
            if status in ["win", "lose"]:
                print(f"Fin : {status.upper()}")
                return status == "win"

            state = res["state"]
            new_pos = tuple(state["player_pos"])

            if new_pos == curr_pos:
                cached_path = []

    def update_internal_map(self, visible_grid, player_pos):
        for y, row in enumerate(visible_grid):
            for x, char in enumerate(row):
                if char != "?":
                    self.memory_map[(x, y)] = char

    def find_nearest_frontier(self, start_pos):
        queue = deque([start_pos])
        visited = {start_pos}
        while queue:
            x, y = queue.popleft()
            for dx, dy in [(0,1),(0,-1),(1,0),(-1,0)]:
                nx, ny = x+dx, y+dy
                if (nx, ny) not in self.memory_map:
                    return (x, y)
                if (nx, ny) not in visited and self.memory_map[(nx,ny)] != "#":
                    visited.add((nx, ny))
                    queue.append((nx, ny))
        return None

    def get_path_to_target(self, start, target):
        if start == target: return []
        queue = deque([(start, [])])
        visited = {start}
        moves = [("up",0,-1),("down",0,1),("left",-1,0),("right",1,0)]
        while queue:
            (x, y), path = queue.popleft()
            if (x, y) == target: return path
            for name, dx, dy in moves:
                nx, ny = x+dx, y+dy
                if (nx,ny) not in visited and self.memory_map.get((nx,ny), "#") != "#":
                    visited.add((nx, ny))
                    queue.append(((nx,ny), path+[name]))
        return None

if __name__ == "__main__":
    TOKEN = "a729a0ed3b8f5ca37e5b8f95a9fa61d0"
    URL = "https://24hcode2026.plaiades.fr"

    client = GameAPIClient(server_url=URL, token=TOKEN, max_calls_per_second=0.85)
    bot = PartialVisibilitySpeedrunner(client)

    while True:
        try:
            bot.play_game()
        except Exception as e:
            print(f"Erreur : {e}")
        time.sleep(0.1)