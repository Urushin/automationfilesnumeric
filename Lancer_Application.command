#!/bin/bash

# Configuration des chemins absolus
REPO_ROOT="/Users/issam/Documents/Projets perso/AutomatisationNumericFiles"
cd "$REPO_ROOT" || exit 1

# Variables de suivi des processus
BACKEND_PID=""
FRONTEND_PID=""

# Routine de nettoyage à l'arrêt
cleanup() {
    echo "Arrêt en cours des serveurs d'application..."
    if [ -n "$BACKEND_PID" ]; then
        kill "$BACKEND_PID" 2>/dev/null
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill "$FRONTEND_PID" 2>/dev/null
    fi
    exit 0
}

# Piège (Trap) pour intercepter les signaux d'arrêt et de fermeture de la fenêtre
trap cleanup INT TERM EXIT

# 1. Démarrage du Backend (FastAPI)
echo "Démarrage du serveur Backend (FastAPI)..."
cd "$REPO_ROOT/backend" || exit 1
# Activation de l'environnement virtuel (décommenter si nécessaire)
# source .venv/bin/activate
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000 > /dev/null 2>&1 &
BACKEND_PID=$!

# 2. Démarrage du Frontend (Next.js)
echo "Démarrage du serveur Frontend (Next.js)..."
cd "$REPO_ROOT/frontend" || exit 1
npm run dev > /dev/null 2>&1 &
FRONTEND_PID=$!

# 3. Synchronisation et Ouverture de l'interface
echo "Attente de l'initialisation des ports..."
sleep 3

echo "Ouverture de l'application dans votre navigateur..."
open "http://localhost:3000"

# Maintenir le terminal actif pour conserver le trap opérationnel
wait
