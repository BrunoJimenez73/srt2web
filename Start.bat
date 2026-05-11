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
REM Verificar GPU (usando venv)
REM =============================================
echo.
set "VENV_PYTHON=venv\Scripts\python.exe"

REM Verificar GPU con PyTorch y fallback pynvml
%VENV_PYTHON% -c "import torch; print('GPU: ' + torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'GPU: No disponible')" 2>nul
if errorlevel 1 (
    REM Fallback: verificar con pynvml si PyTorch falla
    %VENV_PYTHON% -c "import pynvml; pynvml.nvmlInit(); print('GPU: ' + pynvml.nvmlDeviceGetName(pynvml.nvmlDeviceGetHandleByIndex(0)).decode())" 2>nul || echo GPU: No disponible
)

REM Verificar ONNX GPU
%VENV_PYTHON% -c "import onnxruntime as ort; print('ONNX: ' + ('GPU' if 'CUDAExecutionProvider' in ort.get_available_providers() else 'CPU'))" 2>nul

REM =============================================
REM Iniciar servidor
REM =============================================
echo.
echo [OK] Iniciando servidor...
echo [INFO] Dashboard: http://localhost:!PORT!
echo [INFO] API: http://localhost:!PORT!/docs
echo.

REM NOTE: CUDA/cuDNN paths handled by main.py (from venv site-packages)
REM Just add FFmpeg
set "PATH=%SCRIPT_DIR%bin\ffmpeg-master-latest-win64-gpl\bin;%PATH%"

REM Iniciar servidor DIRECTAMENTE en esta consola (no en ventana oculta)
echo [INFO] Iniciando servidor en esta consola...
echo [INFO] Para detener: Ctrl+C
echo.

"%PYTHON%" -X utf8 main.py 2>&1

REM Si llegamos aqui, el servidor se cerro
set EXIT_CODE=%errorlevel%

echo.
echo ===============================================
echo            SERVIDOR DETENIDO
echo ===============================================
echo.
if %EXIT_CODE% neq 0 (
    echo [ERROR] El servidor fallo con codigo de error: %EXIT_CODE%
    echo.
    echo Verifica los logs en logs/srt2web.log para mas detalles.
) else (
    echo [OK] Servidor cerrado correctamente.
)
echo.
echo Presiona cualquier tecla para cerrar esta ventana...
pause >nul
