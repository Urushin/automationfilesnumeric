@echo off
title Validateur de Lancement - Automatisation Numeric Files

echo ========================================================
echo       VERIFICATION DES COMPOSANTS SYSTEME (MODE SECURE)
echo ========================================================
echo.

:: 1. Dynamic Root Directory Capture
set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

echo [DEBUG] Racine detectee : "%PROJECT_DIR%"

:: 2. Safety Check: Verify folder structure layout
if not exist "%PROJECT_DIR%\backend" (
    echo [ERREUR CRITIQUE] Dossier 'backend' introuvable dans : "%PROJECT_DIR%"
    echo Assurez-vous que ce fichier .bat est bien PLACE A LA RACINE du projet.
    echo.
    pause
    exit
)

:: 3. Validate Python Presence
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ALERTE] Python est absent. Telechargement de l'installateur...
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile '$env:TEMP\py_setup.exe'"
    echo [ACTION] Installation de Python (Veuillez accepter l'autorisation Windows)...
    start /wait "" "%TEMP%\py_setup.exe" /quiet PrependPath=1 Include_pip=1
    echo [SUCCES] Python installe.
)

:: 4. Validate Node.js / NPM Presence
where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo [ALERTE] Node.js / NPM est absent. Telechargement de l'installateur...
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://nodejs.org/dist/v20.11.1/node-v20.11.1-x64.msi' -OutFile '$env:TEMP\node_setup.msi'"
    echo [ACTION] Installation de Node.js (Veuillez accepter l'autorisation Windows)...
    start /wait "" msiexec /i "%TEMP%\node_setup.msi" /quiet /norestart
    set "PATH=%PATH%;C:\Program Files\nodejs\"
    echo [SUCCES] Node.js installe.
)

:: Re-verify binaries natively before continuing
where python >nul 2>nul || (echo Erreur fatale verification Python. & pause & exit)
where npm >nul 2>nul || (echo Erreur fatale verification NPM. & pause & exit)

:: 5. Install Local Dependencies
echo [INFO] Synchronisation du Backend Python...
cd /d "%PROJECT_DIR%\backend"
if not exist "venv" (
    python -m venv venv
)
call venv\Scripts\activate
pip install -r requirements.txt

echo [INFO] Synchronisation du Frontend Next.js...
cd /d "%PROJECT_DIR%\frontend"
if not exist "node_modules" (
    echo Installation des packages Node.js (Cette operation peut prendre 1 a 2 minutes)...
    call npm install
)

:: 6. Launch Sequence
echo.
echo ========================================================
echo          DEMARRAGE DES SERVEURS EN COURS...
echo ========================================================
echo.

cd /d "%PROJECT_DIR%\backend"
call venv\Scripts\activate
start "Backend_FastAPI" /b uvicorn app.main:app --port 8000

cd /d "%PROJECT_DIR%\frontend"
start "Frontend_NextJS" /b npm run dev

echo Initialisation des ports reseaux (5 secondes)...
timeout /t 5 /nobreak >nul

start http://localhost:3000

echo.
echo ========================================================
echo L'APPLICATION EST ACTIVE SUR http://localhost:3000
echo.
echo IMPORTANT : LAISSEZ CETTE FENETRE OUVERTE POUR TRAVAILLER.
echo Appuyez sur une touche ICI pour fermer proprement l'application.
echo ========================================================
pause

echo Fermeture des serveurs d'arriere-plan...
taskkill /f /im python.exe /t >nul 2>nul
taskkill /f /im node.exe /t >nul 2>nul
exit
