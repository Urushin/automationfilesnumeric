@echo off
chcp 65001 >nul
title Lancer Application Automatisation

:: Configuration du dossier racine du projet
set "PROJECT_ROOT=C:\Users\issam\Documents\Projets perso\AutomatisationNumericFiles"

echo =======================================================
echo Démarrage de l'Application en cours...
echo =======================================================

:: 1. Démarrage du Backend (FastAPI)
echo Démarrage du serveur Backend (FastAPI)...
cd /d "%PROJECT_ROOT%\backend"
:: Activation de l'environnement virtuel si présent (décommenter la ligne ci-dessous si nécessaire)
:: call venv\Scripts\activate
start /b python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

:: 2. Démarrage du Frontend (Next.js)
echo Démarrage du serveur Frontend (Next.js)...
cd /d "%PROJECT_ROOT%\frontend"
start /b npm run dev

:: 3. Attente d'initialisation des ports
echo Attente de l'initialisation des ports (4 secondes)...
timeout /t 4 /nobreak >nul

:: 4. Ouverture de l'application dans le navigateur par défaut
echo Ouverture de l'application web...
start http://localhost:3000

echo =======================================================
echo Application démarrée !
echo APPUYEZ SUR ENTRÉE DANS CETTE FENÊTRE POUR TOUT ARRÊTER.
echo =======================================================
echo.

:: Bloquer la fenêtre pour garder les serveurs actifs et intercepter l'arrêt
set /p exit_prompt=Appuyez sur [Entrée] pour quitter et arrêter les serveurs...

:: 5. Arrêt propre des processus serveurs en arrière-plan
echo Arrêt des serveurs en cours...
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im node.exe >nul 2>&1

echo Tout est arrêté. Vous pouvez fermer cette fenêtre.
timeout /t 2 >nul
exit
