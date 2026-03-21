from __future__ import annotations

from copy import Error
import time
import requests
from collections import deque

from players.shared_api_client import GameAPIClient

URL = "https://24hcode2026.plaiades.fr/"
TOKEN = "a729a0ed3b8f5ca37e5b8f95a9fa61d0"

GAME_NAME = "Snake"
TERMINAL = {"win", "lose", "tie", "max_steps"}
RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}


NETWORK_EXCEPTIONS = (
    requests.exceptions.Timeout,
    requests.exceptions.ReadTimeout,
    requests.exceptions.ConnectionError,
    requests.exceptions.ChunkedEncodingError,
    requests.exceptions.SSLError,
)

DIRS = {
    "up": (-1, 0),
    "down": (1, 0),
    "left": (0, -1),
    "right": (0, 1),
}
OPPOSITE = {"up": "down", "down": "up", "left": "right", "right": "left"}


class TooManyRequestsError(Exception):
    pass


class RetryableAPIError(Exception):
    pass


def api_call(fn, *args, retries: int = 8, base_sleep: float = 0.25, **kwargs):
    for attempt in range(retries):
        try:
            return fn(*args, **kwargs)

        except NETWORK_EXCEPTIONS as exc:
            wait_s = min(base_sleep * (2 ** attempt), 3.0)
            time.sleep(wait_s)

        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status not in RETRYABLE_STATUS:
                raise

            retry_after = 0.0
            if exc.response is not None:
                ra = exc.response.headers.get("Retry-After")
                if ra:
                    try:
                        retry_after = float(ra)
                    except ValueError:
                        retry_after = 0.0
            wait_s = min(max(retry_after, base_sleep * (2 ** attempt)), 3.0)
            time.sleep(wait_s)

    raise RetryableAPIError(f"Erreur persistante sur {fn.__name__}")


def norm_pos(p):
    # support [r,c], (r,c) ou {"x":..,"y":..}
    if isinstance(p, dict):
        if "row" in p and "col" in p:
            return (int(p["row"]), int(p["col"]))
        if "x" in p and "y" in p:
            return (int(p["y"]), int(p["x"]))
    if isinstance(p, (list, tuple)) and len(p) >= 2:
        return (int(p[0]), int(p[1]))
    raise ValueError(f"Position non reconnue: {p}")


def parse_state(state: dict):
    snake_raw = state.get("snake", [])
    food_raw = state.get("food")
    direction = state.get("direction")
    grid_size = int(state.get("grid_size", 20))

    snake = [norm_pos(s) for s in snake_raw] if snake_raw else []
    food = norm_pos(food_raw) if food_raw is not None else None
    return snake, food, direction, grid_size


def in_bounds(r, c, n):
    return 0 <= r < n and 0 <= c < n


def wrap_pos(r: int, c: int, n: int) -> tuple[int, int]:
    return (r % n, c % n)


def bfs_path(head, target, blocked, n):
    """Retourne la liste complète d'actions jusqu'à target (avec wrap), ou None."""
    if target is None:
        return None

    q = deque([head])
    parent = {head: None}
    parent_move = {}

    while q:
        cur = q.popleft()
        if cur == target:
            break

        for a, (dr, dc) in DIRS.items():
            nr, nc = wrap_pos(cur[0] + dr, cur[1] + dc, n)
            nxt = (nr, nc)

            # En wrap-around, pas de check in_bounds
            if nxt in blocked and nxt != target:
                continue
            if nxt in parent:
                continue

            parent[nxt] = cur
            parent_move[nxt] = a
            q.append(nxt)

    if target not in parent:
        return None

    actions = []
    cur = target
    while parent[cur] is not None:
        actions.append(parent_move[cur])
        cur = parent[cur]
    actions.reverse()
    return actions


def safe_actions(head, body_set, n, allowed):
    out = []
    for a in allowed:
        dr, dc = DIRS[a]
        nr, nc = wrap_pos(head[0] + dr, head[1] + dc, n)
        if (nr, nc) not in body_set:
            out.append(a)
    return out


def path_exists_wrap(start: tuple[int, int], target: tuple[int, int], blocked: set[tuple[int, int]], n: int) -> bool:
    if start == target:
        return True
    q = deque([start])
    seen = {start}
    while q:
        r, c = q.popleft()
        for dr, dc in DIRS.values():
            nr, nc = wrap_pos(r + dr, c + dc, n)
            nxt = (nr, nc)
            if nxt == target:
                return True
            if nxt in blocked or nxt in seen:
                continue
            seen.add(nxt)
            q.append(nxt)
    return False


def simulate_move(
    snake: list[tuple[int, int]],
    action: str,
    food: tuple[int, int] | None,
    n: int,
) -> tuple[list[tuple[int, int]], bool]:
    """Retourne (nouveau_snake, collision)."""
    dr, dc = DIRS[action]
    head = snake[0]
    new_head = wrap_pos(head[0] + dr, head[1] + dc, n)
    grow = (food is not None and new_head == food)

    # Si on ne grandit pas, la case de queue actuelle sera libérée (donc autorisée)
    occupied = set(snake if grow else snake[:-1])
    if new_head in occupied:
        return snake, True

    if grow:
        new_snake = [new_head] + snake
    else:
        new_snake = [new_head] + snake[:-1]
    return new_snake, False


def is_survivable_action(
    snake: list[tuple[int, int]],
    action: str,
    food: tuple[int, int] | None,
    n: int,
) -> bool:
    new_snake, collision = simulate_move(snake, action, food, n)
    if collision:
        return False

    # Heuristique de survie: garder un chemin tête -> queue
    new_head = new_snake[0]
    new_tail = new_snake[-1]
    blocked = set(new_snake[1:-1])  # on laisse la queue comme cible atteignable
    return path_exists_wrap(new_head, new_tail, blocked, n)


def choose_action_from_parsed(
    snake: list[tuple[int, int]],
    food: tuple[int, int] | None,
    direction: str | None,
    n: int,
    action_list: dict,
    planner: dict | None = None,
) -> str:
    allowed = [a for a in (action_list or {}).keys() if a in DIRS]
    if not allowed:
        raise RuntimeError("Aucune action valide reçue.")
    if not snake:
        return allowed[0]

    if direction in OPPOSITE and OPPOSITE[direction] in allowed and len(allowed) > 1:
        allowed = [a for a in allowed if a != OPPOSITE[direction]]

    # 1) action planifiée si elle reste survivable
    if planner is not None:
        cached_food = planner.get("food")
        cached_path = planner.get("path")
        if cached_food == food and isinstance(cached_path, deque) and cached_path:
            a = cached_path[0]
            if a in allowed and is_survivable_action(snake, a, food, n):
                return cached_path.popleft()

        head = snake[0]
        body_set = set(snake[1:])
        new_path = bfs_path(head, food, body_set, n)
        if new_path:
            planner["food"] = food
            planner["path"] = deque(new_path)
            a = planner["path"][0]
            if a in allowed and is_survivable_action(snake, a, food, n):
                return planner["path"].popleft()

    # 2) sinon: première action survivable
    for a in allowed:
        if is_survivable_action(snake, a, food, n):
            return a

    # 3) fallback: éviter au moins la collision immédiate
    for a in allowed:
        _, collision = simulate_move(snake, a, food, n)
        if not collision:
            return a

    return allowed[0]


def get_game_id(client: GameAPIClient) -> int:
    games = api_call(client.list_games)
    for g in games:
        if g.get("name") == GAME_NAME:
            return int(g["id"])
    raise RuntimeError(f"Jeu '{GAME_NAME}' introuvable.")


def play_one_session(client: GameAPIClient, session_id: int) -> str:
    step = 0
    req_count = 1
    act_with_state = 0
    payload = api_call(client.get_state, session_id)
    t0 = time.perf_counter()
    planner = {"food": None, "path": deque()}

    while True:
        status = payload.get("status", "continue")
        if status in TERMINAL:
            dt = max(time.perf_counter() - t0, 1e-9)
            print(
                f"[session={session_id}] fin -> {status} | moves/s={step/dt:.2f} | "
                f"req/move={req_count/max(step,1):.2f} | act_with_state={act_with_state}"
            )
            return status

        state = payload.get("state", {}) or {}
        action_list = payload.get("action_list") or infer_action_list_from_state(state)

        snake, food, direction, n = parse_state(state)
        if not snake:
            return "max_steps"

        action = choose_action_from_parsed(snake, food, direction, n, action_list, planner)

        try:
            result = api_call(client.act, session_id, action, retries=1, base_sleep=0.0)
            req_count += 1
        except RetryableAPIError:
            # IMPORTANT: ne pas faire get_state immédiat ici (sinon rafale)
            continue

        step += 1
        r_status = result.get("status", "continue")
        if r_status in TERMINAL:
            dt = max(time.perf_counter() - t0, 1e-9)
            print(
                f"[session={session_id}] fin -> {r_status} | moves/s={step/dt:.2f} | "
                f"req/move={req_count/max(step,1):.2f} | act_with_state={act_with_state}"
            )
            return r_status

        if isinstance(result, dict) and "state" in result:
            act_with_state += 1
            payload = {
                "status": result.get("status", "continue"),
                "state": result.get("state") or {},
                "action_list": result.get("action_list") or infer_action_list_from_state(result.get("state") or {}),
            }
        else:
            payload = api_call(client.get_state, session_id)
            req_count += 1


def infer_action_list_from_state(state: dict) -> dict:
    """Fallback local si le serveur ne renvoie pas action_list."""
    direction = state.get("direction")
    allowed = set(DIRS.keys())
    if direction in OPPOSITE:
        # Snake interdit généralement le demi-tour
        allowed.discard(OPPOSITE[direction])
    return {a: f"move {a}" for a in allowed}


def start_fresh_session(client: GameAPIClient, game_id: int, previous_session_id: int | None) -> int:
    # 1 seul appel start_game (évite burst)
    start = api_call(client.start_game, game_id)
    return int(start["gamesessionid"])


def build_client() -> GameAPIClient:
    return GameAPIClient(
        URL,
        TOKEN,
        max_calls_per_second=1.0,
        request_timeout=6.0,
        cleanup_on_exit=False,
    )


def main():
    wins = losses = ties = max_steps = 0
    i = 0
    previous_session_id = None
    reconnect_backoff = 1.0

    client = build_client()
    game_id = get_game_id(client)  # <-- une seule fois, pas dans la boucle

    while True:
        try:
            i += 1
            session_id = start_fresh_session(client, game_id, previous_session_id)
            
            print(f"[{i}] Nouvelle session Snake démarrée: gamesessionid={session_id}")

            status = play_one_session(client, session_id)

            if status == "win":
                wins += 1
            elif status == "lose":
                losses += 1
            elif status == "tie":
                ties += 1
            else:
                max_steps += 1

            print(f"Totaux: win={wins}, lose={losses}, tie={ties}, max_steps={max_steps}")
            previous_session_id = session_id
            reconnect_backoff = 1.0

        except (RetryableAPIError, TooManyRequestsError, *NETWORK_EXCEPTIONS) as exc:
            print(f"Déconnexion/erreur transitoire: {exc}. Reconnexion...")
            client = build_client()
            # game_id reste le même, pas besoin de relister à chaque fois
            continue

        except KeyboardInterrupt:
            print("Arrêt demandé par l'utilisateur.")
            break


if __name__ == "__main__":
    main()