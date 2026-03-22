from __future__ import annotations
from players.shared_api_client import GameAPIClient
import pickle
from pathlib import Path
import random

import time
import requests

URL = "https://24hcode2026.plaiades.fr/"
TOKEN = "a729a0ed3b8f5ca37e5b8f95a9fa61d0"

GAME_NAME = "Tic-Tac-Toe"
REUSE_SESSION_ID = None 


def winner(board: list[list[str]]) -> str | None:
    lines = list(board)
    lines.extend([[board[0][c], board[1][c], board[2][c]] for c in range(3)])
    lines.append([board[0][0], board[1][1], board[2][2]])
    lines.append([board[0][2], board[1][1], board[2][0]])
    for line in lines:
        if line[0] and line[0] == line[1] == line[2]:
            return line[0]
    return None


def is_full(board: list[list[str]]) -> bool:
    return all(cell not in ("", None) for row in board for cell in row)


def board_after_move(board: list[list[str]], action: str, player: str) -> list[list[str]]:
    r, c = int(action[0]), int(action[1])
    new_board = [row[:] for row in board]
    new_board[r][c] = player
    return new_board


def minimax(board: list[list[str]], actions: list[str], player: str) -> tuple[int, str | None]:
    w = winner(board)
    if w == "X": return 1, None
    if w == "O": return -1, None
    if is_full(board) or not actions: return 0, None

    if player == "X":
        best_score, best_action = -10, None
        for a in actions:
            nb = board_after_move(board, a, "X")
            score, _ = minimax(nb, [x for x in actions if x != a], "O")
            if score > best_score:
                best_score, best_action = score, a
        return best_score, best_action

    best_score, best_action = 10, None
    for a in actions:
        nb = board_after_move(board, a, "O")
        score, _ = minimax(nb, [x for x in actions if x != a], "X")
        if score < best_score:
            best_score, best_action = score, a
    return best_score, best_action


Q_TABLE_PATH = Path("tictactoe_q.pkl")
Q_TABLE = None

if Q_TABLE_PATH.exists():
    with Q_TABLE_PATH.open("rb") as f:
        Q_TABLE = pickle.load(f)
    print(f"Q-table chargée: {Q_TABLE_PATH}")
else:
    print("Q-table introuvable, fallback sur stratégie existante.")

def _state_key_from_server_state(state: dict) -> tuple:
    board = state.get("board") or [["", "", ""], ["", "", ""], ["", "", ""]]
    mapping = {"X": 1.0, "O": -1.0, "": 0.0, None: 0.0}
    flat = [mapping.get(board[r][c], 0.0) for r in range(3) for c in range(3)]
    turn_flag = 1.0 if state.get("current_player") == "X" else -1.0
    flat.append(turn_flag)
    return tuple(float(x) for x in flat)

def choose_action(state: dict, action_list: dict) -> str:
    valid = [a for a, ok in (action_list or {}).items() if ok]
    if not valid:
        return random.choice(list((action_list or {}).keys()))

    # Q-learning si modèle présent
    if Q_TABLE is not None:
        s = _state_key_from_server_state(state)
        qvals = Q_TABLE.get(s)
        if qvals is not None:
            # actions serveur attendues type "00","01",...
            best = max(valid, key=lambda a: qvals[int(a[0]) * 3 + int(a[1])])
            return best

    # fallback: centre puis random
    if "11" in valid:
        return "11"
    return random.choice(valid)


TERMINAL = {"win", "lose", "tie", "max_steps"}
RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}
NETWORK_EXCEPTIONS = (
    requests.exceptions.Timeout,
    requests.exceptions.ReadTimeout,
    requests.exceptions.ConnectionError,
    requests.exceptions.ChunkedEncodingError,
)


def api_call(fn, *args, retries: int = 20, base_sleep: float = 0.01, **kwargs):
    for attempt in range(retries):
        try:
            return fn(*args, **kwargs)

        except NETWORK_EXCEPTIONS as exc:
            wait_s = min(base_sleep , 2.0)
            print(f"Réseau/timeout sur {fn.__name__}: {exc} -> retry dans {wait_s:.2f}s")
            time.sleep(wait_s)

        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status not in RETRYABLE_STATUS:
                raise

            retry_after = 0.0
            if exc.response is not None:
                ra = exc.response.headers.get("Retry-After", "")
                try:
                    retry_after = float(ra)
                except ValueError:
                    pass

            # Prend le max entre ce que le serveur demande et notre backoff,
            # mais on plafonne à 2s car dépasser ça ne sert à rien pour ce jeu
            wait_s = min(max(retry_after, base_sleep), 2.0)
            print(f"HTTP {status} sur {fn.__name__} -> retry dans {wait_s:.2f}s")
            time.sleep(wait_s)

    raise RuntimeError(f"Erreur persistante sur {fn.__name__} après {retries} tentatives")


def get_tictactoe_id(client: GameAPIClient) -> int:
    games = api_call(client.list_games)
    for g in games:
        if g.get("name") == GAME_NAME:
            return int(g["id"])
    raise RuntimeError(f"Jeu '{GAME_NAME}' introuvable.")


def play_one_session(client: GameAPIClient, session_id: int) -> str:
    payload = api_call(client.get_state, session_id)
    t0 = time.perf_counter()  # ← chrono au démarrage
    moves = 0

    while True:
        state = payload.get("state") or {}
        action_list = payload.get("action_list") or {}
        status = payload.get("status")

        if status in TERMINAL:
            dt = time.perf_counter() - t0
            print(f"  → Terminal status={status} en {dt:.2f}s ({moves} moves)")
            return status
        if state.get("winner") == "X":
            dt = time.perf_counter() - t0
            print(f"  → Win en {dt:.2f}s ({moves} moves)")
            return "win"
        if state.get("winner") == "O":
            dt = time.perf_counter() - t0
            print(f"  → Lose en {dt:.2f}s ({moves} moves)")
            return "lose"
        if not action_list:
            dt = time.perf_counter() - t0
            print(f"  → Tie en {dt:.2f}s ({moves} moves)")
            return "tie"

        if state.get("current_player") == "X":
            action = choose_action(state, action_list)
            payload = api_call(client.act, session_id, action)
            moves += 1
        else:
            payload = api_call(client.get_state, session_id)


def main():
    client = GameAPIClient(URL, TOKEN, max_calls_per_second=10.0, cleanup_on_exit=False)

    wins = losses = ties = max_steps = 0
    game_id = get_tictactoe_id(client)

    session_id = REUSE_SESSION_ID
    i = 0
    times = []
    
    while True:
        i += 1
        if session_id is None:
            start = api_call(client.start_game, game_id)
            session_id = int(start["gamesessionid"])

        t_start = time.perf_counter()
        status = play_one_session(client, session_id)
        t_elapsed = time.perf_counter() - t_start
        times.append(t_elapsed)

        print(f"[{i}] session={session_id} -> {status} | Total: {t_elapsed:.2f}s")

        if status == "win":       wins      += 1
        elif status == "lose":    losses    += 1
        elif status == "tie":     ties      += 1
        else:                     max_steps += 1

        avg_time = sum(times) / len(times) if times else 0
        print(f"Totaux: win={wins}, lose={losses}, tie={ties}, max_steps={max_steps}")
        print(f"Temps moyen: {avg_time:.2f}s/partie | Parties/min: {60/avg_time:.1f}")
        
        session_id = None  # nouvelle partie à chaque tour


if __name__ == "__main__":
    main()