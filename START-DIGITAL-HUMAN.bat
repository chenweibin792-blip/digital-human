@echo off
setlocal
title DIGITAL-HUMAN

set "PROJECT_DIR=%~dp0"
set "ENV_DIR=E:\Anaconda\envs\DIGITAL-HUMAN"
set "PYTHON=%ENV_DIR%\python.exe"
set "PORT=8010"
set "URL=http://127.0.0.1:%PORT%/index.html"

if not exist "%PYTHON%" (
    echo [ERROR] DIGITAL-HUMAN environment was not found:
    echo %PYTHON%
    echo.
    pause
    exit /b 1
)

if not exist "%PROJECT_DIR%models\wav2lip.pth" (
    echo [ERROR] Missing model: models\wav2lip.pth
    echo.
    pause
    exit /b 1
)

if not exist "%PROJECT_DIR%data\avatars\wav2lip256_avatar1\coords.pkl" (
    echo [ERROR] Missing avatar: wav2lip256_avatar1
    echo.
    pause
    exit /b 1
)

powershell.exe -NoProfile -Command ^
    "if (Get-NetTCPConnection -LocalPort %PORT% -State Listen -ErrorAction SilentlyContinue) { exit 1 }"
if errorlevel 1 (
    echo [INFO] Port %PORT% is already active. Opening the existing service.
    start "" "%URL%"
    echo.
    pause
    exit /b 0
)

set "PATH=%ENV_DIR%;%ENV_DIR%\Scripts;%ENV_DIR%\Library\bin;%PATH%"
set "TEMP=E:\SZR\.tmp"
set "TMP=E:\SZR\.tmp"
set "PIP_CACHE_DIR=E:\SZR\.cache\pip"
set "HF_HOME=E:\SZR\.cache\huggingface"

if not exist "%TEMP%" mkdir "%TEMP%"
if not exist "%HF_HOME%" mkdir "%HF_HOME%"

cd /d "%PROJECT_DIR%"

echo ========================================
echo   Starting DIGITAL-HUMAN in CPU mode
echo   URL: %URL%
echo   Press Ctrl+C to stop
echo ========================================
echo.

start "" /b powershell.exe -NoProfile -WindowStyle Hidden -Command ^
    "Start-Sleep -Seconds 8; Start-Process '%URL%'"

"%PYTHON%" app.py ^
    --transport webrtc ^
    --model wav2lip ^
    --avatar_id wav2lip256_avatar1 ^
    --tts edgetts ^
    --listenport %PORT% ^
    --host 127.0.0.1

set "EXIT_CODE=%ERRORLEVEL%"
echo.
if not "%EXIT_CODE%"=="0" echo [ERROR] Service exited with code %EXIT_CODE%.
echo Service stopped.
pause
exit /b %EXIT_CODE%
