@echo off
chcp 65001 >nul
title Fix-PyTorch-CUDA

echo ===============================================
echo     FIX: Reinstalar PyTorch con CUDA
echo ===============================================
echo.
echo [INFO] Este script reinstalara PyTorch con soporte CUDA.
echo.

py -3.12 --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python 3.12 no encontrado.
    echo [INFO] Instala Python 3.12 primero.
    pause
    exit /b 1
)

set PYTHON_CMD=py -3.12

echo [INFO] Estado actual de PyTorch:
%PYTHON_CMD% -c "import torch; print('  Version:', torch.__version__); print('  CUDA:', torch.cuda.is_available()); print('  cuDNN:', torch.backends.cudnn.is_available())"

echo.
echo [INFO] Desinstalando PyTorch anterior...
%PYTHON_CMD% -m pip uninstall torch torchvision torchaudio -y

echo.
echo [INFO] Instalando PyTorch 2.5.1 con CUDA 12.1...
%PYTHON_CMD% -m pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu121

if %errorlevel% equ 0 (
    echo.
    echo [OK] PyTorch reinstalado. Verificando...
    %PYTHON_CMD% -c "import torch; print('  Version:', torch.__version__); print('  CUDA:', torch.cuda.is_available()); print('  cuDNN:', torch.backends.cudnn.is_available()); print('  GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')"
    echo.
    echo [SUCCESS] PyTorch CUDA instalado correctamente.
) else (
    echo.
    echo [ERROR] Fallo al instalar PyTorch.
)

echo.
pause
