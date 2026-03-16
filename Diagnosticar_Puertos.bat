@echo off
chcp 65001 >nul
color 0b
title Diagnosticar Puertos SRT2Web

echo ===============================================
echo        DIAGNÓSTICO DE PUERTOS SRT2Web
echo ===============================================
echo.

echo [INFO] Verificando estado de puertos críticos...
echo.

:: Puerto 8080 (Dashboard)
echo Puerto 8080 (Dashboard):
netstat -ano | findstr :8080 >nul
if %errorlevel% equ 0 (
    echo [OCUPADO] Puerto 8080 está en uso por:
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8080') do (
        if "%%a" NEQ "0" (
            echo   PID: %%a
            tasklist /FI "PID eq %%a" | findstr %%a
        )
    )
) else (
    echo [LIBRE] Puerto 8080 está disponible
)

echo.

:: Puerto 9000 (SRT Stream)
echo Puerto 9000 (Stream SRT):
netstat -ano | findstr :9000 >nul
if %errorlevel% equ 0 (
    echo [OCUPADO] Puerto 9000 está en uso por:
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :9000') do (
        if "%%a" NEQ "0" (
            echo   PID: %%a
            tasklist /FI "PID eq %%a" | findstr %%a
        )
    )
) else (
    echo [LIBRE] Puerto 9000 está disponible
)

echo.

:: Puerto 8000 (alternativo)
echo Puerto 8000 (alternativo):
netstat -ano | findstr :8000 >nul
if %errorlevel% equ 0 (
    echo [OCUPADO] Puerto 8000 está en uso por:
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000') do (
        if "%%a" NEQ "0" (
            echo   PID: %%a
            tasklist /FI "PID eq %%a" | findstr %%a
        )
    )
) else (
    echo [LIBRE] Puerto 8000 está disponible
)

echo.

:: Procesos Python relacionados
echo Procesos Python en ejecución:
tasklist /FI "IMAGENAME eq python.exe" >nul 2>&1
if %errorlevel% equ 0 (
    echo [ACTIVOS] Procesos Python encontrados:
    tasklist /FI "IMAGENAME eq python.exe" | findstr python.exe
) else (
    echo [NINGUNO] No hay procesos Python activos
)

echo.

:: Procesos FFmpeg
echo Procesos FFmpeg en ejecución:
tasklist /FI "IMAGENAME eq ffmpeg.exe" >nul 2>&1
if %errorlevel% equ 0 (
    echo [ACTIVOS] Procesos FFmpeg encontrados:
    tasklist /FI "IMAGENAME eq ffmpeg.exe" | findstr ffmpeg.exe
) else (
    echo [NINGUNO] No hay procesos FFmpeg activos
)

echo.
echo ===============================================
echo RESUMEN DEL DIAGNÓSTICO:
echo - Puerto 8080: Dashboard principal
echo - Puerto 9000: Stream SRT
echo - Puerto 8000: Dashboard alternativo
echo - Python: Procesos del servidor
echo - FFmpeg: Procesos de transcodificación
echo ===============================================
echo.
echo [INFO] Si los puertos están ocupados, usa Detener_Servidor.bat
echo [INFO] o cambia los puertos en config.yaml
echo.
pause