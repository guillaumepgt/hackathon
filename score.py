import requests
from bs4 import BeautifulSoup
from datetime import datetime
from collections import defaultdict
import time
import os

URL = "https://24hcode2026.plaiades.fr/scores"

def get_live_stats():
    try:
        # Timeout un peu plus court vu qu'on requête chaque seconde
        response = requests.get(URL, timeout=3)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Erreur de connexion au serveur : {e}")
        return

    table = soup.find('table')
    if not table:
        return

    rows = table.find('tbody').find_all('tr')

    parsed_data = []
    all_dates = []

    # 1. Extraction de toutes les données de la page
    for row in rows:
        cols = row.find_all('td')
        if len(cols) >= 5:
            team_name = cols[0].get_text(strip=True)
            game_name = cols[1].get_text(strip=True)
            date_str = cols[4].get_text(strip=True)

            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                parsed_data.append((team_name, game_name, dt))
                all_dates.append(dt)
            except ValueError:
                continue

    if not all_dates:
        return

    # 2. Utiliser l'heure du serveur comme référence pour éviter les décalages horaires
    latest_time = max(all_dates)

    # game_counts[jeu][equipe] = nombre_de_parties_en_15s
    game_counts = defaultdict(lambda: defaultdict(int))

    # 3. Filtrer sur les 15 dernières secondes et compter
    for team, game, dt in parsed_data:
        if (latest_time - dt).total_seconds() <= 120:
            game_counts[game][team] += 1

    # 4. Nettoyer l'écran du terminal pour faire un effet Dashboard
    os.system('cls' if os.name == 'nt' else 'clear')

    print("=" * 75)
    print(f"🚀 LIVE DASHBOARD - Moyenne sur les 15 dernières secondes")
    print(f"Dernier rafraîchissement : {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 75)

    if not game_counts:
        print("\nCalme plat. Aucune partie terminée dans les 15 dernières secondes.")
        return

    # 5. Calculer la vitesse et afficher le classement
    for game in sorted(game_counts.keys()):
        print(f"\n🎮 {game.upper()}")
        print("-" * 75)
        print(f"{'Pos':<5} | {'Équipe':<20} | {'Vitesse (Moyenne)':<25} | {'Parties validées'}")
        print("-" * 75)

        team_stats = []
        for team, count in game_counts[game].items():
            # Moyenne : 15 secondes / nb de parties.
            # Ex: 3 parties en 15s = 1 partie toutes les 5s.
            avg_speed = 120.0 / count
            team_stats.append((team, avg_speed, count))

        # Tri du plus rapide (temps le plus bas) au plus lent
        team_stats.sort(key=lambda x: x[1])

        for index, (team, avg_speed, count) in enumerate(team_stats, 1):
            freq_str = f"1 partie / {avg_speed:.1f} sec"

            if index == 1:
                print(f"🥇 {index:<3} | {team:<20} | {freq_str:<25} | {count}")
            elif index == 2:
                print(f"🥈 {index:<3} | {team:<20} | {freq_str:<25} | {count}")
            elif index == 3:
                print(f"🥉 {index:<3} | {team:<20} | {freq_str:<25} | {count}")
            else:
                print(f"   {index:<3} | {team:<20} | {freq_str:<25} | {count}")

if __name__ == "__main__":
    # Nettoyage initial du terminal
    os.system('cls' if os.name == 'nt' else 'clear')
    print("Démarrage du radar... Première requête en cours...")

    while True:
        get_live_stats()
        # Requête toutes les secondes
        time.sleep(1)