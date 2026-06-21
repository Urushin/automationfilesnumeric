@echo off
setlocal enabledelayedexpansion
title Configurator Auto-Heal - Automatisation Numeric Files

echo ========================================================
echo       VERIFICATION ET AUTO-INSTALLATION DES COMPOSANTS
echo ========================================================
echo.

set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

:: -------------------------------------------------------------------
:: 1. PYTHON CHECK & AUTO-INSTALLER
:: -------------------------------------------------------------------
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ALERTE] Python est introuvable sur cette machine.
    echo [ACTION] Telechargement et installation silencieuse de Python en cours...
    
    set "PY_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
    set "PY_EXE=%TEMP%\python_installer.exe"
    
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object System.Net.WebClient).DownloadFile('!PY_URL!', '!PY_EXE!')"
    
    echo [ACTION] Execution de l'installateur Python (Veuillez valider l'autorisation Windows)...
    start /wait "" "!PY_EXE!" /quiet PrependPath=1 Include_test=0 Include_pip=1
    
    :: Refresh PATH for the current session
    refreshenv >nul 2>nul || set "PATH=%PATH%;%PrependPath%"
    echo [SUCCES] Python a ete configure.
    echo.
)

:: -------------------------------------------------------------------
:: 2. NODE.JS / NPM CHECK & AUTO-INSTALLER
:: -------------------------------------------------------------------
where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo [ALERTE] Node.js / NPM est introuvable sur cette machine.
    echo [ACTION] Telechargement de l'installateur officiel de Node.js...
    
    set "NODE_URL=https://nodejs.org/dist/v20.11.1/node-v20.11.1-x64.msi"
    set "NODE_MSI=%TEMP%\node_installer.msi"
    
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object System.Net.WebClient).DownloadFile('!NODE_URL!', '!NODE_MSI!')"
    
    echo [ACTION] Installation de Node.js en arriere-plan (Ecran de validation Windows)...
    start /wait "" msiexec /i "!NODE_MSI!" /quiet /norestart
    
    echo [SUCCES] Node.js installe. Re-routage des variables systeme...
    :: Manually inject default Node installation paths into current batch context
    set "PATH=%PATH%;C:\Program Files\nodejs\"
    echo.
)

:: Double check execution tokens before proceeding to directory validation
where python >nul 2>nul || goto CRASH_PAUSE
where npm >nul 2>nul || goto CRASH_PAUSE

echo [SUCCES] Tous les frameworks systemes sont opérationnels.
echo [INFO] Passage a la synchronisation des modules locaux...
echo.

:: -------------------------------------------------------------------
:: 3. CONTINUITY PIPELINE (VENV & NPM INSTALL)
:: -------------------------------------------------------------------
cd /d "%PROJECT_DIR%\backend"
if not exist "venv" (
    python -m venv venv
)
call venv\Scripts\activate
pip install -r requirements.txt

cd /d "%PROJECT_DIR%\frontend"
if not exist "node_modules" (
    echo [INFO] Installation des modules Next.js (Operation longue au premier démarrage)...
    call npm install
)

echo.
echo ========================================================
echo       LANCEMENT DE L'APPLICATION - TOUT EST PRET        
echo ========================================================
echo.

cd /d "%PROJECT_DIR%\backend"
call venv\Scripts\activate
start "Backend_FastAPI" /b uvicorn app.main:app --port 8000

cd /d "%PROJECT_DIR%\frontend"
start "Frontend_NextJS" /b npm run dev

timeout /t 5 /nobreak >nul
start http://localhost:3000

echo L'application est active. Appuyez sur une touche pour tout couper.
pause

taskkill /f /im python.exe /t >nul 2>nul
taskkill /f /im node.exe /t >nul 2>nul
exit

:CRASH_PAUSE
echo.
echo ========================================================
echo   [ERREUR] L'AUTO-INSTALLATEUR N'A PAS PU TOUT CONFIGURER
echo ========================================================
echo Veuillez redemarrer le script en mode Administrateur (Clic droit > Executer en tant qu'administrateur).
pause
exit
