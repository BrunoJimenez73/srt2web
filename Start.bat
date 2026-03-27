@echo off
chcp 65001 >nul
title SRT2Web - Iniciando
color 0a

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo.
echo ===============================================
echo            INICIANDO SRT2Web
echo ===============================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Entorno virtual no encontrado.
    echo Ejecuta Install.bat primero.
    pause
    exit /b 1
)

set PYTHON=venv\Scripts\python.exe

%PYTHON% --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] El entorno virtual no funciona.
    pause
    exit /b 1
)

echo [OK] Verificando FFmpeg...
if exist "bin\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe" (
    echo [OK] FFmpeg encontrado.
) else (
    echo [WARNING] FFmpeg no encontrado en bin/
)

echo.
echo [OK] Iniciando servidor minimizado...
echo [INFO] Dashboard: http://localhost:9998
echo [INFO] Para detener: Stop.bat
echo.

REM Start PowerShell minimized to run server
powershell -WindowStyle Hidden -Command "Start-Process -FilePath '%PYTHON%' -ArgumentList '-X utf8', 'main.py' -WorkingDirectory '%SCRIPT_DIR%' -WindowStyle Minimized"

timeout /t 2 >nul 2>&1

echo [OK] Servidor iniciado.
exit
