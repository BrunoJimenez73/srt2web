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
REM 5. Descargar voces Piper
REM =============================================
echo.
echo [5/6] Voces Piper...

if not exist "models\piper" mkdir models\piper

REM Run the voice download script
%PYTHON% scripts\download_piper_voices.py

if exist "models\piper\*.onnx" (
    echo  [OK] Voces Piper instaladas.
) else (
    echo  [WARNING] No se encontraron voces. Se pueden descargar manualmente.
)

REM =============================================
REM 6. Verificar frontend build
REM =============================================
echo.
echo [6/6] Frontend...

if exist "server\static\index.html" (
    echo  [OK] Frontend ya construido.
) else (
    echo  [INFO] Construyendo frontend...
    if exist "frontend\package.json" (
        cd frontend
        call npm install --silent
        call npm run build:local --silent
        cd ..
        xcopy frontend\dist server\static /E /Y /I >nul 2>&1
        echo  [OK] Frontend construido.
    ) else (
        echo  [WARNING] No se encontro frontend. Asegurate de que la carpeta frontend/ existe.
    )
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
