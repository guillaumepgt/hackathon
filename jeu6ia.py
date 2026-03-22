import time
import random
from collections import deque
from players.shared_api_client import GameAPIClient

# ==========================================
# PARTIE 1 : L'AGENT EXPLORATEUR (IA HYBRIDE)
# ==========================================
class FrontierAgent:
    def __init__(self):
        self.memory_map = {}
        self.confirmed_walls = set() # <--- Nouveau : Le Panthéon des murs
        self.blacklist = set()
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
                
                # SI LA CASE EST UN MUR CONFIRMÉ, ON NE TOUCHE À RIEN
                if (gx, gy) in self.confirmed_walls:
                    self.memory_map[(gx, gy)] = '#'
                    continue

                if cell != '?':
                    self.memory_map[(gx, gy)] = cell

    def find_nearest_frontier(self, start_pos):
        queue = deque([start_pos])
        visited = {start_pos}
        
        while queue:
            curr = queue.popleft()
            x, y = curr
            
            for dx, dy in [(0,1), (0,-1), (1,0), (-1,0)]:
                neighbor = (x + dx, y + dy)
                
                # Si le voisin est inconnu
                if neighbor not in self.memory_map:
                    # On vérifie que curr n'est ni un mur, ni dans la blacklist
                    if self.memory_map.get(curr) != '#' and curr not in self.blacklist:
                        return curr
                
                if neighbor in self.memory_map and neighbor not in visited:
                    if self.memory_map[neighbor] != '#':
                        visited.add(neighbor)
                        queue.append(neighbor)
        return None

    def get_path(self, start, target):
        if start == target: return []
        queue = deque([(start, [])])
        visited = {start}
        while queue:
            (x, y), path = queue.popleft()
            if (x, y) == target: return path
            for move in self.actions:
                dx, dy = {"up":(0,-1), "down":(0,1), "left":(-1,0), "right":(1,0)}[move]
                nx, ny = x + dx, y + dy
                if (nx, ny) in self.memory_map and self.memory_map[(nx, ny)] != '#' and (nx, ny) not in visited:
                    visited.add((nx, ny))
                    queue.append(((nx, ny), path + [move]))
        return None

# ==========================================
# PARTIE 2 : LE SIMULATEUR LOCAL (POUR TESTER)
# ==========================================
class LocalMazeEnv:
    def __init__(self, size=10):
        self.size = size
        self.grid = []
        self.player_pos = [1, 1]
        self.exit_pos = [8, 8]

    def reset(self):
        # Création d'un mini labyrinthe simple
        self.grid = [['.' for _ in range(self.size)] for _ in range(self.size)]
        # Murs extérieurs
        for i in range(self.size):
            self.grid[0][i] = self.grid[self.size-1][i] = '#'
            self.grid[i][0] = self.grid[i][self.size-1] = '#'
        self.grid[8][8] = 'E'
        self.player_pos = [1, 1]
        return self.get_state()

    def get_state(self):
        px, py = self.player_pos
        visible = []
        for y in range(py-2, py+3):
            row = []
            for x in range(px-2, px+3):
                if 0 <= x < self.size and 0 <= y < self.size:
                    row.append(self.grid[y][x])
                else: row.append('#')
            visible.append(row)
        
        dist_exit = abs(px-8) <= 2 and abs(py-8) <= 2
        return {"player_pos": self.player_pos, "grid": visible, "exit_pos": [8, 8] if dist_exit else None}

# ==========================================
# PARTIE 3 : UTILISATION SERVEUR
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

        # --- INITIALISATION DES VARIABLES DE CONTRÔLE ---
        last_pos = None
        last_action = "up" # Valeur par défaut pour le premier tour
        target = None

        while True:
            # 1. Obtenir l'état
            res = client.get_state(session_id)
            if not res or "state" not in res:
                time.sleep(1)
                continue
                
            state = res["state"]
            curr_pos = tuple(state["player_pos"])
            
            # --- DÉTECTION DE CHOC ---
            if last_pos == curr_pos:
                dx, dy = {"up":(0,-1), "down":(0,1), "left":(-1,0), "right":(1,0)}[last_action]
                wall_pos = (curr_pos[0] + dx, curr_pos[1] + dy)
                print(f"💥 Collision RÉELLE en {wall_pos}! Verrouillage MUR.")
                
                # ON ENREGISTRE DANS LES DEUX
                agent.confirmed_walls.add(wall_pos)
                agent.memory_map[wall_pos] = '#'
                
                target = None 
                continue
            
            last_pos = curr_pos
            agent.update_map(state["grid"], curr_pos)

            # 2. Choisir la cible (Sortie > Frontier)
            if state.get("exit_pos"):
                target = tuple(state["exit_pos"])
            else:
                target = agent.find_nearest_frontier(curr_pos)
            
            if not target:
                print("🏁 Zone totalement explorée ou bloquée. Reset de la session...")
                # On tente de dire au serveur que c'est fini (si l'API le permet)
                # Sinon, le simple 'break' va quitter la boucle, et le 'while True' 
                # principal relancera une nouvelle partie.
                break

            # 3. Calculer le chemin
            path = agent.get_path(curr_pos, target)
            
            if path is None or len(path) == 0:
                print(f"🚫 Cible {target} inatteignable. Blacklistée.")
                agent.memory_map[target] = '#' 
                agent.blacklist.add(target)
                continue 

            # 4. Agir
            action = path[0]
            last_action = action # On mémorise pour le prochain tour
            
            print(f"📍 {curr_pos} -> {action} (Cible: {target})")
            res_act = client.act(session_id, action)

            # 5. Vérifier fin
            status = res_act.get("status")
            if status in ["win", "lose"]:
                print(f"🎉 FIN DE PARTIE : {status.upper()}")
                return status == "win"

    except Exception as e:
        print(f"💥 Erreur Critique : {e}")
        time.sleep(5)

if __name__ == "__main__":
    TOKEN = "a729a0ed3b8f5ca37e5b8f95a9fa61d0"
    URL = "https://24hcode2026.plaiades.fr"
    
    # On reste à 0.85 pour être rapide sans 429
    client = GameAPIClient(URL, TOKEN, max_calls_per_second=0.45)
    agent = FrontierAgent()

    # --- MODE SIMULATEUR (Décommenter pour tester sans internet) ---
    # env = LocalMazeEnv()
    # state = env.reset()
    # print("Test simulateur local...")

    # --- MODE SERVEUR ---
    while True:
        try:
            success = jouer_labyrinthe(client, agent)
            if not success:
                print("🔄 Session infructueuse, attente avant nouvelle tentative...")
                time.sleep(5) # On laisse le temps au serveur de fermer la session 76577
        except Exception as e:
            print(f"Erreur : {e}")
            time.sleep(5)