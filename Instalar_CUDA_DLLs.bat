@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

:: Auto-elevate to admin if not running as admin
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Este script necesita permisos de Administrador.
    echo Reintentando con elevacion...
    powershell -Command "Start-Process cmd -ArgumentList '/c cd /d %CD% && %~f0' -Verb RunAs"
    exit /b
)

echo ================================================
echo  Instalando TODAS las DLLs de CUDA para 
echo  onnxruntime-gpu (incluyendo cuDNN)
echo ================================================
echo.

set "SOURCE=C:\Users\bruno\AppData\Roaming\Python\Python313\site-packages\nvidia"
set "DEST=C:\Windows\System32"

echo [1/5] Verificando carpeta NVIDIA...
if not exist "%SOURCE%" (
    echo [ERROR] No se encontro la carpeta NVIDIA
    echo Asegurate de haber instalado los paquetes:
    echo   pip install nvidia-cublas-cu12 nvidia-cuda-runtime-cu12 nvidia-cudnn-cu12
    pause
    exit /b 1
)
echo [OK] Carpeta NVIDIA encontrada

echo.
echo [2/5] Copiando TODAS las DLLs de NVIDIA...
echo.

set "COPIED=0"

:: Copiar cuBLAS
if exist "%SOURCE%\cublas\bin\*.dll" (
    echo   - cuBLAS...
    for %%f in ("%SOURCE%\cublas\bin\*.dll") do (
        copy /Y "%%f" "%DEST%\" >nul 2>&1
        if !errorlevel! equ 0 set /a COPIED+=1
    )
    echo     [OK]
)

:: Copiar CUDA Runtime
if exist "%SOURCE%\cuda_runtime\bin\*.dll" (
    echo   - CUDA Runtime...
    for %%f in ("%SOURCE%\cuda_runtime\bin\*.dll") do (
        copy /Y "%%f" "%DEST%\" >nul 2>&1
        if !errorlevel! equ 0 set /a COPIED+=1
    )
    echo     [OK]
)

:: Copiar cuDNN (CRITICO!)
if exist "%SOURCE%\cudnn\bin\*.dll" (
    echo   - cuDNN (CRITICO)...
    for %%f in ("%SOURCE%\cudnn\bin\*.dll") do (
        copy /Y "%%f" "%DEST%\" >nul 2>&1
        if !errorlevel! equ 0 set /a COPIED+=1
    )
    echo     [OK]
) else (
    echo   - cuDNN [NO ENCONTRADO EN:%SOURCE%\cudnn\bin\]
)

:: Copiar nvjit (si existe)
if exist "%SOURCE%\nvjit\bin\*.dll" (
    echo   - nvJIT...
    for %%f in ("%SOURCE%\nvjit\bin\*.dll") do (
        copy /Y "%%f" "%DEST%\" >nul 2>&1
        if !errorlevel! equ 0 set /a COPIED+=1
    )
    echo     [OK]
)

echo.
echo [3/5] Total DLLs copiadas: %COPIED%

echo.
echo [4/5] Verificando DLLs criticas...
echo.

set "ALL_OK=1"

if exist "%DEST%\cublasLt64_12.dll" (
    echo [OK] cublasLt64_12.dll
) else (
    echo [FALTA] cublasLt64_12.dll
    set "ALL_OK=0"
)

if exist "%DEST%\cudart64_12.dll" (
    echo [OK] cudart64_12.dll
) else (
    echo [FALTA] cudart64_12.dll
    set "ALL_OK=0"
)

if exist "%DEST%\cudnn64_9.dll" (
    echo [OK] cudnn64_9.dll
) else (
    echo [FALTA] cudnn64_9.dll *** CRITICO ***
    set "ALL_OK=0"
)

if exist "%DEST%\cudnn_cnn64_9.dll" (
    echo [OK] cudnn_cnn64_9.dll
) else (
    echo [FALTA] cudnn_cnn64_9.dll
    set "ALL_OK=0"
)

if exist "%DEST%\cudnn_ops64_9.dll" (
    echo [OK] cudnn_ops64_9.dll
) else (
    echo [FALTA] cudnn_ops64_9.dll
    set "ALL_OK=0"
)

echo.
echo [5/5] Resultado...
echo.

if "%ALL_OK%"=="1" (
    echo ================================================
    echo  TODAS LAS DLLs INSTALADAS EXITOSAMENTE!
    echo ================================================
    echo.
    echo IMPORTANTE: Cierra y reinicia el servidor de srt2web
    echo para que los cambios tengan efecto.
) else (
    echo ================================================
    echo  HUBO ERRORES
    echo ================================================
    echo.
    echo Soluciones:
    echo 1. Ejecuta este script como ADMINISTRADOR (click derecho)
    echo 2. Verifica que tienes los paquetes NVIDIA:
    echo    pip install nvidia-cublas-cu12 nvidia-cuda-runtime-cu12 nvidia-cudnn-cu12
    echo 3. Reinicia el equipo
)

echo.
pause
