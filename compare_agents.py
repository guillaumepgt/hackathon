"""Analyse HTML des scores publics et comparaison d'agents."""

from __future__ import annotations

import re
import html as ihtml
from datetime import datetime, timedelta
from collections import defaultdict
import time
import hashlib
import argparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

SCORES_URL = "https://24hcode2026.plaiades.fr/scores"
AGENTS = ["Lumen", "bfsm", "TheLastCommit"]

GAME_ORDER = [
    "Tic-Tac-Toe",              # 1
    "Car Racing",               # 2
    "Snake",                    # 3
    "Rush Hour",                # 4
    "Adaptive Traffic Racing",  # 5
    "Partial Visibility Maze",  # 6
    "Lava Maze",                # 7
    "Key & Door Maze",          # 8
    "Lava + Key & Door Maze",   # 9
    "Noisy Moon Lander Lite",   # 10
]

_CONNECT_TIMEOUT = 5
_READ_TIMEOUT = 25

_session = requests.Session()
_retry = Retry(
    total=5,
    connect=5,
    read=5,
    backoff_factor=0.8,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=frozenset(["GET"]),
)
_adapter = HTTPAdapter(max_retries=_retry)
_session.mount("https://", _adapter)
_session.mount("http://", _adapter)


def fetch_scores_html() -> str | None:
    try:
        r = _session.get(
            SCORES_URL,
            timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT),
            headers={"User-Agent": "compare-agents/1.0"},
        )
        r.raise_for_status()
        return r.text
    except requests.exceptions.RequestException as e:
        print(f"⚠️ fetch /scores échoué: {e}")
        return None


def _strip_tags(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s)
    s = ihtml.unescape(s)
    return " ".join(s.split()).strip()


def parse_scores_html(doc: str) -> list[dict]:
    rows = []
    trs = re.findall(r"<tr[^>]*>(.*?)</tr>", doc, flags=re.IGNORECASE | re.DOTALL)
    for tr in trs:
        tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.IGNORECASE | re.DOTALL)
        if len(tds) < 5:
            continue

        cols = [_strip_tags(x) for x in tds]
        team = cols[0]
        game = cols[1]
        result = cols[2]
        points_raw = cols[3]
        date_raw = cols[4]

        try:
            points = int(re.sub(r"[^\d-]", "", points_raw) or "0")
        except ValueError:
            points = 0

        try:
            ts = datetime.strptime(date_raw, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            ts = None

        rows.append(
            {
                "team": team,
                "game": game,
                "result": result,
                "points": points,
                "date": ts,
            }
        )
    return rows


def _row_key(r: dict) -> tuple:
    return (r.get("team"), r.get("game"), r.get("result"), r.get("points"), r.get("date"))


def merge_history(history_rows: list[dict], seen_keys: set[tuple], new_rows: list[dict]) -> int:
    """Ajoute seulement les nouvelles lignes (déduplication)."""
    added = 0
    for r in new_rows:
        k = _row_key(r)
        if k in seen_keys:
            continue
        seen_keys.add(k)
        history_rows.append(r)
        added += 1
    return added


def _rate_per_hour(count: int, tmin: datetime | None, tmax: datetime | None) -> float:
    if count <= 0 or tmin is None or tmax is None:
        return 0.0
    hours = (tmax - tmin).total_seconds() / 3600.0
    if hours <= 0:
        hours = 1.0 / 60.0  # 1 minute min pour éviter division par 0
    return count / hours


def analyze(rows: list[dict]) -> tuple[dict, list[str]]:
    filtered = [r for r in rows if r["team"] in AGENTS]

    found_games = {r["game"] for r in filtered}
    games = [g for g in GAME_ORDER if g in found_games]
    extras = sorted(found_games - set(GAME_ORDER))  # au cas où de nouveaux jeux apparaissent
    games.extend(extras)

    results = {}
    for a in AGENTS:
        rws = [r for r in filtered if r["team"] == a]
        dates = [r["date"] for r in rws if r["date"] is not None]
        tmin = min(dates) if dates else None
        tmax = max(dates) if dates else None

        wins = sum(1 for r in rws if r["result"].lower() == "win")
        ties = sum(1 for r in rws if r["result"].lower() == "tie")
        loses = sum(1 for r in rws if r["result"].lower() == "lose")

        per_game = {}
        for g in games:
            gg = [r for r in rws if r["game"] == g]
            gd = [r["date"] for r in gg if r["date"] is not None]
            gmin = min(gd) if gd else None
            gmax = max(gd) if gd else None
            per_game[g] = {
                "count": len(gg),
                "points": sum(x["points"] for x in gg),
                "wins": sum(1 for x in gg if x["result"].lower() == "win"),
                "ties": sum(1 for x in gg if x["result"].lower() == "tie"),
                "loses": sum(1 for x in gg if x["result"].lower() == "lose"),
                "games_per_hour": _rate_per_hour(len(gg), gmin, gmax),
                "points_per_hour": _rate_per_hour(sum(x["points"] for x in gg), gmin, gmax),
            }

        total_points = sum(r["points"] for r in rws)
        total_count = len(rws)
        results[a] = {
            "count": total_count,
            "points": total_points,
            "wins": wins,
            "ties": ties,
            "loses": loses,
            "games_per_hour": _rate_per_hour(total_count, tmin, tmax),
            "points_per_hour": _rate_per_hour(total_points, tmin, tmax),
            "per_game": per_game,
        }

    return results, games


def print_report(results: dict, games: list[str]) -> None:
    print("\n" + "=" * 110)
    print("COMPARAISON GLOBALE")
    print("=" * 110)
    print(f"{'Agent':<16}{'Parties':<10}{'Points':<10}{'W/T/L':<12}{'Parties/h':<12}{'Points/h':<12}")
    for a in AGENTS:
        r = results[a]
        wtl = f"{r['wins']}/{r['ties']}/{r['loses']}"
        print(
            f"{a:<16}{r['count']:<10}{r['points']:<10}{wtl:<12}"
            f"{r['games_per_hour']:<12.2f}{r['points_per_hour']:<12.2f}"
        )

    print("\n" + "=" * 110)
    print("DETAIL PAR JEU")
    print("=" * 110)
    for g in games:
        print(f"\n[{g}]")
        print(f"{'Agent':<16}{'Parties':<10}{'Points':<10}{'W/T/L':<12}{'Parties/h':<12}{'Points/h':<12}")
        for a in AGENTS:
            pg = results[a]["per_game"][g]
            wtl = f"{pg['wins']}/{pg['ties']}/{pg['loses']}"
            print(
                f"{a:<16}{pg['count']:<10}{pg['points']:<10}{wtl:<12}"
                f"{pg['games_per_hour']:<12.2f}{pg['points_per_hour']:<12.2f}"
            )

    ranking = sorted(AGENTS, key=lambda x: results[x]["points"], reverse=True)
    print("\n" + "=" * 110)
    print("CLASSEMENT GLOBAL (points)")
    print("=" * 110)
    for i, a in enumerate(ranking, 1):
        print(f"{i}. {a} - {results[a]['points']} pts")


def print_cumulative_avg_per_game(rows: list[dict]) -> None:
    """Moyennes par jeu depuis le démarrage (historique cumulé)."""
    filtered = [r for r in rows if r.get("team") in AGENTS]
    if not filtered:
        print("Aucune donnée cumulée pour les agents ciblés.")
        return

    games = sorted({r["game"] for r in filtered})

    print("\n" + "=" * 110)
    print("MOYENNES CUMULÉES PAR JEU (depuis le lancement)")
    print("=" * 110)

    for g in games:
        print(f"\n[{g}]")
        print(f"{'Agent':<16}{'Parties':<10}{'Points tot':<12}{'Points moy':<12}{'Winrate':<10}")
        for a in AGENTS:
            rr = [x for x in filtered if x["game"] == g and x["team"] == a]
            n = len(rr)
            pts = sum(x["points"] for x in rr)
            pavg = (pts / n) if n else 0.0
            wins = sum(1 for x in rr if str(x["result"]).lower() == "win")
            ties = sum(1 for x in rr if str(x["result"]).lower() == "tie")
            wr = ((wins + ties) / n * 100.0) if n else 0.0
            print(f"{a:<16}{n:<10}{pts:<12}{pavg:<12.2f}{wr:<10.1f}%")


def run_once() -> None:
    html_doc = fetch_scores_html()
    if not html_doc:
        print("Aucune donnée récupérée (timeout/réseau).")
        return
    rows = parse_scores_html(html_doc)
    results, games = analyze(rows)

    if not rows:
        print("Aucune ligne de score trouvée dans la page HTML.")
        return
    if not games:
        print("Aucune donnée pour les agents ciblés.")
        return

    print_report(results, games)


def run_live(interval: int = 30, only_on_change: bool = False, window_seconds: int = 120) -> None:
    # interval = fetch period (30s), window_seconds = log period (120s)
    last_sig = None
    next_log_ts = time.time() + window_seconds

    history_rows: list[dict] = []
    seen_keys: set[tuple] = set()
    n=0
    while True:
        try:
            html_doc = fetch_scores_html()
            if html_doc:
                if only_on_change:
                    sig = hashlib.md5(html_doc.encode("utf-8")).hexdigest()
                    if sig != last_sig:
                        last_sig = sig
                        current_rows = parse_scores_html(html_doc)
                        merge_history(history_rows, seen_keys, current_rows)
                else:
                    current_rows = parse_scores_html(html_doc)
                    merge_history(history_rows, seen_keys, current_rows)

            # logs toutes les 2 minutes (même si pas de changement)
            now = time.time()
            if now >= next_log_ts:
                print("\n" + "=" * 110)
                n += 1
                print(f"LOG {n} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"Historique cumulé: {len(history_rows)} lignes")
                print("=" * 110)

                results, games = analyze(history_rows)
                if history_rows and games:
                    print_report(results, games) 
                else:
                    print("Aucune donnée pour les agents ciblés.")

                next_log_ts = now + window_seconds

            time.sleep(interval)

        except KeyboardInterrupt:
            print("\nArrêt du monitoring.")
            break
        except Exception as e:
            print(f"Erreur: {e}")
            time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Comparaison d'agents depuis /scores (HTML)")
    parser.add_argument("--live", action="store_true", help="Boucle continue")
    parser.add_argument("--interval", type=int, default=30, help="Intervalle en secondes (défaut: 30)")
    parser.add_argument("--only-on-change", action="store_true", help="Affiche seulement si la page change")
    parser.add_argument("--window-seconds", type=int, default=120, help="Fenêtre de moyenne glissante (défaut: 120)")
    args = parser.parse_args()

    if args.live:
        run_live(interval=args.interval, only_on_change=args.only_on_change, window_seconds=args.window_seconds)
    else:
        run_once()


if __name__ == "__main__":
    main()