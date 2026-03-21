from __future__ import annotations

import time
import requests
from players.shared_api_client import GameAPIClient

URL = "https://24hcode2026.plaiades.fr/"
TOKEN = "a729a0ed3b8f5ca37e5b8f95a9fa61d0"

GAME_NAME = "Tic-Tac-Toe"
REUSE_SESSION_ID = None   # mettre None pour démarrer une nouvelle session


def winner(board: list[list[str]]) -> str | None:
    lines = []
    lines.extend(board)  
    lines.extend([[board[0][c], board[1][c], board[2][c]] for c in range(3)])  # cols
    lines.append([board[0][0], board[1][1], board[2][2]])
    lines.append([board[0][2], board[1][1], board[2][0]])

    for line in lines:
        if line[0] and line[0] == line[1] == line[2]:
            return line[0]
    return None


def is_full(board: list[list[str]]) -> bool:
    return all(cell != "" for row in board for cell in row)


def board_after_move(board: list[list[str]], action: str, player: str) -> list[list[str]]:
    r, c = int(action[0]), int(action[1])
    new_board = [row[:] for row in board]
    new_board[r][c] = player
    return new_board


def minimax(board: list[list[str]], actions: list[str], player: str) -> tuple[int, str | None]:
    w = winner(board)
    if w == "X":
        return 1, None
    if w == "O":
        return -1, None
    if is_full(board) or not actions:
        return 0, None

    if player == "X":
        best_score, best_action = -10, None
        for a in actions:
            nb = board_after_move(board, a, "X")
            next_actions = [x for x in actions if x != a]
            score, _ = minimax(nb, next_actions, "O")
            if score > best_score:
                best_score, best_action = score, a
        return best_score, best_action

    best_score, best_action = 10, None
    for a in actions:
        nb = board_after_move(board, a, "O")
        next_actions = [x for x in actions if x != a]
        score, _ = minimax(nb, next_actions, "X")
        if score < best_score:
            best_score, best_action = score, a
    return best_score, best_action


def choose_action(state: dict, action_list: dict) -> str:
    server_actions = list((action_list or {}).keys())
    if not server_actions:
        raise RuntimeError("Aucune action disponible.")

    board = state.get("board")
    if (
        not isinstance(board, list)
        or len(board) != 3
        or any(not isinstance(row, list) or len(row) != 3 for row in board)
    ):
        return server_actions[0]

    # Garde uniquement les actions correspondant à des cases réellement vides
    board_valid_actions: list[str] = []
    for a in server_actions:
        if len(a) == 2 and a[0].isdigit() and a[1].isdigit():
            r, c = int(a[0]), int(a[1])
            if 0 <= r < 3 and 0 <= c < 3 and board[r][c] in ("", None):
                board_valid_actions.append(a)

    actions = board_valid_actions or server_actions

    # Centre seulement si vide ET autorisé
    if "11" in actions and board[1][1] in ("", None):
        return "11"

    _, best = minimax(board, actions, "X")
    return best if best in actions else actions[0]


TERMINAL = {"win", "lose", "tie", "max_steps"}


def api_call(fn, *args, retries: int = 8, base_sleep: float = 0.25, **kwargs):
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

            wait_s = min(max(retry_after, base_sleep * (2 ** attempt)), 3.0)
            print(f"429 sur {fn.__name__}, attente {wait_s:.2f}s...")
            time.sleep(wait_s)

    raise RuntimeError(f"429 persistant sur {fn.__name__}")


def get_tictactoe_id(client: GameAPIClient) -> int:
    games = api_call(client.list_games)
    for g in games:
        if g.get("name") == GAME_NAME:
            return int(g["id"])
    raise RuntimeError(f"Jeu '{GAME_NAME}' introuvable.")


def play_one_session(client: GameAPIClient, session_id: int) -> str:
    payload = api_call(client.get_state, session_id)  # 1er état uniquement

    while True:
        state = payload.get("state", {}) or {}
        action_list = payload.get("action_list") or {}

        status = payload.get("status")
        if status in TERMINAL:
            return status

        winner_value = state.get("winner")
        if winner_value == "X":
            return "win"
        if winner_value == "O":
            return "lose"
        if not action_list:
            return "tie"

        if state.get("current_player") == "X":
            action = choose_action(state, action_list)
            print(f"session={session_id} | action={action}")
            result = api_call(client.act, session_id, action)

            # Réutilise la réponse act si possible
            if isinstance(result, dict) and ("state" in result or "action_list" in result or "status" in result):
                payload = result
            else:
                payload = api_call(client.get_state, session_id)
        else:
            # Pas de sleep fixe: le client applique déjà la limite 1 req/s
            payload = api_call(client.get_state, session_id)

def main():
    client = GameAPIClient(URL, TOKEN, max_calls_per_second=1.0, cleanup_on_exit=False)

    wins = losses = ties = max_steps = 0
    game_id = get_tictactoe_id(client)

    session_id = REUSE_SESSION_ID
    i = 0
    while True:
        i += 1
        if session_id is None:
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

        session_id = None  # nouvelle partie à chaque tour

    print(f"Résultats: win={wins}, lose={losses}, tie={ties}, max_steps={max_steps}")

if __name__ == "__main__":
    main()