@echo off
title Configuration et Lancement - Automatisation Numeric Files
echo ========================================================
echo   VERIFICATION ET INSTALLATION DES DEPENDANCES WINDOWS  
echo ========================================================
echo.

:: 1. Isolate the absolute project base directory
set "PROJECT_DIR=C:\Users\issam\Documents\Projets perso\AutomatisationNumericFiles"
cd /d "%PROJECT_DIR%"

:: 2. Check for Python installation and repair execution mapping
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERREUR] Python n'est pas installe ou n'est pas dans le PATH de Windows.
    echo Veuillez installer Python depuis le Microsoft Store ou python.org avant de continuer.
    pause
    exit
)

:: 3. Setup and sync Python Virtual Environment silently to install missing modules
cd /d "%PROJECT_DIR%\backend"
if not exist "venv" (
    echo [INFO] Creation de l'environnement virtuel Python (venv)...
    python -m venv venv
)
echo [INFO] Activation de l'environnement virtuel...
call venv\Scripts\activate

echo [INFO] Verification et installation des packages Python (Pip)...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt

:: 4. Check for Node.js / NPM and sync Frontend dependencies
where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERREUR] Node.js / NPM n'est pas installe. 
    echo Veuillez installer Node.js depuis nodejs.org pour executer l'application.
    pause
    exit
)

cd /d "%PROJECT_DIR%\frontend"
if not exist "node_modules" (
    echo [INFO] Premier lancement detecte : Installation des modules Next.js...
    call npm install
)

:: 5. Asynchronous dual-server boot sequence using explicit Windows commands
echo.
echo ========================================================
echo      LANCEMENT DE L'APPLICATION (NE PAS FERMER)         
echo ========================================================
echo.

cd /d "%PROJECT_DIR%\backend"
call venv\Scripts\activate
start "Backend_FastAPI" /b uvicorn app.main:app --port 8000

cd /d "%PROJECT_DIR%\frontend"
start "Frontend_NextJS" /b npm run dev

echo [INFO] Initialisation des serveurs en cours (4 secondes)...
timeout /t 4 /nobreak >nul

:: Launch the default browser
start http://localhost:3000

echo.
echo === APPLICATION COMPLETE ET ACTIVE ===
echo Pour arreter proprement les serveurs, appuyez sur une touche ICI.
echo ========================================================
echo.
pause

:: Clean up process memory to unlock locked ports (3000 and 8000)
echo [INFO] Fermeture propre des serveurs en arriere-plan...
taskkill /f /fi "WINDOWTITLE eq Backend_FastAPI*" >nul 2>nul
taskkill /f /fi "WINDOWTITLE eq Frontend_NextJS*" >nul 2>nul
taskkill /f /im python.exe /t >nul 2>nul
taskkill /f /im node.exe /t >nul 2>nul
echo Appareil nettoye. Fermeture de la fenetre.
exit
