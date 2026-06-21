@echo off
setlocal enabledelayedexpansion
title Lanceur Universel - Automatisation Numeric Files

echo ========================================================
echo       INITIALISATION AUTO-PORTABLE DU PROJET
echo ========================================================
echo.

:: 1. DYNAMICALLY CAPTURE THE DIRECTORY WHERE THE .BAT FILE IS LOCATED
:: %~dp0 includes the trailing backslash, we strip it or map it carefully
set "PROJECT_DIR=%~dp0"
:: Remove trailing backslash for consistency if needed, but quotes handle it safely
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

echo [DEBUG] Racine du projet detectee : "%PROJECT_DIR%"

:: 2. VALIDATION OF SYSTEM MAP INTEGRITY
if not exist "%PROJECT_DIR%\backend" (
    echo [CRITICAL] Dossier 'backend' introuvable dans le répertoire courant.
    echo Veuillez vous assurer que ce fichier .bat est place A LA RACINE du projet.
    goto CRASH_PAUSE
)
if not exist "%PROJECT_DIR%\frontend" (
    echo [CRITICAL] Dossier 'frontend' introuvable dans le répertoire courant.
    goto CRASH_PAUSE
)

:: 3. COMPILER BINARY EVALUATION
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [CRITICAL] Python est introuvable sur cette machine.
    echo Assurez-vous d'installer Python et de COCHER "Add python.exe to PATH" lors de l'installation.
    goto CRASH_PAUSE
)
where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo [CRITICAL] Node.js / NPM est introuvable sur cette machine.
    goto CRASH_PAUSE
)

:: 4. AUTOMATIC VIRTUAL ENVIRONMENT & PIP LOCK SYNC
echo [INFO] Verification de l'environnement virtuel Python...
cd /d "%PROJECT_DIR%\backend"
if not exist "venv" (
    echo [INFO] Premier démarrage : Creation de l'environnement virtuel (venv)...
    python -m venv venv
)
echo [INFO] Activation de l'environnement virtuel et synchronisation des modules...
call venv\Scripts\activate
python -m pip install --upgrade pip >nul 2>nul
echo [INFO] Installation des dépendances Python (veuillez patienter)...
pip install -r requirements.txt

:: 5. NPM DEPENDENCY HANDSHAKE
echo [INFO] Verification des modules Frontend Next.js...
cd /d "%PROJECT_DIR%\frontend"
if not exist "node_modules" (
    echo [INFO] Premier démarrage : Installation des packages Node.js...
    call npm install
)

echo.
echo ========================================================
echo       LANCEMENT DES SERVEURS - PIPELINE ACTIVE          
echo ========================================================
echo.

:: 6. EXPLICIT ASYNCHRONOUS DAEMON SPAWNING
cd /d "%PROJECT_DIR%\backend"
call venv\Scripts\activate
start "Backend_FastAPI" /b uvicorn app.main:app --port 8000

cd /d "%PROJECT_DIR%\frontend"
start "Frontend_NextJS" /b npm run dev

echo [INFO] Demarrage des interfaces en cours (4 secondes)...
timeout /t 4 /nobreak >nul

:: Launch default browser session
start http://localhost:3000

echo.
echo === TOUT EST PRET ! L'APPLICATION EST EN COURS D'EXECUTION ===
echo [CONSIGNE] Laissez cette fenetre ouverte pendant le travail.
echo [FERMETURE] Appuyez sur une touche ICI pour arreter proprement l'application.
echo ========================================================
echo.
pause

echo [INFO] Fermeture et liberation des ports systeme...
taskkill /f /fi "WINDOWTITLE eq Backend_FastAPI*" >nul 2>nul
taskkill /f /fi "WINDOWTITLE eq Frontend_NextJS*" >nul 2>nul
taskkill /f /im python.exe /t >nul 2>nul
taskkill /f /im node.exe /t >nul 2>nul
echo Termine.
exit

:CRASH_PAUSE
echo.
echo ========================================================
echo            ECHEC DE CONFIGURATION ET DE LANCEMENT
echo ========================================================
pause
exit
