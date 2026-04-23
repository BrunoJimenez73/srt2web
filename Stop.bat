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
REM 1. Configuracion
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
echo [1/5] Liberando puertos...

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

REM Puerto RTMP
netstat -ano | findstr :1935 | findstr LISTENING >nul 2>&1
if !errorlevel! equ 0 (
    for /f "tokens=5" %%A in ('netstat -ano ^| findstr :1935 ^| findstr LISTENING') do (
        taskkill /F /PID %%A >nul 2>&1
    )
    echo  [OK] Puerto 1935 liberado.
) else (
    echo  [INFO] Puerto 1935 ya libre.
)

REM =============================================
REM 3. Detener procesos
REM =============================================
echo.
echo [2/5] Deteniendo procesos...

REM FFmpeg
taskkill /F /IM ffmpeg.exe >nul 2>&1
taskkill /F /IM ffprobe.exe >nul 2>&1
echo  [OK] FFmpeg detenido.

REM Python (main.py)
wmic process where "name='python.exe' and commandline like '%%main.py%%'" call terminate >nul 2>&1
taskkill /F /IM python.exe /FI "COMMANDLINE like %%main.py%%" >nul 2>&1
taskkill /F /IM python.exe /FI "WINDOWTITLE like %%SRT2Web%%" >nul 2>&1
echo  [OK] Python detenido.

timeout /t 2 /nobreak >nul

REM =============================================
REM 4. Limpiar archivos temporales
REM =============================================
echo.
echo [3/5] Limpiando archivos temporales...

REM Directorios temporales
if exist "output\temp_audio" (
    rmdir /s /q "output\temp_audio" 2>nul
    echo  [OK] temp_audio eliminado.
) else (
    echo  [SKIP] temp_audio no existe.
)

if exist "output\temp_mix" (
    rmdir /s /q "output\temp_mix" 2>nul
    echo  [OK] temp_mix eliminado.
) else (
    echo  [SKIP] temp_mix no existe.
)

if exist "output\temp_tts" (
    rmdir /s /q "output\temp_tts" 2>nul
    echo  [OK] temp_tts eliminado.
) else (
    echo  [SKIP] temp_tts no existe.
)

REM Archivos de chunks (video extraido de OBS)
for /f "delims=" %%F in ('dir /b "output\chunk_*.wav" 2^>nul') do (
    del "output\%%F" >nul 2>&1
)
for /f "delims=" %%F in ('dir /b "output\chunk_*.vtt" 2^>nul') do (
    del "output\%%F" >nul 2>&1
)
for /f "delims=" %%F in ('dir /b "output\chunk_*.srt" 2^>nul') do (
    del "output\%%F" >nul 2>&1
)
echo  [OK] Chunk files (*.wav, *.vtt, *.srt) eliminados.

REM Archivos TTS
for /f "delims=" %%F in ('dir /b "output\tts_*.wav" 2^>nul') do (
    del "output\%%F" >nul 2>&1
)
echo  [OK] TTS files (tts_*.wav) eliminados.

REM Archivos de proceso de audio
for /f "delims=" %%F in ('dir /b "output\audio_*.wav" 2^>nul') do (
    del "output\%%F" >nul 2>&1
)
for /f "delims=" %%F in ('dir /b "output\mix_*.wav" 2^>nul') do (
    del "output\%%F" >nul 2>&1
)
echo  [OK] Audio processing files (audio_*.wav, mix_*.wav) eliminados.

REM Archivos de grabacion de audio
for /f "delims=" %%F in ('dir /b "output\rec_a_*.wav" 2^>nul') do (
    del "output\%%F" >nul 2>&1
)
echo  [OK] Recording audio files (rec_a_*.wav) eliminados.

REM Archivos de grabacion de video (HLS segments)
for /f "delims=" %%F in ('dir /b "output\seg_*.ts" 2^>nul') do (
    del "output\%%F" >nul 2>&1
)
echo  [OK] HLS segments (seg_*.ts) eliminados.

REM Archivos de grabacion de video (rec_v_*.mp4, rec_v_*.mkv)
for /f "delims=" %%F in ('dir /b "output\rec_v_*.mp4" 2^>nul') do (
    del "output\%%F" >nul 2>&1
)
for /f "delims=" %%F in ('dir /b "output\rec_v_*.mkv" 2^>nul') do (
    del "output\%%F" >nul 2>&1
)
echo  [OK] Recording video files (rec_v_*.mp4, rec_v_*.mkv) eliminados.

REM Playlists HLS antiguas (mantener solo las ultimas 2)
for /f "delims=" %%F in ('dir /b "output\master_*.m3u8" 2^>nul') do (
    del "output\%%F" >nul 2>&1
)
for /f "delims=" %%F in ('dir /b "output\stream_*.m3u8" 2^>nul') do (
    del "output\%%F" >nul 2>&1
)
echo  [OK] Old HLS playlists eliminados.

REM Archivos de subtitles temporales
for /f "delims=" %%F in ('dir /b "output\*.vtt" 2^>nul') do (
    del "output\%%F" >nul 2>&1
)
echo  [OK] Subtitle files (*.vtt) eliminados.

REM =============================================
REM 5. Limpiar logs y verificar
REM =============================================
echo.
echo [4/5] Limpiando logs...

REM Rotar logs (mantener solo 2 backups)
if exist "logs\srt2web.log.3" (
    del "logs\srt2web.log.3" >nul 2>&1
)
if exist "logs\srt2web.log.2" (
    ren "logs\srt2web.log.2" srt2web.log.3 >nul 2>&1
)
if exist "logs\srt2web.log.1" (
    ren "logs\srt2web.log.1" srt2web.log.2 >nul 2>&1
)
if exist "logs\srt2web.log" (
    ren "logs\srt2web.log" srt2web.log.1 >nul 2>&1
)
echo  [OK] Logs rotados.

REM =============================================
REM 6. Verificacion final
REM =============================================
echo.
echo [5/5] Verificando...

REM Contar archivos restantes
set "REMAINING=0"
for %%F in ("output\chunk_*.wav" "output\chunk_*.vtt" "output\tts_*.wav" "output\audio_*.wav" "output\mix_*.wav" "output\rec_a_*.wav" "output\seg_*.ts") do (
    if exist "output\%%F" (
        for /f %%A in ('dir /b "output\%%F" 2^>nul ^| find /c /v ""') do (
            set /a REMAINING+=%%A
        )
    )
)

if !REMAINING! equ 0 (
    echo  [OK] No quedan archivos temporales.
) else (
    echo  [WARNING] !REMAINING! archivos restantes.
)

REM Verificar puertos
netstat -ano | findstr :!PORT! | findstr LISTENING >nul 2>&1
if !errorlevel! neq 0 (
    echo  [OK] Puerto !PORT! libre.
) else (
    echo  [WARNING] Puerto !PORT! sigue ocupado.
)

echo.
echo ===============================================
echo            SERVIDOR DETENIDO
echo            LIMPIEZA COMPLETADA
echo ===============================================
echo.
pause