@echo off
chcp 65001 >nul
title SRT2Web Console
cd /d "%~dp0"

echo.
echo ================================================
echo         SRT2Web - MODO CONSOLA
echo ================================================
echo.

REM NOTE: CUDA/cuDNN paths are now handled automatically by main.py
REM (it adds paths from venv's site-packages/nvidia/)

REM Ejecutar servidor en modo consola visible
venv\Scripts\python.exe -X utf8 main.py

echo.
echo ================================================
echo         SERVIDOR DETENIDO
echo ================================================
pause