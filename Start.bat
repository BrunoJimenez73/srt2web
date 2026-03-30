@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title SRT2Web - Iniciando
color 0a

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo.
echo ===============================================
echo            INICIANDO SRT2Web
echo ===============================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Entorno virtual no encontrado.
    echo Ejecuta Install.bat primero.
    pause
    exit /b 1
)

set "PYTHON=venv\Scripts\python.exe"
set "FFMPEG=bin\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"

REM =============================================
REM Verificar puerto del servidor
REM =============================================
set "PORT=8083"

REM Leer puerto del servidor de config.yaml (buscar en seccion server)
for /f "tokens=2" %%A in ('findstr /C:"  port:" config.yaml 2^>nul') do (
    set "PORT=%%A"
)
set "PORT=!PORT: =!"

echo [INFO] Puerto del servidor: !PORT!

REM =============================================
REM Verificar FFmpeg
REM =============================================
echo.
if exist "%FFMPEG%" (
    echo [OK] FFmpeg encontrado.
    
    REM Verificar NVENC
    "%FFMPEG%" -encoders 2>nul | findstr /C:"h264_nvenc" >nul 2>&1
    if !errorlevel! equ 0 (
        echo [OK] NVENC disponible ^(video GPU^)
    ) else (
        echo [WARNING] FFmpeg sin NVENC ^(CPU encoding^)
    )
) else (
    echo [WARNING] FFmpeg no encontrado en bin/
    echo [INFO] Ejecuta Install.bat para descargar.
)

REM =============================================
REM Verificar GPU
REM =============================================
echo.
"%PYTHON%" -c "import torch; print('GPU: ' + torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'GPU: No disponible')" 2>nul
"%PYTHON%" -c "import onnxruntime as ort; print('ONNX: ' + ('GPU' if 'CUDAExecutionProvider' in ort.get_available_providers() else 'CPU'))" 2>nul

REM =============================================
REM Iniciar servidor
REM =============================================
echo.
echo [OK] Iniciando servidor...
echo [INFO] Dashboard: http://localhost:!PORT!
echo [INFO] API: http://localhost:!PORT!/docs
echo.

REM Agregar bin\cuda al PATH para ONNX GPU
set "PATH=%SCRIPT_DIR%bin\cuda;%SCRIPT_DIR%bin\ffmpeg-master-latest-win64-gpl\bin;%PATH%"

REM Iniciar servidor en nueva ventana
start cmd /c "cd /d "%SCRIPT_DIR%" && "%PYTHON%" -X utf8 main.py"

REM Esperar a que arranque
timeout /t 3 >nul 2>&1

REM Verificar si el servidor esta corriendo
netstat -ano | findstr :!PORT! | findstr LISTENING >nul 2>&1
if !errorlevel! equ 0 (
    echo [OK] Servidor iniciado en puerto !PORT!
) else (
    echo [WARNING] Verificando con otro metodo...
    timeout /t 2 >nul 2>&1
    netstat -ano | findstr :!PORT! | findstr LISTENING >nul 2>&1
    if !errorlevel! equ 0 (
        echo [OK] Servidor iniciado en puerto !PORT!
    ) else (
        echo [WARNING] Servidor puede no haber arrancado. Revisa los logs.
    )
)

echo.
echo ===============================================
echo            SERVIDOR INICIADO
echo ===============================================
echo.
echo  - Dashboard: http://localhost:!PORT!
echo  - Detener: Stop.bat
echo.
echo [INFO] Presiona cualquier tecla para abrir el navegador...
pause >nul

REM Abrir navegador
start http://localhost:!PORT!
