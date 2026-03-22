# On utilise une image Node.js légère
FROM node:20-alpine

# On définit le dossier de travail dans le conteneur
WORKDIR /app

# On copie d'abord les fichiers de dépendances (pour optimiser le cache Docker)
COPY package.json package-lock.json* ./

# Installation des dépendances
RUN npm install

# On copie le reste du code
COPY . .

# On expose le port par défaut de Vite.js
EXPOSE 5173

# Commande pour démarrer le serveur (avec --host pour que Docker l'expose vers l'extérieur)
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]