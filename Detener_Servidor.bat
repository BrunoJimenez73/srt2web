@echo off
chcp 65001 >nul 2>&1
title Detener SRT2Web

setlocal EnableDelayedExpansion

set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "WHITE=[97m"
set "RESET=[0m"

echo.
echo  +=============================================+
echo  ^|          DETENIENDO SRT2Web               ^|
echo  +=============================================+
echo.

echo %WHITE%[INFO]%RESET% Deteniendo todos los procesos relacionados...
echo.

REM Kill FFmpeg first
echo %WHITE%[INFO]%RESET% Matando FFmpeg...
taskkill /F /IM ffmpeg.exe 2>nul
if !errorlevel!==0 (
    echo %GREEN%[OK]%RESET% FFmpeg detenido
) else (
    echo %WHITE%[INFO]%RESET% No habia FFmpeg corriendo
)
timeout /t 1 /nobreak >nul

REM Kill Python processes
echo %WHITE%[INFO]%RESET% Matando procesos Python...
taskkill /F /IM python.exe 2>nul
if !errorlevel!==0 (
    echo %GREEN%[OK]%RESET% Python detenido
) else (
    echo %WHITE%[INFO]%RESET% No habia Python corriendo
)
timeout /t 1 /nobreak >nul

REM Also kill pythonw if any
taskkill /F /IM pythonw.exe 2>nul

REM Check for processes on our ports and kill them
set "PORTS=9999 9000 8000"

echo.
echo %WHITE%[INFO]%RESET% Verificando puertos...
for %%P in (%PORTS%) do (
    echo Verificando puerto %%P...
    for /f "tokens=5" %%A in ('netstat -ano ^| findstr :%%P ^| findstr LISTENING') do (
        if "%%A" NEQ "0" (
            echo %YELLOW%[WARN]%RESET% Matando proceso PID %%A en puerto %%P
            taskkill /F /PID %%A 2>nul
            timeout /t 1 /nobreak >nul
        )
    )
)

REM Double check FFmpeg is dead
echo.
echo %WHITE%[INFO]%RESET% Verificando FFmpeg...
tasklist /NH /FI "IMAGENAME eq ffmpeg.exe" 2>nul | findstr /I "ffmpeg.exe" >nul
if !errorlevel!==0 (
    echo %YELLOW%[WARN]%RESET% FFmpeg aun corriendo, forzando muerte...
    taskkill /F /IM ffmpeg.exe /T 2>nul
    timeout /t 2 /nobreak >nul
)

REM Verify ports are free
echo.
echo %WHITE%[INFO]%RESET% Verificando que puertos estan libres...
set "ALL_FREE=1"
for %%P in (%PORTS%) do (
    netstat -ano | findstr :%%P | findstr LISTENING >nul 2>&1
    if !errorlevel!==0 (
        echo %RED%[ERROR]%RESET% Puerto %%P aun en uso
        for /f "tokens=5" %%A in ('netstat -ano ^| findstr :%%P ^| findstr LISTENING') do (
            echo %RED%[ERROR]%RESET% Matando PID %%A que ocupa %%P
            taskkill /F /PID %%A 2>nul
        )
        set "ALL_FREE=0"
    ) else (
        echo %GREEN%[OK]%RESET% Puerto %%P libre
    )
)

REM Clean temp files
echo.
echo %WHITE%[INFO]%RESET% Limpiando archivos temporales...

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Clean output directories
for %%D in (chunks temp_audio temp_mix temp_tts) do (
    if exist "output\%%D" (
        echo Limpiando output\%%D\...
        del /q /f "output\%%D\*" 2>nul
        for %%F in ("output\%%D\*") do (
            del /q /f "%%F" 2>nul
        )
    )
)

REM Clean HLS files
if exist "output\hls" (
    echo Limpiando output\hls\...
    del /q /f "output\hls\seg_*.ts" 2>nul
    del /q /f "output\hls\chunk_*.srt" 2>nul
    del /q /f "output\hls\*.m3u8" 2>nul
)

REM Reset VTT file
if exist "output\hls\subs.vtt" (
    (
        echo WEBVTT
        echo.
    ) > "output\hls\subs.vtt"
)

REM Reset playlist
if exist "output\hls\stream.m3u8" (
    (
        echo #EXTM3U
        echo #EXT-X-VERSION:3
        echo #EXT-X-TARGETDURATION:10
        echo #EXT-X-MEDIA-SEQUENCE:0
        echo #EXT-X-PLAYLIST-TYPE:EVENT
        echo #EXT-X-ENDLIST
    ) > "output\hls\stream.m3u8"
)

echo %GREEN%[OK]%RESET% Archivos temporales limpiados

echo.
echo  +=============================================+
echo %GREEN%[OK]%RESET% Servidor detenido correctamente
echo  +=============================================+
echo.
pause
