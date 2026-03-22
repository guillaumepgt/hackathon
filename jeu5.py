import time
from players.shared_api_client import GameAPIClient

class AdaptiveTrafficRacing:
    def __init__(self, api_client):
        self.api = api_client
        self.game_id = 5

    def play_game(self):
        print("\n🏎️ [Jeu 5] Démarrage de la course (Adaptive Drive)...")
        start = self.api.start_game(self.game_id)
        session_id = start["gamesessionid"]

        while True:
            # 1. Récupération des données
            payload = self.api.get_state(session_id)
            state = payload["state"]

            lane = state["lane"]
            speed = state["speed"]
            gaps = state["lane_gaps"]
            progress = state["progress"]

            # Remplacement des NULL par une très grande distance (route dégagée)
            current_ahead = gaps[lane]["ahead"] if gaps[lane]["ahead"] is not None else 999

            # Distance d'anticipation basée sur notre vitesse
            safe_distance = max(10, speed * 2 + 3)

            action = "keep"

            # 2. LOGIQUE ADAPTATIVE
            if current_ahead < safe_distance:
                # Danger devant ! On cherche une issue sur les voies directement ADJACENTES
                best_lane = lane
                best_ahead = current_ahead

                for target_lane in [lane - 1, lane + 1]:
                    if 0 <= target_lane <= 2: # On vérifie que la voie existe (0, 1 ou 2)
                        if gaps[target_lane]["safe_now"]:
                            target_ahead = gaps[target_lane]["ahead"] if gaps[target_lane]["ahead"] is not None else 999
                            # On choisit la voie qui offre le plus d'espace
                            if target_ahead > best_ahead:
                                best_ahead = target_ahead
                                best_lane = target_lane

                # Exécution de l'esquive ou freinage d'urgence
                if best_lane < lane:
                    action = "left"
                elif best_lane > lane:
                    action = "right"
                else:
                    action = "brake" # Aucune voie adjacente libre, on plante les freins

            else:
                # Voie dégagée, on gère la vitesse de croisière
                if speed < 15: # Vitesse max cible (à ajuster selon la nervosité des adversaires)
                    action = "accelerate"
                else:
                    action = "keep"

            print(f"  -> Prog: {progress:.1f}/130 | Voie: {lane} | Vit: {speed:.1f} | Dist. dev: {current_ahead:.1f} => Action: {action.upper()}")

            # 3. Envoi de l'action
            result = self.api.act(session_id, action)
            status = result.get("status")

            if status != "continue":
                print(f"🏁 FIN DE COURSE | Statut: {status} | Progression: {result.get('state', {}).get('progress', progress):.1f}/130")
                # Nettoyage de la session pour éviter le blocage
                try:
                    self.api.stop_game(session_id, allow_missing=True)
                except:
                    pass
                break

if __name__ == "__main__":
    # N'oublie pas de vérifier ton token
    TOKEN = "a729a0ed3b8f5ca37e5b8f95a9fa61d0"
    URL = "https://24hcode2026.plaiades.fr"

    # On utilise 0.95 pour maximiser les actions par seconde sans déclencher l'erreur de rate limiting
    client = GameAPIClient(URL, TOKEN, max_calls_per_second=0.95)
    bot = AdaptiveTrafficRacing(client)

    course_num = 1
    while True:
        print(f"\n=======================")
        print(f"   COURSE N°{course_num}")
        print(f"=======================")
        try:
            bot.play_game()
        except Exception as e:
            print