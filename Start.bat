@echo off
chcp 65001 >nul
title SRT2Web - Iniciando
color 0a

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

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

echo.
echo [OK] Verificando FFmpeg...
if exist "bin\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe" (
    echo [OK] FFmpeg encontrado.
) else (
    echo [WARNING] FFmpeg no encontrado en bin/
)

echo.
echo [OK] Iniciando servidor (ventana visible para logs)...
echo.
%PYTHON% -X utf8 main.py

echo.
echo [INFO] Servidor detenido.
pause