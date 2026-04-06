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
echo [1/4] Liberando puertos...

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
echo [2/4] Deteniendo procesos...

REM FFmpeg (matar TODOS los procesos FFmpeg)
taskkill /F /IM ffmpeg.exe >nul 2>&1
taskkill /F /IM ffprobe.exe >nul 2>&1
echo  [OK] FFmpeg detenido.

REM Python del proyecto (matar TODOS los python.exe que ejecutan main.py)
wmic process where "name='python.exe' and commandline like '%%main.py%%'" call terminate >nul 2>&1
timeout /t 1 /nobreak >nul
taskkill /F /IM python.exe /FI "COMMANDLINE like %%main.py%%" >nul 2>&1
echo  [OK] Python detenido.

REM Matar cualquier proceso que siga usando el puerto 9000 y 8080
for /f "tokens=5" %%A in ('netstat -ano ^| findstr :9000 ^| findstr LISTENING') do taskkill /F /PID %%A >nul 2>&1
for /f "tokens=5" %%A in ('netstat -ano ^| findstr :8080 ^| findstr LISTENING') do taskkill /F /PID %%A >nul 2>&1
for /f "tokens=5" %%A in ('netstat -ano ^| findstr :9999 ^| findstr LISTENING') do taskkill /F /PID %%A >nul 2>&1

timeout /t 2 /nobreak >nul

REM =============================================
REM 4. Limpiar archivos temporales
REM =============================================
echo.
echo [3/4] Limpiando archivos temporales...

REM Limpiar chunks
if exist "output\chunks" (
    rmdir /s /q "output\chunks" 2>nul
    echo  [OK] Chunks limpiados.
)

REM Limpiar audio temporal
if exist "output\temp_audio" (
    rmdir /s /q "output\temp_audio" 2>nul
    echo  [OK] Audio temporal limpiado.
)

REM Limpiar mix temporal
if exist "output\temp_mix" (
    rmdir /s /q "output\temp_mix" 2>nul
    echo  [OK] Mix temporal limpiado.
)

REM Limpiar TTS temporal
if exist "output\temp_tts" (
    rmdir /s /q "output\temp_tts" 2>nul
    echo  [OK] TTS temporal limpiado.
)

REM Limpiar segmentos HLS
if exist "output\hls" (
    del /q "output\hls\seg_*.ts" 2>nul
    del /q "output\hls\*.m3u8" 2>nul
    del /q "output\hls\*.m4a" 2>nul
    del /q "output\hls\*.mp3" 2>nul
    del /q "output\hls\*.wav" 2>nul
    
    REM Reset subs.vtt
    if exist "output\hls\subs.vtt" (
        (echo WEBVTT & echo. & echo 00:00:00.000 --^> 00:00:10.000 & echo Esperando stream...) > "output\hls\subs.vtt"
    )
    echo  [OK] HLS limpiado.
)

REM Limpiar audio en output raiz
del /q "output\*.wav" 2>nul
del /q "output\*.mp3" 2>nul
del /q "output\*.m4a" 2>nul

REM Limpiar logs antiguos
del /q "server_*.log" 2>nul
del /q "server.log" 2>nul

REM LIMPIAR CACHE PYTHON COMPLETA
echo  [OK] Borrando cache __pycache__...
rmdir /s /q "__pycache__" 2>nul
rmdir /s /q "core\__pycache__" 2>nul
rmdir /s /q "modules\__pycache__" 2>nul
rmdir /s /q "server\__pycache__" 2>nul
rmdir /s /q "modules\inputs\__pycache__" 2>nul
rmdir /s /q "modules\outputs\__pycache__" 2>nul
rmdir /s /q "scripts\__pycache__" 2>nul
rmdir /s /q "tests\__pycache__" 2>nul

REM Matar TODOS los procesos python que queden abiertos
taskkill /F /IM python.exe /T 2>nul

REM =============================================
REM 5. Verificar estado final
REM =============================================
echo.
echo [4/4] Verificando...

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
pause
