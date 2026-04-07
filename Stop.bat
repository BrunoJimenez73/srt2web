@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title SRT2Web - Detener
color 0c

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo.
echo ===============================================
echo            DETENIENDO SRT2Web
echo ===============================================
echo.

REM =============================================
REM 1. Leer puerto de config
REM =============================================
set "PORT=8083"

for /f "tokens=2" %%A in ('findstr /C:"  port:" config.yaml 2^>nul') do (
    set "PORT=%%A"
)
set "PORT=!PORT: =!"

echo [INFO] Puerto del servidor: !PORT!

REM =============================================
REM 2. Liberar puertos
REM =============================================
echo.
echo [1/3] Liberando puertos...

netstat -ano | findstr :!PORT! | findstr LISTENING >nul 2>&1
if !errorlevel! equ 0 (
    for /f "tokens=5" %%A in ('netstat -ano ^| findstr :!PORT! ^| findstr LISTENING') do (
        taskkill /F /PID %%A >nul 2>&1
    )
    echo  [OK] Puerto !PORT! liberado.
) else (
    echo  [INFO] Puerto !PORT! ya libre.
)

REM Puerto SRT
netstat -ano | findstr :9000 | findstr LISTENING >nul 2>&1
if !errorlevel! equ 0 (
    for /f "tokens=5" %%A in ('netstat -ano ^| findstr :9000 ^| findstr LISTENING') do (
        taskkill /F /PID %%A >nul 2>&1
    )
    echo  [OK] Puerto 9000 liberado.
) else (
    echo  [INFO] Puerto 9000 ya libre.
)

REM =============================================
REM 3. Detener procesos relacionados
REM =============================================
echo.
echo [2/3] Deteniendo procesos...

REM FFmpeg
taskkill /F /IM ffmpeg.exe >nul 2>&1
taskkill /F /IM ffprobe.exe >nul 2>&1
echo  [OK] FFmpeg detenido.

REM Python del proyecto (matar procesos que ejecutan main.py)
wmic process where "name='python.exe' and commandline like '%%main.py%%'" call terminate >nul 2>&1
taskkill /F /IM python.exe /FI "COMMANDLINE like %%main.py%%" >nul 2>&1
echo  [OK] Python detenido.

timeout /t 2 /nobreak >nul

REM =============================================
REM 4. Verificar estado final
REM =============================================
echo.
echo [3/3] Verificando...

netstat -ano | findstr :!PORT! | findstr LISTENING >nul 2>&1
if !errorlevel! neq 0 (
    echo  [OK] Puerto !PORT! libre.
) else (
    echo  [WARNING] Puerto !PORT! sigue ocupado.
)

echo.
echo ===============================================
echo            SERVIDOR DETENIDO
echo ===============================================
echo.
echo [INFO] Para una limpieza profunda, usa DeepClean.bat
echo.
pause