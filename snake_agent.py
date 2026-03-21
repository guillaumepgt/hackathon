from __future__ import annotations

import time
from collections import deque
import requests

from players.shared_api_client import GameAPIClient

URL = "https://24hcode2026.plaiades.fr/"
TOKEN = "a729a0ed3b8f5ca37e5b8f95a9fa61d0"

GAME_NAME = "Snake"
TERMINAL = {"win", "lose", "tie", "max_steps"}
LOG_EVERY = 25  # moins de logs = moins d'overhead

DIRS = {
    "up": (-1, 0),
    "down": (1, 0),
    "left": (0, -1),
    "right": (0, 1),
}
OPPOSITE = {"up": "down", "down": "up", "left": "right", "right": "left"}


def api_call(fn, *args, retries: int = 6, base_sleep: float = 0.25, **kwargs):
    for attempt in range(retries):
        try:
            return fn(*args, **kwargs)
        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status != 429:
                raise

            retry_after = 0.0
            if exc.response is not None:
                h = exc.response.headers.get("Retry-After")
                if h:
                    try:
                        retry_after = float(h)
                    except ValueError:
                        retry_after = 0.0

            # backoff borné pour éviter les attentes énormes
            wait_s = min(max(retry_after, base_sleep * (2 ** attempt)), 2.0)
            print(f"429 sur {fn.__name__}, attente {wait_s:.2f}s...")
            time.sleep(wait_s)

    raise RuntimeError(f"429 persistant sur {fn.__name__}")


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


def bfs_path(head, target, blocked, n):
    """Retourne la liste complète d'actions jusqu'à target, ou None."""
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
            nxt = (cur[0] + dr, cur[1] + dc)
            if not in_bounds(nxt[0], nxt[1], n):
                continue
            if nxt in blocked and nxt != target:
                continue
            if nxt in parent:
                continue
            parent[nxt] = cur
            parent_move[nxt] = a
            q.append(nxt)

    if target not in parent:
        return None

    # reconstruction du chemin
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
        nr, nc = head[0] + dr, head[1] + dc
        if in_bounds(nr, nc, n) and (nr, nc) not in body_set:
            out.append(a)
    return out


def choose_action(state: dict, action_list: dict, planner: dict | None = None) -> str:
    allowed = [a for a in (action_list or {}).keys() if a in DIRS]
    if not allowed:
        raise RuntimeError("Aucune action valide reçue.")

    snake, food, direction, n = parse_state(state)
    if not snake:
        return allowed[0]

    head = snake[0]
    body_set = set(snake[1:])

    # éviter demi-tour si possible
    if direction in OPPOSITE and OPPOSITE[direction] in allowed and len(allowed) > 1:
        allowed = [a for a in allowed if a != OPPOSITE[direction]]

    # --- cache de plan ---
    if planner is not None:
        cached_food = planner.get("food")
        cached_path = planner.get("path")

        if (
            cached_food == food
            and isinstance(cached_path, deque)
            and len(cached_path) > 0
            and cached_path[0] in allowed
        ):
            return cached_path.popleft()

        new_path = bfs_path(head, food, body_set, n)
        if new_path:
            planner["food"] = food
            planner["path"] = deque(new_path)
            if planner["path"] and planner["path"][0] in allowed:
                return planner["path"].popleft()

    # fallback
    safe = safe_actions(head, body_set, n, allowed)
    if safe:
        return safe[0]
    return allowed[0]


def get_game_id(client: GameAPIClient) -> int:
    games = api_call(client.list_games)
    for g in games:
        if g.get("name") == GAME_NAME:
            return int(g["id"])
    raise RuntimeError(f"Jeu '{GAME_NAME}' introuvable.")


def play_one_session(client: GameAPIClient, session_id: int) -> str:
    step = 0
    payload = api_call(client.get_state, session_id)
    t0 = time.perf_counter()
    planner = {"food": None, "path": deque()}

    while True:
        status = payload.get("status", "continue")
        if status in TERMINAL:
            dt = max(time.perf_counter() - t0, 1e-9)
            print(f"[session={session_id}] fin -> {status} | moves/s={step/dt:.2f}")
            return status

        state = payload.get("state", {}) or {}
        action_list = payload.get("action_list") or {}
        if not action_list:
            action_list = infer_action_list_from_state(state)

        snake, food, direction, _ = parse_state(state)
        if not snake:
            return "max_steps"

        action = choose_action(state, action_list, planner)

        if step % LOG_EVERY == 0:
            print(f"[session={session_id}] step={step} head={snake[0]} dir={direction} food={food} action={action}")

        result = api_call(client.act, session_id, action)
        step += 1

        r_status = result.get("status", "continue")
        if r_status in TERMINAL:
            dt = max(time.perf_counter() - t0, 1e-9)
            print(f"[session={session_id}] fin -> {r_status} | moves/s={step/dt:.2f}")
            return r_status

        # optimisation: réutiliser act() même sans action_list
        if isinstance(result, dict) and "state" in result:
            payload = {
                "status": result.get("status", "continue"),
                "state": result.get("state") or {},
                "action_list": result.get("action_list") or infer_action_list_from_state(result.get("state") or {}),
            }
        else:
            payload = api_call(client.get_state, session_id)


def main():
    client = GameAPIClient(
        URL,
        TOKEN,
        max_calls_per_second=1.0,   # garder 1.0 (limite serveur)
        request_timeout=5.0,
        cleanup_on_exit=False,
    )
    game_id = get_game_id(client)

    wins = losses = ties = max_steps = 0
    i = 0

    while True:
        i += 1
        start = api_call(client.start_game, game_id)
        session_id = int(start["gamesessionid"])

        status = play_one_session(client, session_id)
        print(f"[{i}] session={session_id} -> {status}")

        if status == "win":
            wins += 1
        elif status == "lose":
            losses += 1
        elif status == "tie":
            ties += 1
        else:
            max_steps += 1

        print(f"Totaux: win={wins}, lose={losses}, tie={ties}, max_steps={max_steps}")


if __name__ == "__main__":
    main()