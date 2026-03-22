/**
 * Fichier de configuration des données textuelles des jeux.
 * Les clés (1, 2, 3...) correspondent aux IDs définis dans App.js
 */
const GAMES_CONFIG = {
    1: {
        title: "Tic-Tac-Toe",
        desc: "Jeu classique du morpion sur une grille 3x3.",
        instructions: "Alignez 3 symboles identiques (X ou O) horizontalement, verticalement ou en diagonale pour gagner.",
        points: { win: "1 pt", loss: "-1 pt", draw: "1 pt" }
    },
    2: {
        title: "Car Racing",
        desc: "Naviguez sur une route à 3 voies et survivez le plus longtemps possible.",
        instructions: "Évitez les obstacles en changeant de voie avec les flèches Gauche et Droite.",
        points: { win: "2 pts", loss: "-1 pt" }
    },
    3: {
        title: "Snake",
        desc: "Dirigez le serpent pour manger les pommes et grandir sans vous heurter.",
        instructions: "Atteignez 40 segments pour gagner. Ne touchez ni les murs, ni votre propre corps.",
        points: { win: "3 pts", loss: "-1 pt" }
    },
    4: {
        title: "Rush Hour",
        desc: "Casse-tête de déblocage : libérez la voiture rouge coincée dans le trafic.",
        instructions: "Faites glisser les autres véhicules pour créer un chemin vers la sortie à droite.",
        points: { win: "4 pts", loss: "-1 pt" }
    },
    5: {
        title: "Traffic Racing",
        desc: "Course adaptative où les adversaires changent de comportement.",
        instructions: "Doublez les voitures prudemment. Attention, leur style de conduite est caché et évolutif.",
        points: { win: "6 à 7 pts", loss: "-2 pts" }
    },
    6: {
        title: "Partial Visibility Maze",
        desc: "Labyrinthe plongé dans le brouillard avec une vision limitée.",
        instructions: "Vous ne voyez qu'à 2 cases autour de vous. Trouvez la sortie (E) dans l'inconnu.",
        points: { win: "7 pts", loss: "-1 pt" }
    },
    7: {
        title: "Lava Maze",
        desc: "Labyrinthe mortel rempli de pièges de lave.",
        instructions: "Trouvez le chemin vers la sortie (E) sans jamais marcher sur une case de lave (L).",
        points: { win: "8 pts", loss: "-1 pt" }
    },
    8: {
        title: "Key & Door Maze",
        desc: "Labyrinthe avec mécanisme de verrouillage.",
        instructions: "Récupérez d'abord la clé (K) pour pouvoir ouvrir la porte (D) et sortir.",
        points: { win: "9 pts", loss: "-1 pt" }
    },
    9: {
        title: "Expert Maze",
        desc: "Le défi ultime combinant lave, clé et visibilité réduite.",
        instructions: "Évitez la lave, trouvez la clé et rejoignez la sortie dans ce labyrinthe complexe.",
        points: { win: "10 pts", loss: "-1 pt" }
    },
    10: {
        title: "Moon Lander",
        desc: "Simulateur d'atterrissage lunaire avec physique réaliste.",
        instructions: "Stabilisez le vaisseau et gérez la poussée pour atterrir doucement sur la plateforme.",
        points: { win: "10 à 11 pts", loss: "-2 pts" }
    }
};