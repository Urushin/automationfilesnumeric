@echo off
:: Enable local variable scope to prevent environmental leaking
setlocal enabledelayedexpansion
title DEBUGMODE - Lancement Automatisation Numeric Files

echo ========================================================
echo        DIAGNOSTIC DE LANCEMENT DE L'APPLICATION         
echo ========================================================
echo.

:: ENCLOSE THE ABSOLUTE PATH SAFELY IN DOUBLE QUOTES TO HANDLE SPACES ("Projets perso")
set "PROJECT_DIR=C:\Users\issam\Documents\Projets perso\AutomatisationNumericFiles"

echo [DEBUG] Verification du dossier racine...
if not exist "%PROJECT_DIR%" (
    echo [CRITICAL] Le dossier specifie n'existe pas : "%PROJECT_DIR%"
    echo Veuillez verifier la lettre du lecteur ou le nom exact du chemin.
    goto CRASH_PAUSE
)

cd /d "%PROJECT_DIR%"
if %errorlevel% neq 0 (
    echo [CRITICAL] Impossible d'acceder au dossier : "%PROJECT_DIR%"
    goto CRASH_PAUSE
)

echo [DEBUG] Verification du binaire Python...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [CRITICAL] Python n'est pas installe ou n'est pas ajoute au PATH de Windows.
    echo Cochez absolument l'option "Add python.exe to PATH" lors de l'installation de Python.
    goto CRASH_PAUSE
)

echo [DEBUG] Verification du binaire NPM...
where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo [CRITICAL] Node.js / NPM est introuvable dans les variables d'environnement.
    goto CRASH_PAUSE
)

:: Keep the rest of your self-healing installation layers below but catch any error code:
echo [DEBUG] Configuration valide. Passage au chargement des modules...
goto CONTINUE_EXECUTION

:CRASH_PAUSE
echo.
echo ========================================================
echo   [ECHEC] LE SCRIPT A RECONTRE UNE ERREUR SYSTEME FATALE
echo ========================================================
echo Lisez le rapport ci-dessus pour resoudre le probleme.
pause
exit

:CONTINUE_EXECUTION
:: 3. Setup and sync Python Virtual Environment silently to install missing modules
cd /d "%PROJECT_DIR%\backend"
if not exist "venv" (
    echo [INFO] Creation de l'environnement virtuel Python (venv)...
    python -m venv venv
)
echo [INFO] Activation de l'environnement virtuel...
call "venv\Scripts\activate"

echo [INFO] Verification et installation des packages Python (Pip)...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt

:: 4. Check for Node.js / NPM and sync Frontend dependencies
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
call "venv\Scripts\activate"
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
