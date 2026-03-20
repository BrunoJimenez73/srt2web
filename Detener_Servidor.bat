@echo off
chcp 65001 >nul 2>&1
title Detener SRT2Web

setlocal EnableDelayedExpansion

set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "WHITE=[97m"
set "RESET=[0m"

set "ERRORS_FOUND=0"
set "KILLED=0"

echo.
echo  +=============================================+
echo  ^|          DETENIENDO SRT2Web               ^|
echo  +=============================================+
echo.

echo %WHITE%[INFO]%RESET% Deteniendo servicios y limpiando puertos...
echo.

set "PORTS=9999 9000 8000"

for %%P in (%PORTS%) do (
    for /f "tokens=5" %%A in ('netstat -ano ^| findstr :%%P ^| findstr LISTENING') do (
        if "%%A" NEQ "0" (
            echo %YELLOW%[WARN]%RESET% Proceso PID %%A en puerto %%P
            taskkill /F /PID %%A >nul 2>&1
            if !errorlevel! equ 0 (
                echo %GREEN%[OK]%RESET% Proceso %%A detenido
                set "KILLED=1"
            ) else (
                echo %RED%[ERROR]%RESET% No se pudo detener %%A
                set "ERRORS_FOUND=1"
            )
        )
    )
)

echo.
echo %WHITE%[INFO]%RESET% Deteniendo FFmpeg...
for /f "tokens=2" %%A in ('tasklist /NH /FI "IMAGENAME eq ffmpeg.exe" 2^>nul ^| findstr /I "ffmpeg.exe"') do (
    taskkill /F /PID %%A >nul 2>&1
    if !errorlevel! equ 0 (
        set "KILLED=1"
    )
)
if !KILLED!==1 (
    echo %GREEN%[OK]%RESET% FFmpeg detenido
)

set "KILLED=0"
echo.
echo %WHITE%[INFO]%RESET% Deteniendo procesos Python...
for /f "tokens=2" %%A in ('tasklist /NH /FI "IMAGENAME eq python.exe" 2^>nul ^| findstr /I "python.exe"') do (
    taskkill /F /PID %%A >nul 2>&1
    if !errorlevel! equ 0 (
        set "KILLED=1"
    )
)
if !KILLED!==1 (
    echo %GREEN%[OK]%RESET% Procesos Python detenidos
)

echo.
echo %WHITE%[INFO]%RESET% Verificando puertos...
set "ALL_FREE=1"
for %%P in (%PORTS%) do (
    netstat -ano | findstr :%%P | findstr LISTENING >nul 2>&1
    if !errorlevel! equ 0 (
        echo %RED%[ERROR]%RESET% Puerto %%P aun en uso
        set "ALL_FREE=0"
        set "ERRORS_FOUND=1"
    )
)
if "!ALL_FREE!"=="1" (
    echo %GREEN%[OK]%RESET% Todos los puertos libres
)

echo.
echo %WHITE%[INFO]%RESET% Limpiando archivos temporales...

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

set "CLEANED=0"

for %%D in (chunks temp_audio temp_mix temp_tts) do (
    if exist "output\%%D" (
        for %%F in ("output\%%D\*") do (
            del /q "%%F" >nul 2>&1
            set "CLEANED=1"
        )
    )
)

for %%E in (seg_*.ts chunk_*.srt *.m3u8) do (
    if exist "output\hls\%%E" (
        del /q "output\hls\%%E" >nul 2>&1
        set "CLEANED=1"
    )
)

if exist "output\hls\subs.vtt" (
    (
        echo WEBVTT
        echo.
    ) > "output\hls\subs.vtt"
    set "CLEANED=1"
)

if "!CLEANED!"=="1" (
    echo %GREEN%[OK]%RESET% Archivos temporales limpiados
) else (
    echo %WHITE%[INFO]%RESET% No habia archivos que limpiar
)

echo.
echo  +=============================================+
if "!ERRORS_FOUND!"=="1" (
    echo %RED%[ERROR]%RESET% Algunos procesos no pudieron detenerse
) else (
    echo %GREEN%[OK]%RESET% Servidor detenido correctamente
)
echo  +=============================================+
echo.
pause
