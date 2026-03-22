import time
from players.shared_api_client import GameAPIClient

class MoonLanderControlledApproach:
    def __init__(self, api_client):
        self.api = api_client
        self.game_id = 10

    def play_game(self):
        print("\n🚀 [Jeu 10] Mission d'Atterrissage de PRÉCISION (Approche contrôlée)...")
        start = self.api.start_game(self.game_id)
        session_id = start["gamesessionid"]

        while True:
            payload = self.api.get_state(session_id)
            state = payload["state"]
            obs = state["observation"]

            # 0: alt, 1: vx, 2: vy, 3: dx_pad, 5: sin_theta, 7: omega, 8: leg_contact_l, 9: leg_contact_r
            alt, vx, vy, dx, fuel, sin_t, cos_t, omega, l_contact, r_contact = obs

            action = "idle"

            # 1. Coupe-circuit de contact au sol (Priorité absolue)
            if l_contact > 0 or r_contact > 0:
                action = "idle"

                # 2. Stabilisation d'inclinaison (Priorité 2)
            # On utilise la gyrostabilisation si ça penche trop
            elif abs(sin_t) > 0.15 or abs(omega) > 0.1:
                action = "stabilize"

            else:
                # 3. Calcul de l'alinement horizontal (Cible dX=0, précis à 1m près)
                target_vx = dx * 0.15 # Vitesse latérale proportionnelle à la distance
                target_vx = max(min(target_vx, 0.6), -0.6) # Bridage de vx max à 0.6

                need_side = None
                # dX est la distance à la cible. S'il est positif, la cible est à DROITE.
                # Allumer moteur droit -> x augmente, dX diminue. Allumer moteur gauche -> x diminue, dX augmente.
                # target_vx sera positive si dx > 0 (cible à droite). Si vx < target_vx, il faut accélérer à DROITE.
                if vx < target_vx - 0.1:
                    need_side = "right" # Allume moteur droit -> x augmente, dX diminue (Correct)
                elif vx > target_vx + 0.1:
                    need_side = "left"  # Allume moteur gauche -> x diminue, dX augmente (Correct)

                # 4. Profil de descente contrôlé (Lent pour donner du temps à dX)
                # target_vy sera par exemple de -0.5 à 10m de haut, et -0.2 près du sol
                # Ce profil est moins agressif pour augmenter le temps de vol
                target_vy = max(-0.5, -0.2 - (alt / 20.0))

                # Le simulateur valide l'atterrissage jusqu'à -1.10. On a énormément de marge.
                need_main = (vy < target_vy)

                # 5. Synthèse des actions combinées (Gère les deux axes)
                if need_main:
                    if need_side == "left": action = "main_left"
                    elif need_side == "right": action = "main_right"
                    else: action = "main"
                else:
                    if need_side == "left": action = "left"
                    elif need_side == "right": action = "right"
                    else:
                        # Si on est au-dessus de la cible (dx < 1.0) et qu'on dérape, on utilise le "frein magique"
                        # Le code source dit : abs(vx) <= 0.95 pour gagner. On vise 0.2.
                        if abs(dx) < 1.0 and abs(vx) > 0.2:
                            action = "stabilize"
                        else:
                            action = "idle"

            # Affichage télémétrie en temps réel pour debug
            print(f"  -> Alt:{alt:05.2f} | dX:{dx:+05.2f} | vX:{vx:+05.2f} | vY:{vy:+05.2f} | Fuel:{fuel*100:03.0f}% | {action.upper()}")

            result = self.api.act(session_id, action)
            status = result.get("status")

            if status != "continue":
                reward = result.get('reward', '?')
                if status == "win":
                    print(f"🏆 ATTERRISSAGE RÉUSSI AVEC PRÉCISION ! | Récompense: {reward} pts")
                else:
                    print(f"💥 ÉCHEC... Crash à dX={dx:.1f} | Récompense: {reward} pts")

                # Nettoyage de la session pour relancer proprement
                try:
                    self.api.stop_game(session_id, allow_missing=True)
                except:
                    pass
                break

if __name__ == "__main__":
    TOKEN = "a729a0ed3b8f5ca37e5b8f95a9fa61d0"
    URL = "https://24hcode2026.plaiades.fr"

    # Fréquence optimale pour ne pas trigger le Rate Limit (1 appel/s)
    client = GameAPIClient(URL, TOKEN, max_calls_per_second=0.95)
    bot = MoonLanderControlledApproach(client)

    partie_n = 1
    while True:
        print(f"\n=======================")
        print(f"   MISSION DE PRÉCISION N°{partie_n}")
        print(f"=======================")
        try:
            bot.play_game()
        except Exception as e:
            print(f"⚠️ Erreur de transmission Houston : {e}")
            time.sleep(2)
        partie_n += 1
        time.sleep(1)