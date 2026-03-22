from __future__ import annotations

import time
import requests

from players.shared_api_client import GameAPIClient

URL = "https://24hcode2026.plaiades.fr/"
TOKEN = "a729a0ed3b8f5ca37e5b8f95a9fa61d0"

GAME_NAME = "Car Racing"
TERMINAL = {"win", "lose", "tie", "max_steps"}
MAX_STEPS = 1000

RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}

NETWORK_EXCEPTIONS = (
    requests.exceptions.Timeout,
    requests.exceptions.ReadTimeout,
    requests.exceptions.ConnectionError,
    requests.exceptions.ChunkedEncodingError,
    requests.exceptions.SSLError,
)

LANES = (0, 1, 2)
ACTION_TO_DLANE = {"move_left": -1, "move_right": 1, "stay": 0}


class RetryableAPIError(Exception):
    pass


def api_call(fn, *args, retries: int = 8, base_sleep: float = 0.15, **kwargs):
    for attempt in range(retries):
        try:
            return fn(*args, **kwargs)

        except NETWORK_EXCEPTIONS:
            wait_s = min(base_sleep * (1.8 ** attempt), 1.5)
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

            # 429: backoff court + respect Retry-After
            if status == 429:
                short_backoff = min(0.20 + 0.20 * attempt, 1.2)
                wait_s = max(retry_after, short_backoff)
            else:
                wait_s = min(max(retry_after, base_sleep * (1.8 ** attempt)), 2.0)

            time.sleep(wait_s)

    raise RetryableAPIError(f"Erreur persistante sur {fn.__name__}")


def to_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def infer_action_list_from_state() -> dict:
    return {"move_left": "move_left", "move_right": "move_right", "stay": "stay"}


def next_lane(current_lane: int, action: str) -> int:
    return max(0, min(2, current_lane + ACTION_TO_DLANE.get(action, 0)))


def normalize_obstacle(obs):
    # dict {"position":x,"lane":y} ou {"step":x,"lane":y} ou [x,y]
    if isinstance(obs, dict):
        p = to_int(obs.get("position", obs.get("pos", obs.get("step", 0))), 0)
        l = to_int(obs.get("lane", 1), 1)
        return p, l
    if isinstance(obs, (list, tuple)) and len(obs) >= 2:
        return to_int(obs[0], 0), to_int(obs[1], 1)
    return None


def parse_state(state: dict):
    position = to_int(state.get("position", state.get("step", 0)), 0)
    lane = to_int(state.get("lane", state.get("current_lane", 1)), 1)

    raw_obstacles = (
        state.get("upcoming_obstacles")
        or state.get("visible_obstacles")
        or state.get("obstacles_visible")
        or state.get("obstacles")
        or []
    )

    obstacles: list[tuple[int, int]] = []
    for o in raw_obstacles:
        n = normalize_obstacle(o)
        if n is not None and n[1] in LANES:
            obstacles.append(n)

    return position, lane, obstacles


def extract_state_and_actions(payload: dict) -> tuple[dict, dict]:
    # Car Racing peut renvoyer un état "flat" (position/lane directement à la racine)
    state = payload.get("state")
    if not isinstance(state, dict) or not state:
        state = payload

    action_list = (
        payload.get("action_list")
        or payload.get("actions")
        or payload.get("available_actions")
        or infer_action_list_from_state()
    )
    return state, action_list


def extract_allowed_actions(action_list: dict | None, current_lane: int | None = None) -> list[str]:
    if not action_list:
        allowed = ["move_left", "move_right", "stay"]
    else:
        allowed = []

        for k in action_list.keys():
            if k in ACTION_TO_DLANE:
                allowed.append(k)

        for v in action_list.values():
            if isinstance(v, str) and v in ACTION_TO_DLANE:
                allowed.append(v)

        out = []
        seen = set()
        for a in allowed:
            if a not in seen:
                seen.add(a)
                out.append(a)
        allowed = out or ["stay"]

    # IMPORTANT: retire les actions impossibles aux bords
    if current_lane is not None:
        if current_lane <= 0:
            allowed = [a for a in allowed if a != "move_left"]
        if current_lane >= 2:
            allowed = [a for a in allowed if a != "move_right"]

    return allowed or ["stay"]


def choose_action(state: dict, action_list: dict) -> str:
    position, lane, obstacles = parse_state(state)
    allowed = extract_allowed_actions(action_list, current_lane=lane)

    safe = []
    for a in allowed:
        nl = next_lane(lane, a)
        if not collision_at(position + 1, nl, obstacles):
            safe.append(a)

    candidates = safe if safe else allowed
    best_action = candidates[0]
    best_score = -1e9

    current_lane_dist = distance_to_next_obstacle(position, lane, obstacles, horizon=20)

    for a in candidates:
        nl = next_lane(lane, a)
        np = position + 1
        score = -1e9 if collision_at(np, nl, obstacles) else rollout_score(np, nl, obstacles, depth=2)

        if a == "stay":
            score -= 0.2
            if current_lane_dist <= 4:
                score -= 0.8

        if score > best_score:
            best_score = score
            best_action = a

    return best_action


def play_one_session(client: GameAPIClient, session_id: int) -> str:
    payload = api_call(client.get_state, session_id)
    steps = 0
    t0 = time.perf_counter()

    while True:
        state, action_list = extract_state_and_actions(payload)
        status = get_status_from_payload(payload, state)

        if status in TERMINAL:
            dt = max(time.perf_counter() - t0, 1e-9)
            print(f"[session={session_id}] fin={status} steps={steps} speed={steps/dt:.2f}/s")
            return status

        action = choose_action(state, action_list)

        try:
            result = api_call(client.act, session_id, action, retries=5, base_sleep=0.15)
        except RetryableAPIError:
            # fallback léger, sans gros sleep
            payload = api_call(client.get_state, session_id, retries=5, base_sleep=0.15)
            continue

        steps += 1

        # IMPORTANT: ne pas poller inutilement -> réutilise la réponse de act
        if isinstance(result, dict) and (
            "state" in result or "action_list" in result or "status" in result or "position" in result
        ):
            payload = result
        else:
            payload = api_call(client.get_state, session_id, retries=5, base_sleep=0.15)


def get_game_id(client: GameAPIClient) -> int:
    games = api_call(client.list_games)
    for g in games:
        if g.get("name") == GAME_NAME:
            return int(g["id"])
    raise RuntimeError(f"Jeu '{GAME_NAME}' introuvable.")

def get_status_from_payload(payload: dict, state: dict) -> str:
    status = payload.get("status") or state.get("status") or "continue"

    done = payload.get("done", state.get("done", False))
    if done and status == "continue":
        status = (
            payload.get("result")
            or state.get("result")
            or payload.get("outcome")
            or state.get("outcome")
            or "max_steps"
        )

    # Force max_steps à 1000
    step_like = to_int(
        state.get("step", state.get("position", payload.get("step", payload.get("position", 0)))),
        0,
    )
    if step_like >= MAX_STEPS and status == "continue":
        status = "max_steps"

    return status


def build_client() -> GameAPIClient:
    return GameAPIClient(
        URL,
        TOKEN,
        max_calls_per_second=0.95,  # marge anti-429 tout en restant rapide
        request_timeout=6.0,
        cleanup_on_exit=False,
    )

def collision_at(next_pos: int, lane: int, obstacles: list[tuple[int, int]]) -> bool:
    return any(op == next_pos and ol == lane for op, ol in obstacles)


def distance_to_next_obstacle(
    position: int,
    lane: int,
    obstacles: list[tuple[int, int]],
    horizon: int = 20,
) -> int:
    ahead = [op - position for op, ol in obstacles if ol == lane and op > position]
    if not ahead:
        return horizon
    return min(min(ahead), horizon)


def rollout_score(position: int, lane: int, obstacles: list[tuple[int, int]], depth: int) -> float:
    # Évaluation à horizon court
    if depth <= 0:
        return float(distance_to_next_obstacle(position, lane, obstacles, horizon=20)) + (0.15 if lane == 1 else 0.0)

    best = -1e9
    for a in ("move_left", "move_right", "stay"):
        nl = next_lane(lane, a)
        np = position + 1

        if collision_at(np, nl, obstacles):
            continue

        immediate = 3.0
        immediate += (-0.05 if a == "stay" else 0.05)
        immediate += (0.15 if nl == 1 else 0.0)
        immediate += 0.6 * distance_to_next_obstacle(np, nl, obstacles, horizon=10)

        score = immediate + 0.85 * rollout_score(np, nl, obstacles, depth - 1)
        if score > best:
            best = score

    return best if best > -1e8 else -1e9


def main():
    wins = losses = ties = max_steps = 0
    i = 0

    client = build_client()
    game_id = get_game_id(client)

    while True:
        try:
            i += 1
            start = api_call(client.start_game, game_id)
            session_id = int(start["gamesessionid"])
            print(f"[{i}] Nouvelle session Car Racing: gamesessionid={session_id}")

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

        except KeyboardInterrupt:
            print("Arrêt demandé par l'utilisateur.")
            break

        except (RetryableAPIError, *NETWORK_EXCEPTIONS) as exc:
            print(f"Erreur transitoire: {exc}. Reconnexion...")
            time.sleep(1.0)
            client = build_client()
            continue


if __name__ == "__main__":
    main()