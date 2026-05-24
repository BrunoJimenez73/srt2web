@echo off
setlocal enabledelayedexpansion
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
REM 2. Crear entorno virtual si no existe
REM =============================================
echo [2/6] Entorno virtual...

if not exist "venv\Scripts\python.exe" (
    echo  [INFO] Creando entorno virtual...
    python -m venv venv
    if exist "venv\Scripts\python.exe" (
        echo  [OK] Entorno virtual creado.
    ) else (
        echo  [ERROR] No se pudo crear el entorno virtual.
        pause
        exit /b 1
    )
) else (
    echo  [OK] Entorno virtual ya existe.
)

REM Activar venv para instalaciones
set "VENV_PYTHON=venv\Scripts\python.exe"

REM =============================================
REM 3. Asegurar pip en venv (por si se creo sin pip)
REM =============================================
echo [3/6] Verificando pip...

%VENV_PYTHON% -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [INFO] pip no encontrado, instalando...
    %VENV_PYTHON% -m ensurepip --upgrade 2>nul
    %VENV_PYTHON% -m pip install --upgrade pip 2>nul
)

REM =============================================
REM 4. Instalar dependencias en venv
REM =============================================
echo [4/6] Dependencias...

%VENV_PYTHON% -m pip install --upgrade pip wheel setuptools --quiet 2>nul

echo  [OK] Instalando dependencias del proyecto...
REM Instalar sin onnxruntime para evitar conflicto con GPU
%VENV_PYTHON% -m pip install -r config/requirements.txt --quiet --ignore-installed 2>nul
if %errorlevel% equ 0 (
    echo  [OK] Dependencias instaladas.
) else (
    echo  [WARNING] Error instalando dependencias.
)

REM IMPORTANTE: Reinstalar ONNX GPU después de requirements para evitar que CPU lo sobreescriba
echo  [INFO] Asegurando ONNX Runtime GPU...
%VENV_PYTHON% -m pip install onnxruntime-gpu==1.19.0 --force-reinstall --quiet 2>nul

REM =============================================
REM 5. Instalar PyTorch con CUDA
REM =============================================
echo.
echo [4/6] PyTorch CUDA...

%VENV_PYTHON% -c "import torch; print('CUDA' if torch.cuda.is_available() else 'CPU')" > temp_torch.txt 2>nul
set /p TORCH_STATUS=<temp_torch.txt
del temp_torch.txt 2>nul

if "%TORCH_STATUS%"=="CUDA" (
    echo  [OK] PyTorch CUDA ya instalado.
) else (
    echo  [INFO] Instalando PyTorch con CUDA 12.1...
    %VENV_PYTHON% -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 --quiet 2>nul
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
echo [5/6] ONNX Runtime GPU...

%VENV_PYTHON% -c "import onnxruntime as ort; print('CUDA' if 'CUDAExecutionProvider' in ort.get_available_providers() else 'CPU')" > temp_onnx.txt 2>nul
set /p ONNX_STATUS=<temp_onnx.txt
del temp_onnx.txt 2>nul

if "%ONNX_STATUS%"=="CUDA" (
    echo  [OK] ONNX Runtime GPU ya disponible.
) else (
    echo  [INFO] Instalando onnxruntime-gpu 1.19.0...
    %VENV_PYTHON% -m pip install onnxruntime-gpu==1.19.0 --quiet 2>nul
    if %errorlevel% equ 0 (
        echo  [OK] ONNX Runtime GPU 1.19.0 instalado.
    ) else (
        echo  [WARNING] Fallback a CPU.
    )
)

REM =============================================
REM 5b. Instalar pynvml para monitoreo de GPU
REM =============================================
echo.
echo [INFO] Verificando pynvml para monitoreo GPU...

%VENV_PYTHON% -c "import pynvml; print('OK')" >nul 2>&1
if %errorlevel% equ 0 (
    echo  [OK] pynvml ya instalado.
) else (
    echo  [INFO] Instalando pynvml...
    %VENV_PYTHON% -m pip install nvidia-ml-py --quiet 2>nul
    if %errorlevel% equ 0 (
        echo  [OK] pynvml instalado.
    ) else (
        echo  [WARNING] No se pudo instalar pynvml.
    )
)

REM =============================================
REM 6. Instalar aiortc para WebRTC
REM =============================================
echo.
echo [6/6] aiortc para WebRTC...

%VENV_PYTHON% -c "import aiortc" >nul 2>&1
if %errorlevel% equ 0 (
    echo  [OK] aiortc ya instalado.
) else (
    echo  [INFO] Instalando aiortc para WebRTC...
    %VENV_PYTHON% -m pip install aiortc --quiet 2>nul
    if %errorlevel% equ 0 (
        echo  [OK] aiortc instalado.
    ) else (
        echo  [WARNING] No se pudo instalar aiortc. WebRTC no disponible.
    )
)

REM =============================================
REM Opcional: Modelos Whisper (tiny + medium + large-v3)
REM =============================================
echo.
echo [INFO] Verificando modelos Whisper...

REM tiny (base)
if not exist ".cache\srt2web\whisper\models--Systran--faster-whisper-tiny" (
    echo  [INFO] Descargando modelo Whisper tiny...
    %VENV_PYTHON% -c "from faster_whisper import WhisperModel; WhisperModel('tiny', device='cpu', download_root='.cache/srt2web/whisper')" 2>nul
    if exist ".cache\srt2web\whisper\models--Systran--faster-whisper-tiny" (
        echo  [OK] Modelo Whisper tiny descargado.
    ) else (
        echo  [WARNING] No se pudo descargar tiny.
    )
) else (
    echo  [OK] Whisper tiny ya existe.
)

REM medium (better quality)
if not exist ".cache\srt2web\whisper\models--Systran--faster-whisper-medium" (
    echo  [INFO] Descargando modelo Whisper medium...
    %VENV_PYTHON% -c "from faster_whisper import WhisperModel; WhisperModel('medium', device='cpu', download_root='.cache/srt2web/whisper')" 2>nul
    if exist ".cache\srt2web\whisper\models--Systran--faster-whisper-medium" (
        echo  [OK] Modelo Whisper medium descargado.
    ) else (
        echo  [WARNING] No se pudo descargar medium.
    )
) else (
    echo  [OK] Whisper medium ya existe.
)

REM large-v2 (config default - used by config.yaml)
if not exist ".cache\srt2web\whisper\models--Systran--faster-whisper-large-v2" (
    REM Si existe en AppData, copiarlo
    if exist "%LOCALAPPDATA%\.cache\srt2web\whisper\models--Systran--faster-whisper-large-v2" (
        echo  [INFO] Copiando modelo large-v2 desde cache del sistema...
        xcopy /E /I /Y "%LOCALAPPDATA%\.cache\srt2web\whisper\models--Systran--faster-whisper-large-v2" ".cache\srt2web\whisper\models--Systran--faster-whisper-large-v2" >nul 2>&1
        if exist ".cache\srt2web\whisper\models--Systran--faster-whisper-large-v2" (
            echo  [OK] Modelo Whisper large-v2 copiado.
        ) else (
            echo  [INFO] Descargando modelo Whisper large-v2...
            %VENV_PYTHON% -c "from faster_whisper import WhisperModel; WhisperModel('large-v2', device='cpu', download_root='.cache/srt2web/whisper')" 2>nul
        )
    ) else (
        echo  [INFO] Descargando modelo Whisper large-v2...
        %VENV_PYTHON% -c "from faster_whisper import WhisperModel; WhisperModel('large-v2', device='cpu', download_root='.cache/srt2web/whisper')" 2>nul
    )
    if exist ".cache\srt2web\whisper\models--Systran--faster-whisper-large-v2" (
        echo  [OK] Modelo Whisper large-v2 disponible.
    ) else (
        echo  [WARNING] No se pudo obtener large-v2.
    )
) else (
    echo  [OK] Whisper large-v2 ya existe.
)

REM large-v3 (best quality - optional)
if not exist ".cache\srt2web\whisper\models--Systran--faster-whisper-large-v3" (
    echo  [INFO] Descargando modelo Whisper large-v3...
    %VENV_PYTHON% -c "from faster_whisper import WhisperModel; WhisperModel('large-v3', device='cpu', download_root='.cache/srt2web/whisper')" 2>nul
    if exist ".cache\srt2web\whisper\models--Systran--faster-whisper-large-v3" (
        echo  [OK] Modelo Whisper large-v3 descargado.
    ) else (
        echo  [WARNING] No se pudo descargar large-v3.
    )
) else (
    echo  [OK] Whisper large-v3 ya existe.
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
REM Opcional: Voces Piper (todas las 28 voces)
REM =============================================
echo.
echo [INFO] Verificando voces Piper...

if not exist "models\piper" mkdir models\piper

%VENV_PYTHON% scripts/download_piper_voices.py
if %errorlevel% equ 0 (
    echo  [OK] Voces Piper verificadas/descargadas.
) else (
    echo  [WARNING] Error al descargar voces Piper.
)

REM =============================================
REM Resumen
REM =============================================
echo.
echo ===============================================
echo            RESUMEN DE INSTALACION
echo ===============================================

%VENV_PYTHON% -c "import torch; print('PyTorch: ' + ('CUDA ' + torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'))" 2>nul

%VENV_PYTHON% -c "import onnxruntime as ort; print('ONNX: ' + ('GPU' if 'CUDAExecutionProvider' in ort.get_available_providers() else 'CPU'))" 2>nul

if exist "bin\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe" (
    echo FFmpeg: OK ^(NVENC^)
) else (
    echo FFmpeg: No encontrado
)

REM Contar modelos Whisper descargados
for /d %%D in (.cache\srt2web\whisper\models--Systran--faster-whisper-*) do echo Whisper: %%~nxD

REM Contar voces Piper
for /f %%A in ('dir /b models\piper*.onnx 2^>nul ^| findstr /c".onnx"') do (
    if not defined VOICES_COUNT set VOICES_COUNT=%%A
)
if defined VOICES_COUNT (
    echo Voces Piper: !VOICES_COUNT!
)

echo.
echo ===============================================
echo            INSTALACION COMPLETADA
echo ===============================================
echo.
echo Para iniciar: Start.bat
echo.
pause
