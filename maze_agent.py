import time
from collections import deque
from players.shared_api_client import GameAPIClient

# ==========================================
# PARTIE 1 : L'AGENT EXPLORATEUR
# ==========================================
class FrontierAgent:
    def __init__(self):
        self.memory_map = {}
        self.confirmed_walls = set()  # Murs confirmés par collision réelle (indestructibles)
        self.blacklist = set()        # Cibles inaccessibles
        self.actions = ["up", "down", "left", "right"]

    def reset_memory(self):
        self.memory_map = {}
        self.confirmed_walls = set()
        self.blacklist = set()

    def update_map(self, visible_grid, player_pos):
        px, py = player_pos
        for y_rel, row in enumerate(visible_grid):
            for x_rel, cell in enumerate(row):
                gx, gy = px + (x_rel - 2), py + (y_rel - 2)

                # Règle d'or : un mur confirmé par collision est sacré,
                # le serveur ne peut pas l'effacer
                if (gx, gy) in self.confirmed_walls:
                    self.memory_map[(gx, gy)] = '#'
                    continue

                if cell != '?':
                    self.memory_map[(gx, gy)] = cell

    def find_nearest_frontier(self, start_pos):
        """BFS qui cherche la case traversable la plus proche
        adjacente à une zone inconnue, en ignorant murs et blacklist."""
        queue = deque([start_pos])
        visited = {start_pos}

        while queue:
            curr = queue.popleft()
            x, y = curr

            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                neighbor = (x + dx, y + dy)

                # Si le voisin est inconnu, curr est une frontière valide
                if neighbor not in self.memory_map:
                    if self.memory_map.get(curr) != '#' and curr not in self.blacklist:
                        return curr

                # Propagation BFS uniquement sur cases connues et marchables
                if neighbor in self.memory_map and neighbor not in visited:
                    if self.memory_map[neighbor] != '#':
                        visited.add(neighbor)
                        queue.append(neighbor)

        return None

    def get_path(self, start, target):
        """BFS qui retourne la liste d'actions pour aller de start à target."""
        if start == target:
            return []
        queue = deque([(start, [])])
        visited = {start}
        directions = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}

        while queue:
            (x, y), path = queue.popleft()
            if (x, y) == target:
                return path
            for move, (dx, dy) in directions.items():
                nx, ny = x + dx, y + dy
                if (
                    (nx, ny) in self.memory_map
                    and self.memory_map[(nx, ny)] != '#'
                    and (nx, ny) not in visited
                ):
                    visited.add((nx, ny))
                    queue.append(((nx, ny), path + [move]))

        return None  # Aucun chemin trouvé


# ==========================================
# PARTIE 2 : BOUCLE DE JEU
# ==========================================
def jouer_labyrinthe(client, agent):
    GAME_ID = 6
    try:
        session = client.start_game(GAME_ID)
        session_id = session.get("gamesessionid")
        if not session_id:
            print("⚠️ Impossible d'obtenir un Session ID.")
            return False

        agent.reset_memory()
        print(f"🚀 Session {session_id} démarrée. Exploration...")

        # Variables de contrôle initialisées avant la boucle
        last_pos = None
        last_action = "up"  # Valeur par défaut pour le premier tour
        target = None

        while True:
            # 1. Obtenir l'état du serveur
            res = client.get_state(session_id)
            if not res or "state" not in res:
                print("⏳ Réponse vide, attente...")
                time.sleep(1)
                continue

            state = res["state"]
            curr_pos = tuple(state["player_pos"])

            # 2. Détection de collision réelle
            # Si la position n'a pas changé après une action, il y a un mur
            if last_pos is not None and last_pos == curr_pos:
                directions = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
                dx, dy = directions[last_action]
                wall_pos = (curr_pos[0] + dx, curr_pos[1] + dy)
                print(f"💥 Collision RÉELLE en {wall_pos}! Verrouillage MUR.")

                # Enregistrement dans confirmed_walls ET memory_map
                agent.confirmed_walls.add(wall_pos)
                agent.memory_map[wall_pos] = '#'

                # Forcer le recalcul de la cible et reprendre la boucle
                target = None
                last_pos = None  # Reset pour éviter de reboucler sur le même choc
                continue

            last_pos = curr_pos
            agent.update_map(state["grid"], curr_pos)

            # 3. Choisir la cible : sortie visible en priorité, sinon frontière
            if state.get("exit_pos"):
                target = tuple(state["exit_pos"])
            else:
                target = agent.find_nearest_frontier(curr_pos)

            if not target:
                print("🏁 Zone totalement explorée ou bloquée. Reset de la session...")
                break

            # 4. Calculer le chemin vers la cible
            path = agent.get_path(curr_pos, target)

            if path is None or len(path) == 0:
                print(f"🚫 Cible {target} inatteignable. Blacklistée.")
                agent.memory_map[target] = '#'
                agent.blacklist.add(target)
                target = None
                continue

            # 5. Exécuter la première action du chemin
            action = path[0]
            last_action = action  # Mémorisé pour la détection de collision au prochain tour

            print(f"📍 {curr_pos} -> {action} (Cible: {target})")
            res_act = client.act(session_id, action)

            # 6. Vérifier la fin de partie
            status = res_act.get("status")
            if status in ["win", "lose"]:
                print(f"🎉 FIN DE PARTIE : {status.upper()}")
                return status == "win"

    except Exception as e:
        print(f"💥 Erreur Critique : {e}")
        if "429" in str(e):
            print("🚫 Trop de requêtes ! Pause de sécurité de 15s...")
            time.sleep(15)
        else:
            time.sleep(5)

    return False


# ==========================================
# PARTIE 3 : POINT D'ENTRÉE
# ==========================================
if __name__ == "__main__":
    TOKEN = "a729a0ed3b8f5ca37e5b8f95a9fa61d0"
    URL = "https://24hcode2026.plaiades.fr"

    # 0.45 req/s => ~0.9 requête/s en comptant get_state + act, sous la limite du serveur
    client = GameAPIClient(URL, TOKEN, max_calls_per_second=0.45)
    agent = FrontierAgent()

    while True:
        try:
            success = jouer_labyrinthe(client, agent)
            if not success:
                print("🔄 Session infructueuse, attente avant nouvelle tentative...")
                time.sleep(5)  # Laisser le serveur fermer la session en cours
        except Exception as e:
            print(f"Erreur : {e}")
            time.sleep(5)
