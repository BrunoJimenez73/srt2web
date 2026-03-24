@echo off
chcp 65001 >nul
title Servidor-SRT2Web
color 0a

echo ===============================================
echo            INICIANDO SRT2Web
echo ===============================================
echo.

REM Check if venv exists
if not exist "venv\Scripts\python.exe" (
    echo [INFO] Entorno virtual no encontrado.
    echo [INFO] Creando entorno virtual con Python 3.12...
    
    REM Try py launcher first
    py -3.12 -m venv venv 2>nul
    if %errorlevel% neq 0 (
        REM Try direct Python 3.12 path
        if exist "C:\Users\bruno\AppData\Local\Programs\Python\Python312\python.exe" (
            C:\Users\bruno\AppData\Local\Programs\Python\Python312\python.exe -m venv venv
        ) else (
            echo [ERROR] Python 3.12 no encontrado.
            echo [INFO] Instala Python 3.12 desde: https://www.python.org/downloads/
            pause
            exit /b 1
        )
    )
    
    if %errorlevel% neq 0 (
        echo [ERROR] No se pudo crear el entorno virtual.
        pause
        exit /b 1
    )
    
    echo [OK] Entorno virtual creado.
    
    echo [INFO] Instalando dependencias...
    venv\Scripts\python.exe -m pip install --upgrade pip --quiet
    venv\Scripts\python.exe -m pip install -r requirements.txt --quiet
    if %errorlevel% neq 0 (
        echo [WARNING] Algunas dependencias fallaron, pero continuando...
    )
    echo [OK] Dependencias instaladas.
) else (
    echo [OK] Entorno virtual encontrado.
)

set PYTHON_CMD=venv\Scripts\python.exe

REM Verify venv is working
%PYTHON_CMD% --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] El entorno virtual no funciona correctamente.
    echo [INFO] Elimina la carpeta venv y vuelve a ejecutar este script.
    pause
    exit /b 1
)

REM Show Python version
for /f "tokens=2" %%v in ('%PYTHON_CMD% --version') do echo [OK] Python %%v

if not exist "main.py" (
    echo [ERROR] No se encuentra main.py en el directorio actual.
    echo [INFO] Ejecuta este script desde la carpeta del proyecto.
    pause
    exit /b 1
)

echo.
echo [INFO] ==============================================
echo [INFO] Verificando dependencias CUDA...
echo [INFO] ==============================================

REM Check nvidia-cublas
%PYTHON_CMD% -c "import nvidia.cublas" >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] nvidia-cublas-cu12 no encontrado.
    echo [INFO] Instalando...
    %PYTHON_CMD% -m pip install nvidia-cublas-cu12 --quiet
    if %errorlevel% equ 0 (
        echo [OK] nvidia-cublas-cu12 instalado.
    ) else (
        echo [ERROR] No se pudo instalar nvidia-cublas-cu12
        echo [INFO] Instala: https://pypi.org/project/nvidia-cublas-cu12/
    )
) else (
    echo [OK] nvidia-cublas-cu12
)

REM Check nvidia-cudnn
%PYTHON_CMD% -c "import nvidia.cudnn" >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] nvidia-cudnn-cu12 no encontrado.
    echo [INFO] Instalando...
    %PYTHON_CMD% -m pip install nvidia-cudnn-cu12 --quiet
    if %errorlevel% equ 0 (
        echo [OK] nvidia-cudnn-cu12 instalado.
    ) else (
        echo [ERROR] No se pudo instalar nvidia-cudnn-cu12
        echo [INFO] Instala: https://pypi.org/project/nvidia-cudnn-cu12/
    )
) else (
    echo [OK] nvidia-cudnn-cu12
)

REM Check onnxruntime GPU
%PYTHON_CMD% -c "import onnxruntime; print('CUDAExecutionProvider' in str(onnxruntime.get_available_providers()))" > temp_gpu.txt 2>nul
findstr /C:"True" temp_gpu.txt >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] ONNX Runtime con GPU para Piper TTS.
) else (
    echo [INFO] ONNX Runtime CPU para Piper TTS.
)
if exist temp_gpu.txt del temp_gpu.txt 2>nul

REM Check PyTorch CUDA
%PYTHON_CMD% -c "import torch; print(torch.cuda.is_available())" > temp_torch.txt 2>nul
findstr /C:"True" temp_torch.txt >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] PyTorch con CUDA para transcripcion.
) else (
    echo [INFO] PyTorch CPU para transcripcion.
)
if exist temp_torch.txt del temp_torch.txt 2>nul

echo.
echo [INFO] Iniciando servidor SRT2Web...
echo [INFO] Dashboard: http://localhost:9999
echo [INFO] HLS Stream: http://localhost:9999/hls/stream.m3u8
echo [INFO] Para detener: cierra esta ventana
echo.
echo ===============================================

REM Start server minimized in background
start /min "SRT2Web" %PYTHON_CMD% -X utf8 main.py

REM Wait a moment and check if server started
timeout /t 3 >nul

echo [OK] Servidor iniciado correctamente.
echo.
echo Presiona cualquier tecla para cerrar esta ventana...
pause >nul
exit /b 0
