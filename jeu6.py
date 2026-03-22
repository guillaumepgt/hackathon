import time
from collections import deque
from players.shared_api_client import GameAPIClient

class PartialVisibilitySpeedrunner:
    def __init__(self, api_client):
        self.api = api_client
        self.game_id = 6
        self.memory_map = {}
        self.frontier = set()
        self.exit_pos = None

    def play_game(self):
        session = self.api.start_game(self.game_id)
        session_id = session["gamesessionid"]
        state = session.get("state") or self.api.get_state(session_id)["state"]

        # Remise à zéro pour la nouvelle partie
        self.memory_map = {}
        self.frontier = set()
        self.exit_pos = None
        pas = 0

        while True:
            curr_pos = tuple(state["player_pos"])

            # 1. On intègre ce qu'on voit à notre mémoire
            self.update_internal_map(state["grid"])

            # 2. On prend la meilleure décision en temps réel
            action = self.get_best_action(curr_pos)

            # Sécurité anti-blocage (si la carte est buggée ou fermée)
            if not action:
                action = "up"

            print(f"  -> Pas {pas:02d} | Pos: {curr_pos} | Cases cartographiées: {len(self.memory_map):03d} | Action: {action.upper()}")

            # 3. On agit
            res = self.api.act(session_id, action)
            status = res.get("status")

            if status != "continue":
                if status == "win":
                    print("🏆 SORTIE TROUVÉE ! Le brouillard est dissipé !")
                else:
                    print(f"💥 FIN ({status})")

                try:
                    self.api.stop_game(session_id, allow_missing=True)
                except:
                    pass
                return status == "win"

            state = res["state"]
            pas += 1

    def update_internal_map(self, visible_grid):
        """Met à jour la mémoire du robot et redéfinit la ligne de front (Frontier)."""
        # 1. Enregistrement des nouvelles cases vues
        for y, row in enumerate(visible_grid):
            for x, char in enumerate(row):
                if char != "?":
                    self.memory_map[(x, y)] = char
                    if char == 'E':
                        self.exit_pos = (x, y)

        # 2. Recalcul propre de la frontière
        self.frontier.clear()
        for pos, char in self.memory_map.items():
            # Une case ne peut être une frontière que si on peut marcher dessus
            if char not in ('#', 'L'):
                x, y = pos
                # Si au moins UN voisin est inconnu, alors cette case borde le brouillard !
                for dx, dy in ((0,1), (0,-1), (1,0), (-1,0)):
                    if (x+dx, y+dy) not in self.memory_map:
                        self.frontier.add(pos)
                        break

    def get_best_action(self, start):
        """L'IA de décision instantanée"""
        # Priorité 1 : Si on connaît la sortie, on fonce dessus
        if self.exit_pos:
            action = self._bfs_search(start, target_pos=self.exit_pos)
            if action:
                return action

        # Priorité 2 : Si on ne la voit pas (ou si elle est bloquée), on explore l'inconnu
        return self._bfs_search(start, target_pos=None)

    def _bfs_search(self, start, target_pos=None):
        """Recherche BFS qui retourne LA PREMIÈRE ACTION à faire pour atteindre la cible"""
        queue = deque([(start, [])])
        visited = {start}

        while queue:
            cur, path = queue.popleft()

            # Si on a trouvé la cible (la sortie, ou une case frontière)
            if target_pos and cur == target_pos:
                return path[0] if path else None
            elif not target_pos and cur in self.frontier:
                return path[0] if path else None

            # Expansion de la recherche
            for action_name, dx, dy in (("up", 0, -1), ("down", 0, 1), ("left", -1, 0), ("right", 1, 0)):
                nb = (cur[0]+dx, cur[1]+dy)

                if nb not in visited:
                    # On ne se déplace que sur des cases CONNUES et PRATICABLES
                    char = self.memory_map.get(nb, '#')
                    if char not in ('#', 'L', '?'):
                        visited.add(nb)
                        queue.append((nb, path + [action_name]))
        return None

if __name__ == "__main__":
    TOKEN = "a729a0ed3b8f5ca37e5b8f95a9fa61d0"
    URL = "https://24hcode2026.plaiades.fr"

    # L'API limite à environ 1 coup / sec, le client gère l'attente tout seul
    client = GameAPIClient(server_url=URL, token=TOKEN, max_calls_per_second=0.9)
    bot = PartialVisibilitySpeedrunner(client)

    partie = 1
    while True:
        try:
            print(f"\n===========================")
            print(f"   BROUILLARD DE GUERRE N°{partie}")
            print(f"===========================")
            bot.play_game()
        except Exception as e:
            print(f"⚠️ Erreur système : {e}")

        partie += 1
        time.sleep(0.5)