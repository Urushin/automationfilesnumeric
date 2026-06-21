@echo off
setlocal enabledelayedexpansion

:: 1. Initialisation immediate du fichier de log local
set "LOG_FILE=%~dp0\diagnostic_log.txt"
echo [START] Execution du script de diagnostic > "%LOG_FILE%"
echo [TIME] %DATE% %TIME% >> "%LOG_FILE%"

:: 2. Capture de la racine
set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
echo [LOG] Dossier racine detecte: %PROJECT_DIR% >> "%LOG_FILE%"

echo ========================================================
echo            RECHERCHE FORCEE DES ERREURS SYSTEME         
echo ========================================================
echo.
echo Les etapes sont ecrites en temps reel dans :
echo diagnostic_log.txt
echo.

:: 3. Test structurel du dossier backend
echo [LOG] Verification du dossier backend... >> "%LOG_FILE%"
if not exist "%PROJECT_DIR%\backend" (
    echo [CRITICAL] Dossier backend introuvable >> "%LOG_FILE%"
    echo ERREUR: Le dossier backend est introuvable.
    pause
    exit
)

:: 4. Test structurel du dossier frontend
echo [LOG] Verification du dossier frontend... >> "%LOG_FILE%"
if not exist "%PROJECT_DIR%\frontend" (
    echo [CRITICAL] Dossier frontend introuvable >> "%LOG_FILE%"
    echo ERREUR: Le dossier frontend est introuvable.
    pause
    exit
)

:: 5. Verification de Python
echo [LOG] Verification de la commande python... >> "%LOG_FILE%"
where python >nul 2>nul
echo [LOG] Code de retour Python: %errorlevel% >> "%LOG_FILE%"
if %errorlevel% neq 0 (
    echo [ALERTE] Python absent du PATH. Tentative de telechargement... >> "%LOG_FILE%"
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile '$env:TEMP\py_setup.exe'" >> "%LOG_FILE%" 2>&1
    echo [ACTION] Lancement de l'installateur Python... >> "%LOG_FILE%"
    start /wait "" "%TEMP%\py_setup.exe" /quiet PrependPath=1 Include_pip=1
)

:: 6. Verification de NPM
echo [LOG] Verification de la commande npm... >> "%LOG_FILE%"
where npm >nul 2>nul
echo [LOG] Code de retour NPM: %errorlevel% >> "%LOG_FILE%"
if %errorlevel% neq 0 (
    echo [ALERTE] NPM absent. Tentative de telechargement de Node.js... >> "%LOG_FILE%"
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://nodejs.org/dist/v20.11.1/node-v20.11.1-x64.msi' -OutFile '$env:TEMP\node_setup.msi'" >> "%LOG_FILE%" 2>&1
    echo [ACTION] Lancement de l'installateur Node.msi... >> "%LOG_FILE%"
    start /wait "" msiexec /i "%TEMP%\node_setup.msi" /quiet /norestart
    set "PATH=%PATH%;C:\Program Files\nodejs\"
)

:: 7. Synchronisation des dependances Backend
echo [LOG] Navigation vers backend... >> "%LOG_FILE%"
cd /d "%PROJECT_DIR%\backend" >> "%LOG_FILE%" 2>&1
if not exist "venv" (
    echo [LOG] Creation de venv... >> "%LOG_FILE%"
    python -m venv venv >> "%LOG_FILE%" 2>&1
)
echo [LOG] Activation de venv... >> "%LOG_FILE%"
call venv\Scripts\activate >> "%LOG_FILE%" 2>&1
echo [LOG] Installation des packages PIP... >> "%LOG_FILE%"
pip install -r requirements.txt >> "%LOG_FILE%" 2>&1

:: 8. Synchronisation des dependances Frontend
echo [LOG] Navigation vers frontend... >> "%LOG_FILE%"
cd /d "%PROJECT_DIR%\frontend" >> "%LOG_FILE%" 2>&1
if not exist "node_modules" (
    echo [LOG] Execution de npm install... >> "%LOG_FILE%"
    call npm install >> "%LOG_FILE%" 2>&1
)

:: 9. Demarrage des processus
echo [LOG] Demarrage des serveurs... >> "%LOG_FILE%"
cd /d "%PROJECT_DIR%\backend"
call venv\Scripts\activate
start "Backend_FastAPI" /b uvicorn app.main:app --port 8000 >> "%LOG_FILE%" 2>&1

cd /d "%PROJECT_DIR%\frontend"
start "Frontend_NextJS" /b npm run dev >> "%LOG_FILE%" 2>&1

echo [LOG] Attente de 5 secondes... >> "%LOG_FILE%"
timeout /t 5 /nobreak >nul

echo [LOG] Ouverture du navigateur... >> "%LOG_FILE%"
start http://localhost:3000 >> "%LOG_FILE%" 2>&1

echo [SUCCESS] Script arrive au bout. >> "%LOG_FILE%"
echo Application active. Appuyez sur une touche pour stopper.
pause

echo [LOG] Arret des processus... >> "%LOG_FILE%"
taskkill /f /im python.exe /t >nul 2>nul
taskkill /f /im node.exe /t >nul 2>nul
echo [END] Fin de session >> "%LOG_FILE%"
exit
