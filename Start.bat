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
echo [OK] Iniciando servidor...
echo [INFO] Dashboard: http://localhost:9999
echo [INFO] Para detener: Stop.bat
echo.

REM Start server in new window showing logs
start "SRT2Web Server" cmd /k "cd /d "%SCRIPT_DIR%" && %PYTHON% -X utf8 main.py"
