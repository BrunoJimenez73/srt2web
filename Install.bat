@echo off
chcp 65001 >nul
title SRT2Web - Instalador
color 0f

echo.
echo ===============================================
echo            SRT2Web - INSTALADOR
echo ===============================================
echo.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

set "PYTHON=venv\Scripts\python.exe"
set "NEED_REBOOT=0"

REM =============================================
REM 1. Verificar/Crear entorno virtual
REM =============================================
echo [1/5] Entorno virtual...

if exist "%PYTHON%" (
    echo  [OK] Ya existe.
) else (
    echo  [INFO] No encontrado. Creando con Python 3.12...
    py -3.12 -m venv venv 2>nul
    if %errorlevel% neq 0 (
        if exist "C:\Python312\python.exe" (
            C:\Python312\python.exe -m venv venv
        ) else if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
            "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -m venv venv
        )
    )
    if exist "%PYTHON%" (
        echo  [OK] Entorno virtual creado.
        set "NEED_REBOOT=1"
    ) else (
        echo  [ERROR] No se pudo crear. Instala Python 3.12.
        pause
        exit /b 1
    )
)

REM =============================================
REM 2. Verificar/Instalar dependencias pip
REM =============================================
echo.
echo [2/5] Dependencias Python...

%PYTHON% -m pip install --upgrade pip --quiet 2>nul

set "DEPS_MISSING=0"
%PYTHON% -c "import fastapi" 2>nul
if %errorlevel% neq 0 set "DEPS_MISSING=1"
%PYTHON% -c "import faster_whisper" 2>nul
if %errorlevel% neq 0 set "DEPS_MISSING=1"
%PYTHON% -c "import piper" 2>nul
if %errorlevel% neq 0 set "DEPS_MISSING=1"

if "%DEPS_MISSING%"=="1" (
    echo  [INFO] Instalando dependencias desde requirements.txt...
    %PYTHON% -m pip install -r config/requirements.txt --quiet
    echo  [OK] Dependencias instaladas.
) else (
    echo  [OK] Dependencias ya instaladas.
)

REM Check onnxruntime-gpu
%PYTHON% -c "import onnxruntime; print('CUDA' if 'CUDAExecutionProvider' in onnxruntime.get_available_providers() else 'CPU')" > temp_cuda.txt 2>nul
set /p CUDA_STATUS=<temp_cuda.txt
del temp_cuda.txt 2>nul

if "%CUDA_STATUS%"=="CUDA" (
    echo  [OK] onnxruntime-gpu con CUDA.
) else (
    %PYTHON% -c "import onnxruntime" 2>nul
    if %errorlevel% equ 0 (
        echo  [INFO] onnxruntime sin CUDA. Instalando GPU...
        %PYTHON% -m pip install onnxruntime-gpu --quiet
    ) else (
        echo  [INFO] Instalando onnxruntime-gpu...
        %PYTHON% -m pip install onnxruntime-gpu --quiet
    )
)

REM Check nvidia CUDA libs
%PYTHON% -c "import nvidia.cublas" 2>nul
if %errorlevel% equ 0 (
    echo  [OK] nvidia-cublas-cu12.
) else (
    echo  [INFO] Instalando nvidia-cublas-cu12...
    %PYTHON% -m pip install nvidia-cublas-cu12 --quiet
)

%PYTHON% -c "import nvidia.cudnn" 2>nul
if %errorlevel% equ 0 (
    echo  [OK] nvidia-cudnn-cu12.
) else (
    echo  [INFO] Instalando nvidia-cudnn-cu12...
    %PYTHON% -m pip install nvidia-cudnn-cu12 --quiet
)

REM Ensure torch uses CUDA
%PYTHON% -c "import torch; print('CPU' if torch.version.cuda is None else 'CUDA')" > temp_torch_cuda.txt 2>nul
set /p TORCH_CUDA=<temp_torch_cuda.txt
del temp_torch_cuda.txt 2>nul

if "%TORCH_CUDA%"=="CPU" (
    echo  [INFO] Torch CPU detected. Installing CUDA version...
    %PYTHON% -m pip uninstall torch -y --quiet
    %PYTHON% -m pip install torch --index-url https://download.pytorch.org/whl/cu121 --quiet
    echo  [OK] Torch CUDA installed.
) else if "%TORCH_CUDA%"=="CUDA" (
    echo  [OK] Torch CUDA already installed.
) else (
    echo  [INFO] Torch not installed. Installing CUDA version...
    %PYTHON% -m pip install torch --index-url https://download.pytorch.org/whl/cu121 --quiet
    echo  [OK] Torch CUDA installed.
)

REM Ensure onnxruntime-gpu is used (remove regular onnxruntime)
%PYTHON% -c "import onnxruntime; print('gpu' if 'CUDAExecutionProvider' in onnxruntime.get_available_providers() else 'cpu')" > temp_ort_type.txt 2>nul
set /p ORT_TYPE=<temp_ort_type.txt
del temp_ort_type.txt 2>nul

if "%ORT_TYPE%"=="cpu" (
    echo  [INFO] onnxruntime CPU detected. Removing and ensuring GPU version...
    %PYTHON% -m pip uninstall onnxruntime -y --quiet
    %PYTHON% -m pip install onnxruntime-gpu --force-reinstall --quiet
    echo  [OK] onnxruntime-gpu installed.
) else (
    echo  [OK] onnxruntime GPU already available.
)

REM Remove regular onnxruntime if present (even if GPU is working)
%PYTHON% -c "import pkgutil; import sys; sys.exit(0 if pkgutil.find_loader('onnxruntime') is None else 1)" 2>nul
if %errorlevel% equ 0 (
    echo  [OK] onnxruntime regular no instalado.
) else (
    echo  [INFO] Eliminando onnxruntime regular...
    %PYTHON% -m pip uninstall onnxruntime -y --quiet
    echo  [OK] onnxruntime regular eliminado.
)


REM =============================================
REM 3. Verificar/Descargar FFmpeg
REM =============================================
echo.
echo [3/5] FFmpeg...

if exist "bin\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe" (
    echo  [OK] Ya existe en bin/.
) else if exist "bin\ffmpeg.exe" (
    echo  [OK] Ya existe en bin/.
) else (
    echo  [INFO] Descargando FFmpeg...
    if not exist "bin" mkdir bin
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip' -OutFile 'ffmpeg.zip'" 2>nul
    if exist "ffmpeg.zip" (
        powershell -Command "Expand-Archive -Path 'ffmpeg.zip' -DestinationPath 'bin' -Force" 2>nul
        del ffmpeg.zip
        echo  [OK] FFmpeg descargado.
    ) else (
        echo  [WARNING] No se pudo descargar. Descarga manual desde:
        echo            https://github.com/BtbN/FFmpeg-Builds/releases
    )
)

REM =============================================
REM 4. Verificar CUDA
REM =============================================
echo.
echo [4/5] CUDA...

%PYTHON% -c "import onnxruntime; print('CUDA' if 'CUDAExecutionProvider' in onnxruntime.get_available_providers() else 'CPU')" > temp_cuda.txt 2>nul
set /p CUDA_STATUS=<temp_cuda.txt
del temp_cuda.txt 2>nul

if "%CUDA_STATUS%"=="CUDA" (
    echo  [OK] CUDA disponible.
) else (
    echo  [INFO] CUDA no disponible (usando CPU).
)

REM =============================================
REM 5. Verificar voces Piper
REM =============================================
echo.
echo [5/5] Voces Piper...

if not exist "models\piper" mkdir models\piper

echo  [INFO] Verificando voces Piper...
%PYTHON% scripts/download_piper_voices.py
if %errorlevel% equ 0 (
    echo  [OK] Voces verificadas/descargadas.
) else (
    echo  [WARNING] Error en la descarga de voces. Se descargaran al usar Piper.
)

echo.
echo ===============================================
echo            INSTALACION COMPLETADA
echo ===============================================
echo.
if "%NEED_REBOOT%"=="1" (
    echo [INFO] Entorno virtual creado. Si hay errores, cierra y vuelve a abrir Start.bat
)
echo Para iniciar: Start.bat
echo Para detener: Stop.bat
echo.
pause
