import time
from collections import deque
from players.shared_api_client import GameAPIClient

class SnakeBot:
    def __init__(self, api_client):
        self.api = api_client
        self.game_id = 3
        self.grid_size = 20
        self.last_head = None
        self.current_direction = None

    def play_game(self):
        print("\n🐍 Lancement du serpent (Mode Anti-Collision)...")
        start = self.api.start_game(self.game_id)
        session_id = start["gamesessionid"]

        # Réinitialisation de la mémoire pour chaque nouvelle partie
        self.last_head = None
        self.current_direction = None

        while True:
            payload = self.api.get_state(session_id)
            state = payload["state"]

            if state.get("done"):
                break

            snake = state["snake"]
            food = tuple(state["food"])
            head = tuple(snake[0])
            body = set(tuple(s) for s in snake)

            # --- DÉDUCTION DE LA DIRECTION ACTUELLE ---
            if len(snake) > 1:
                neck = tuple(snake[1])
                dx = head[0] - neck[0]
                dy = head[1] - neck[1]
            elif self.last_head:
                dx = head[0] - self.last_head[0]
                dy = head[1] - self.last_head[1]
            else:
                dx, dy = 0, 0
                self.current_direction = state.get("direction")

            if dx != 0 or dy != 0:
                if dx == 0 and dy == -1: self.current_direction = "up"
                elif dx == 0 and dy == 1: self.current_direction = "down"
                elif dx == -1 and dy == 0: self.current_direction = "left"
                elif dx == 1 and dy == 0: self.current_direction = "right"

            self.last_head = head

            # --- CALCUL DU MEILLEUR COUP ---
            action = self.get_best_action(head, food, body, self.current_direction)

            result = self.api.act(session_id, action)

            if result["status"] != "continue":
                print(f"🏁 Fin de partie : {result['status']} | Score: {result.get('score', state.get('score'))}")
                self.api.stop_game(session_id, allow_missing=True)
                break

    def get_best_action(self, head, target, body, current_dir):
        directions = {
            "up": (0, -1),
            "down": (0, 1),
            "left": (-1, 0),
            "right": (1, 0)
        }

        # On définit le mouvement interdit (le demi-tour)
        opposites = {"up": "down", "down": "up", "left": "right", "right": "left"}
        forbidden_action = opposites.get(current_dir)

        # 1. RECHERCHE DU CHEMIN (BFS)
        queue = deque([(head, [])])
        visited = {head}

        while queue:
            current_pos, path = queue.popleft()

            if current_pos == target:
                return path[0]

            for action_name, (dx, dy) in directions.items():
                # Interdiction absolue de faire demi-tour au tout premier pas
                if len(path) == 0 and action_name == forbidden_action:
                    continue

                nx, ny = current_pos[0] + dx, current_pos[1] + dy
                neighbor = (nx, ny)

                if 0 <= nx < self.grid_size and 0 <= ny < self.grid_size:
                    if neighbor not in body and neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, path + [action_name]))

        # 2. SURVIE (Si la pomme est bloquée)
        for action_name, (dx, dy) in directions.items():
            if action_name == forbidden_action:
                continue
            nx, ny = head[0] + dx, head[1] + dy
            neighbor = (nx, ny)
            if 0 <= nx < self.grid_size and 0 <= ny < self.grid_size:
                if neighbor not in body:
                    return action_name

        # 3. COUP DE LA FIN (Si on est totalement encerclé)
        valid_moves = [a for a in directions.keys() if a != forbidden_action]
        return valid_moves[0] if valid_moves else "up"

if __name__ == "__main__":
    TOKEN = "a729a0ed3b8f5ca37e5b8f95a9fa61d0"
    URL = "https://24hcode2026.plaiades.fr"

    client = GameAPIClient(URL, TOKEN, max_calls_per_second=0.95)
    bot = SnakeBot(client)

    partie = 1
    while True:
        print(f"\n--- SERPENT N°{partie} ---")
        try:
            bot.play_game()
        except Exception as e:
            print(f"⚠️ Erreur : {e}")
            time.sleep(2)
        partie += 1
        time.sleep(1)