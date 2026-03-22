@echo off
chcp 65001 >nul
title Servidor-SRT2Web
color 0a

echo ===============================================
echo            INICIANDO SRT2Web
echo ===============================================
echo.
echo [INFO] Verificando entorno de Python...
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no esta instalado o no esta en el PATH.
    echo [INFO] Por favor, instala Python desde https://python.org
    echo.
    pause
    exit /b 1
)

if not exist "main.py" (
    echo [ERROR] No se encuentra main.py en el directorio actual.
    echo [INFO] Asegurate de ejecutar este script desde la carpeta del proyecto.
    echo.
    pause
    exit /b 1
)

echo [INFO] Verificando dependencias...
if not exist "requirements.txt" (
    echo [WARNING] No se encuentra requirements.txt
) else (
    echo [INFO] Instalando/actualizando dependencias...
    python -m pip install -r requirements.txt --quiet
    if %errorlevel% neq 0 (
        echo [WARNING] No se pudieron instalar algunas dependencias
        echo [INFO] Intentando continuar de todos modos...
    )
)

echo [INFO] Checking for CUDA...
where nvcc >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] CUDA not found in PATH. Piper TTS will use CPU-only mode.
    echo [INFO] For GPU acceleration, please install CUDA and cuDNN manually:
    echo [INFO]   CUDA Toolkit: https://developer.nvidia.com/cuda-downloads
    echo [INFO]   cuDNN: https://developer.nvidia.com/rdp/cudnn-archive (requires NVIDIA developer login)
    echo [INFO] After installation, restart this script.
) else (
    echo [OK] CUDA detected.
)

echo [INFO] Checking onnxruntime-gpu for Piper TTS GPU acceleration...
python -c "import onnxruntime; print('CUDA' in str(onnxruntime.get_available_providers()))" 2>nul | findstr /C:"True" >nul
if %errorlevel% neq 0 (
    echo [INFO] onnxruntime-gpu not detected, installing...
    python -m pip install onnxruntime-gpu --quiet
    if %errorlevel% equ 0 (
        echo [OK] onnxruntime-gpu installed successfully
    ) else (
        echo [WARNING] Could not install onnxruntime-gpu, Piper will use CPU
    )
) else (
    echo [OK] onnxruntime-gpu detected, GPU available for Piper TTS
)

echo.
echo [INFO] Iniciando servidor en modo minimizado...
echo [INFO] El servidor se ejecuta en segundo plano.
echo [INFO] Para detenerlo, cierra la ventana desde la barra de tareas.
echo.
echo ===============================================
echo Servidor iniciado (minimizado)
echo ===============================================
echo.

start /min "" python -X utf8 main.py

echo [OK] Servidor iniciado exitosamente.
echo [INFO] Abre http://localhost:9999 en tu navegador.
echo.
timeout /t 3 >nul
exit /b 0</think>