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

REM =============================================
REM Verificar drivers NVIDIA
REM =============================================
echo [INFO] Verificando NVIDIA...
where nvidia-smi >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  [WARNING] NVIDIA drivers no detectados!
    echo.
    echo  Para usar GPU, instala los drivers NVIDIA:
    echo  1. Ve a: https://www.nvidia.com/Download/index.aspx
    echo  2. Descarga los drivers para tu GPU
    echo  3. Instala y reinicia el PC
    echo.
    echo  El servidor funcionara en modo CPU hasta entonces.
    echo.
) else (
    echo  [OK] NVIDIA drivers detectados.
)

set "PYTHON=python"

REM =============================================
REM 1. Verificar Python global
REM =============================================
echo [1/5] Verificando Python...

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python no encontrado.
    echo  Instala Python 3.12+ desde https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2" %%V in ('python --version 2^>^&1') do set "PYTHON_VERSION=%%V"
echo  [OK] Python %PYTHON_VERSION% detectado.

REM =============================================
REM 2. Instalar dependencias
REM =============================================
echo [2/5] Dependencias...

%PYTHON% -m pip install --upgrade pip wheel setuptools --quiet 2>nul

echo  [OK] Instalando dependencias del proyecto...
%PYTHON% -m pip install -r config/requirements.txt --quiet 2>nul
if %errorlevel% equ 0 (
    echo  [OK] Dependencias instaladas.
) else (
    echo  [WARNING] Error instalando dependencias.
)

REM =============================================
REM 3. Instalar PyTorch con CUDA
REM =============================================
echo.
echo [3/5] PyTorch CUDA...

%PYTHON% -c "import torch; print('CUDA' if torch.cuda.is_available() else 'CPU')" > temp_torch.txt 2>nul
set /p TORCH_STATUS=<temp_torch.txt
del temp_torch.txt 2>nul

if "%TORCH_STATUS%"=="CUDA" (
    echo  [OK] PyTorch CUDA ya instalado.
) else (
    echo  [INFO] Instalando PyTorch con CUDA 12.1...
    %PYTHON% -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 --quiet 2>nul
    if %errorlevel% equ 0 (
        echo  [OK] PyTorch CUDA instalado.
    ) else (
        echo  [WARNING] Fallback a PyTorch CPU.
    )
)

REM =============================================
REM 4. Instalar ONNX Runtime GPU (version especifica)
REM =============================================
echo.
echo [4/5] ONNX Runtime GPU...

%PYTHON% -c "import onnxruntime as ort; print('CUDA' if 'CUDAExecutionProvider' in ort.get_available_providers() else 'CPU')" > temp_onnx.txt 2>nul
set /p ONNX_STATUS=<temp_onnx.txt
del temp_onnx.txt 2>nul

if "%ONNX_STATUS%"=="CUDA" (
    echo  [OK] ONNX Runtime GPU ya disponible.
) else (
    echo  [INFO] Instalando onnxruntime-gpu 1.19.0...
    %PYTHON% -m pip install onnxruntime-gpu==1.19.0 --quiet 2>nul
    if %errorlevel% equ 0 (
        echo  [OK] ONNX Runtime GPU 1.19.0 instalado.
    ) else (
        echo  [WARNING] Fallback a CPU.
    )
)

REM =============================================
REM 5. Instalar aiortc para WebRTC
REM =============================================
echo.
echo [5/5] aiortc para WebRTC...

%PYTHON% -c "import aiortc" >nul 2>&1
if %errorlevel% equ 0 (
    echo  [OK] aiortc ya instalado.
) else (
    echo  [INFO] Instalando aiortc para WebRTC...
    %PYTHON% -m pip install aiortc --quiet 2>nul
    if %errorlevel% equ 0 (
        echo  [OK] aiortc instalado.
    ) else (
        echo  [WARNING] No se pudo instalar aiortc. WebRTC no disponible.
    )
)

REM =============================================
REM Opcional: Modelos Whisper
REM =============================================
echo.
echo [INFO] Verificando modelos Whisper...

if not exist ".cache\srt2web\whisper\models--Systran--faster-whisper-tiny" (
    echo  [INFO] Descargando modelo Whisper tiny...
    %PYTHON% -c "from faster_whisper import WhisperModel; WhisperModel('tiny', device='cpu', download_root='.cache/srt2web/whisper')" 2>nul
    if exist ".cache\srt2web\whisper\models--Systran--faster-whisper-tiny" (
        echo  [OK] Modelo Whisper tiny descargado.
    ) else (
        echo  [WARNING] No se pudo descargar el modelo.
    )
) else (
    echo  [OK] Modelo Whisper tiny ya existe.
)

REM =============================================
REM Opcional: FFmpeg con NVENC
REM =============================================
echo.
echo [INFO] Verificando FFmpeg...

if exist "bin\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe" (
    echo  [OK] FFmpeg ya existe.
    
    REM Verificar NVENC
    bin\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe -encoders 2>nul | findstr /C:"h264_nvenc" >nul 2>&1
    if %errorlevel% equ 0 (
        echo  [OK] NVENC disponible.
    ) else (
        echo  [WARNING] FFmpeg sin NVENC. Descargando...
        goto download_ffmpeg
    )
) else (
    :download_ffmpeg
    echo  [INFO] Descargando FFmpeg con NVENC...
    if not exist "bin" mkdir bin
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip' -OutFile 'bin\ffmpeg.zip'" 2>nul
    if exist "bin\ffmpeg.zip" (
        powershell -Command "Expand-Archive -Path 'bin\ffmpeg.zip' -DestinationPath 'bin' -Force" 2>nul
        del "bin\ffmpeg.zip"
        
        REM Mover archivos al nivel correcto
        if exist "bin\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe" (
            echo  [OK] FFmpeg con NVENC instalado.
        ) else (
            for /d %%F in (bin\ffmpeg-*) do (
                if exist "%%F\bin\ffmpeg.exe" (
                    move "%%F\bin\*" "bin\" >nul 2>&1
                    rmdir "%%F" /s /q 2>nul
                )
            )
        )
    ) else (
        echo  [WARNING] No se pudo descargar FFmpeg.
    )
)

REM =============================================
REM Opcional: Voces Piper
REM =============================================
echo.
echo [INFO] Verificando voces Piper...

if not exist "models\piper" mkdir models\piper

echo  [INFO] Verificando voces Piper...
%PYTHON% scripts/download_piper_voices.py 2>nul
if %errorlevel% equ 0 (
    echo  [OK] Voces verificadas.
) else (
    echo  [INFO] Se descargaran al usar Piper.
)

REM =============================================
REM Resumen
REM =============================================
echo.
echo ===============================================
echo            RESUMEN DE INSTALACION
echo ===============================================

%PYTHON% -c "import torch; print('PyTorch: ' + ('CUDA ' + torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'))" 2>nul

%PYTHON% -c "import onnxruntime as ort; print('ONNX: ' + ('GPU' if 'CUDAExecutionProvider' in ort.get_available_providers() else 'CPU'))" 2>nul

if exist "bin\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe" (
    echo FFmpeg: OK ^(NVENC^)
) else (
    echo FFmpeg: No encontrado
)

echo.
echo ===============================================
echo            INSTALACION COMPLETADA
echo ===============================================
echo.
echo Para iniciar: Start.bat
echo.
pause
