# Utilise l'image Python officielle allégée en tant qu'image de base
FROM python:3.11-slim

# Définit le répertoire de travail dans le conteneur
WORKDIR /app

# Empêche Python d'écrire des fichiers .pyc (compiled) et met en mode non-bufferisé pour les logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copie le fichier de requirements et installe les dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie tout le reste des fichiers du projet dans le conteneur
COPY . .

# Commande par défaut pour démarrer le bot
CMD ["python", "main.py"]
