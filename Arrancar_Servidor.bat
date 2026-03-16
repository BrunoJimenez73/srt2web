@echo off
title Servidor-SRT2Web
echo ===============================================
echo            INICIANDO SRT2Web
echo ===============================================
echo.
echo [INFO] El servidor se esta ejecutando.
echo [INFO] Para detener el servidor de forma manual, simplemente CIERRA esta ventana.
echo.

python main.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Hubo un problema al iniciar el servidor.
    echo [INFO] Asegurate de tener Python instalado y las dependencias de "requirements.txt".
    echo.
    pause
)
