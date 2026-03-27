@echo off
chcp 65001 >nul
title SRT2Web - Detener

echo.
echo ===============================================
echo            DETENIENDO SRT2Web
echo ===============================================
echo.

powershell -Command "Write-Host '[INFO] Liberando puertos...' -ForegroundColor White"

netstat -ano | findstr :9998 | findstr LISTENING >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=5" %%A in ('netstat -ano ^| findstr :9998 ^| findstr LISTENING') do (
        taskkill /F /PID %%A >nul 2>&1
        powershell -Command "Write-Host '  [OK] Puerto 9998 liberado.' -ForegroundColor Green"
    )
) else (
    powershell -Command "Write-Host '  [INFO] Puerto 9998 ya libre.' -ForegroundColor White"
)

netstat -ano | findstr :9000 | findstr LISTENING >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=5" %%A in ('netstat -ano ^| findstr :9000 ^| findstr LISTENING') do (
        taskkill /F /PID %%A >nul 2>&1
        powershell -Command "Write-Host '  [OK] Puerto 9000 liberado.' -ForegroundColor Green"
    )
) else (
    powershell -Command "Write-Host '  [INFO] Puerto 9000 ya libre.' -ForegroundColor White"
)

echo.
powershell -Command "Write-Host '[INFO] Deteniendo procesos...' -ForegroundColor White"

taskkill /F /IM ffmpeg.exe >nul 2>&1
powershell -Command "Write-Host '  [OK] FFmpeg detenido.' -ForegroundColor Green"

taskkill /F /IM python.exe >nul 2>&1
powershell -Command "Write-Host '  [OK] Python detenido.' -ForegroundColor Green"

echo.
powershell -Command "Write-Host '[INFO] Limpiando archivos...' -ForegroundColor White"

if exist output\temp_audio rmdir /s /q output\temp_audio
if exist output\temp_mix rmdir /s /q output\temp_mix
if exist output\temp_tts rmdir /s /q output\temp_tts
if exist output\chunks rmdir /s /q output\chunks
if exist output\hls\seg_*.ts del /q output\hls\seg_*.ts
if exist output\hls\*.m3u8 del /q output\hls\*.m3u8
if exist output\hls\*.m4a del /q output\hls\*.m4a
if exist output\hls\*.mp3 del /q output\hls\*.mp3
if exist output\hls\*.wav del /q output\hls\*.wav
if exist output\hls\subs.vtt (
    (echo WEBVTT & echo. & echo 00:00:00.000 --^> 00:00:10.000 & echo Esperando stream...) > output\hls\subs.vtt
)
if exist output\*.wav del /q output\*.wav
if exist output\*.mp3 del /q output\*.mp3

powershell -Command "Write-Host '  [OK] Archivos limpiados.' -ForegroundColor Green"

echo.
echo ===============================================
powershell -Command "Write-Host '            SERVIDOR DETENIDO' -ForegroundColor Green"
echo ===============================================
echo.
pause
