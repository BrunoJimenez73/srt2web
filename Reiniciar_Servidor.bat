@echo off
chcp 65001 >nul
color 0e
title Reiniciar SRT2Web

echo ===============================================
echo           REINICIANDO SRT2Web
echo ===============================================
echo.

echo [INFO] Paso 1: Deteniendo servicios existentes...
call Detener_Servidor.bat

echo.
echo [INFO] Paso 2: Iniciando servidor...
call Arrancar_Servidor.bat

echo.
echo ===============================================
echo        Reinicio completado
echo ===============================================
pause
