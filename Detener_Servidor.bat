@echo off
chcp 65001 >nul
color 0c
title Detener SRT2Web

echo ===============================================
echo            DETENIENDO SRT2Web
echo ===============================================
echo.

echo Buscando procesos por titulo de ventana...
tasklist /FI "WINDOWTITLE eq Servidor-SRT2Web*" >nul 2>&1
if %errorlevel% equ 0 (
    echo [INFO] Encontrado proceso por titulo de ventana
    taskkill /F /FI "WINDOWTITLE eq Servidor-SRT2Web*" /T >nul 2>&1
    if %errorlevel% equ 0 (
        echo [EXITO] Proceso detenido por titulo de ventana
    ) else (
        echo [INFO] No se pudo detener por titulo de ventana
    )
) else (
    echo [INFO] No se encontro proceso por titulo de ventana
)

echo.
echo Buscando procesos Python relacionados...
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" /FO TABLE ^| findstr python.exe') do (
    echo [INFO] Encontrado proceso Python con PID: %%a
    taskkill /F /PID %%a >nul 2>&1
    if %errorlevel% equ 0 (
        echo [EXITO] Proceso Python %%a detenido
    ) else (
        echo [INFO] No se pudo detener proceso Python %%a
    )
)

echo.
echo Buscando procesos en puertos criticos...

echo Buscando procesos en el puerto 9999 (Dashboard)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :9999') do (
    if "%%a" NEQ "0" (
        echo [INFO] Encontrado proceso en puerto 9999 con PID: %%a
        taskkill /F /PID %%a >nul 2>&1
        if %errorlevel% equ 0 (
            echo [EXITO] Proceso en puerto 9999 detenido
        ) else (
            echo [INFO] No se pudo detener proceso en puerto 9999
        )
    )
)

echo Buscando procesos en el puerto 9000 (Stream SRT)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :9000') do (
    if "%%a" NEQ "0" (
        echo [INFO] Encontrado proceso en puerto 9000 con PID: %%a
        taskkill /F /PID %%a >nul 2>&1
        if %errorlevel% equ 0 (
            echo [EXITO] Proceso en puerto 9000 detenido
        ) else (
            echo [INFO] No se pudo detener proceso en puerto 9000
        )
    )
)

echo Buscando procesos en el puerto 8000 (alternativo)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000') do (
    if "%%a" NEQ "0" (
        echo [INFO] Encontrado proceso en puerto 8000 con PID: %%a
        taskkill /F /PID %%a >nul 2>&1
        if %errorlevel% equ 0 (
            echo [EXITO] Proceso en puerto 8000 detenido
        ) else (
            echo [INFO] No se pudo detener proceso en puerto 8000
        )
    )
)

echo.
echo Buscando procesos FFmpeg...
tasklist /FI "IMAGENAME eq ffmpeg.exe" >nul 2>&1
if %errorlevel% equ 0 (
    echo [INFO] Encontrados procesos FFmpeg
    taskkill /F /IM ffmpeg.exe >nul 2>&1
    if %errorlevel% equ 0 (
        echo [EXITO] Procesos FFmpeg detenidos
    ) else (
        echo [INFO] No se pudieron detener procesos FFmpeg
    )
) else (
    echo [INFO] No se encontraron procesos FFmpeg
)

echo.
echo Verificando puertos liberados...
echo Puerto 9999: 
netstat -ano | findstr :9999 >nul
if %errorlevel% equ 1 (
    echo [EXITO] Puerto 9999 esta libre
) else (
    echo [ADVERTENCIA] Puerto 9999 sigue ocupado
)

echo Puerto 9000:
netstat -ano | findstr :9000 >nul
if %errorlevel% equ 1 (
    echo [EXITO] Puerto 9000 esta libre
) else (
    echo [ADVERTENCIA] Puerto 9000 sigue ocupado
)

echo.
echo ===============================================
echo Resumen de operacion:
echo - Procesos Python: Verificados y detenidos
echo - Procesos FFmpeg: Verificados y detenido  
echo - Puerto 9999: Dashboard
echo - Puerto 9000: Stream SRT
echo ===============================================
echo.
echo [INFO] El servidor y los puertos han sido liberados.
echo [INFO] Si algum puerto sigue ocupado, intenta reiniciar el sistema.
echo.
pause
