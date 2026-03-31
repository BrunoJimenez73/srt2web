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
set "NEED_VENV=0"

REM =============================================
REM 1. Verificar/Crear entorno virtual
REM =============================================
echo [1/6] Entorno virtual...

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
        set "NEED_VENV=1"
    ) else (
        echo  [ERROR] No se pudo crear. Instala Python 3.12.
        pause
        exit /b 1
    )
)

REM =============================================
REM 2. Instalar dependencias base
REM =============================================
echo.
echo [2/6] Dependencias base...

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
echo [3/6] PyTorch CUDA...

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
echo [4/6] ONNX Runtime GPU...

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
REM 5. Descargar modelos de Whisper
REM =============================================
echo.
echo [5/7] Modelos Whisper...

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
REM 6. Verificar/Descargar FFmpeg con NVENC
REM =============================================
echo.
echo [6/6] FFmpeg con NVENC...

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
REM 7. Verificar voces Piper
REM =============================================
echo.
echo [7/7] Voces Piper...

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
