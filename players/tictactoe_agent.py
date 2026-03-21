from __future__ import annotations

import argparse
import random
from typing import Iterable

from players.shared_api_client import GameAPIClient


GAME_ID = 1


def lines(board):
    for r in range(3):
        yield [board[r][0], board[r][1], board[r][2]]
    for c in range(3):
        yield [board[0][c], board[1][c], board[2][c]]
    yield [board[0][0], board[1][1], board[2][2]]
    yield [board[0][2], board[1][1], board[2][0]]


def winner(board):
    for line in lines(board):
        if line[0] and line[0] == line[1] == line[2]:
            return line[0]
    return None


def board_full(board):
    return all(board[r][c] for r in range(3) for c in range(3))


def norm_cell(v):
    if v is None:
        return ""
    s = str(v).strip().upper()
    if s in {"", ".", "-", "_", "NONE", "NULL"}:
        return ""
    if s in {"X", "O"}:
        return s
    return ""


def extract_board(state: dict) -> list[list[str]]:
    # Formats fréquents: state["grid"], state["board"], state["cells"]
    raw = state.get("grid") or state.get("board") or state.get("cells")
    if isinstance(raw, list) and len(raw) == 3 and all(isinstance(r, list) and len(r) == 3 for r in raw):
        return [[norm_cell(raw[r][c]) for c in range(3)] for r in range(3)]
    # fallback vide
    return [["", "", ""], ["", "", ""], ["", "", ""]]


def extract_symbols(state: dict):
    me = str(state.get("my_symbol", "X")).upper()
    if me not in {"X", "O"}:
        me = "X"
    opp = "O" if me == "X" else "X"
    return me, opp


def to_action(r, c):
    return f"{r}{c}"


def minimax(board, turn, me, opp):
    w = winner(board)
    if w == me:
        return 1, None
    if w == opp:
        return -1, None
    if board_full(board):
        return 0, None

    best_score = -2 if turn == me else 2
    best_move = None

    for r in range(3):
        for c in range(3):
            if board[r][c]:
                continue
            board[r][c] = turn
            score, _ = minimax(board, opp if turn == me else me, me, opp)
            board[r][c] = ""

            if turn == me:
                if score > best_score:
                    best_score, best_move = score, (r, c)
            else:
                if score < best_score:
                    best_score, best_move = score, (r, c)

    return best_score, best_move


def choose_action(state: dict, valid_actions: Iterable[str]) -> str:
    valid = set(valid_actions or [])
    if not valid:
        valid = {to_action(r, c) for r in range(3) for c in range(3)}

    board = extract_board(state)
    me, opp = extract_symbols(state)

    _, move = minimax(board, me, me, opp)
    if move is not None:
        a = to_action(*move)
        if a in valid:
            return a

    # fallback: jouer un coup valide quelconque
    candidates = sorted(valid)
    return random.choice(candidates)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-url", required=True, help="Ex: https://24hcode2026.plaiades.fr/api")
    parser.add_argument("--api-key", required=True)
    args = parser.parse_args()

    client = GameAPIClient(args.server_url, args.api_key, cleanup_on_exit=False)

    start = client.start_game(GAME_ID)
    session_id = int(start["gamesessionid"])
    action_list = (start.get("action_list") or {}).keys()

    while True:
        payload = client.get_state(session_id)
        state = payload.get("state", {})
        action = choose_action(state, action_list)
        result = client.act(session_id, action)
        status = str(result.get("status", "continue"))
        if status != "continue":
            print(f"Session {session_id} terminé: {status}")
            break


if __name__ == "__main__":
    main()