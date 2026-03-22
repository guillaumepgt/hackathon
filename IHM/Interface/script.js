document.addEventListener('DOMContentLoaded', () => {
    const cards = document.querySelectorAll('.game-card');

    cards.forEach((card) => {
        // Le JS ne fait plus qu'UNE seule chose : ajouter/enlever la classe d'état
        
        card.addEventListener('mouseenter', () => {
            card.classList.add('is-hovered');
            // L'opacité et les mouvements sont gérés dans style.css
        });

        card.addEventListener('mouseleave', () => {
            card.classList.remove('is-hovered');
            // L'opacité et les mouvements reviennent par défaut via style.css
        });       
    });
});