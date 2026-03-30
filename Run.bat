@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title SRT2Web
color 0a

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo.
echo ===============================================
echo            SRT2Web - MODO CONSOLA
echo ===============================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Entorno virtual no encontrado.
    echo Ejecuta Install.bat primero.
    pause
    exit /b 1
)

set "PYTHON=venv\Scripts\python.exe"

REM Agregar bin\cuda al PATH para ONNX GPU
set "PATH=%SCRIPT_DIR%bin\cuda;%SCRIPT_DIR%bin\ffmpeg-master-latest-win64-gpl\bin;%PATH%"

echo [INFO] Iniciando servidor...
echo [INFO] Logs se guardan en: logs\srt2web.log
echo [INFO] Para detener: Ctrl+C
echo.

REM Ejecutar servidor DIRECTAMENTE en esta consola (no en ventana nueva)
"%PYTHON%" -X utf8 main.py

REM Si llegamos aquí, el servidor terminó
echo.
echo [INFO] Servidor detenido.
pause
