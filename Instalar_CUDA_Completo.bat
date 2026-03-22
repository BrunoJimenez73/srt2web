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
echo  INSTALADOR COMPLETO DE CUDA PARA onnxruntime
echo ================================================
echo.

:: ==============================================
:: PARTE 1: Instalar paquetes NVIDIA via pip
:: ==============================================

echo [PARTE 1] Instalando paquetes NVIDIA via pip...
echo.

set "PACKAGES=nvidia-cublas-cu12 nvidia-cuda-runtime-cu12 nvidia-cudnn-cu12 nvidia-cufft-cu12 nvidia-curand-cu12 nvidia-cusolver-cu12 nvidia-cusparse-cu12 nvidia-nvtx-cu12"

echo Paquetes a instalar:
echo   - nvidia-cublas-cu12
echo   - nvidia-cuda-runtime-cu12  
echo   - nvidia-cudnn-cu12
echo   - nvidia-cufft-cu12
echo   - nvidia-curand-cu12
echo   - nvidia-cusolver-cu12
echo   - nvidia-cusparse-cu12
echo   - nvidia-nvtx-cu12
echo.

:: Intentar instalar con extras de onnxruntime primero
echo Instalando onnxruntime-gpu con extras [cuda,cudnn]...
pip install "onnxruntime-gpu[cuda,cudnn]" --force-reinstall -q
if %errorlevel% equ 0 (
    echo [OK] onnxruntime-gpu reinstalado con extras
) else (
    echo [WARNING] Fallo al reinstalar onnxruntime-gpu, continuando...
)

echo.
echo Instalando paquetes NVIDIA individuales...
for %%p in (%PACKAGES%) do (
    echo   - Instalando %%p...
    pip install %%p -q
    if %errorlevel% equ 0 (
        echo     [OK]
    ) else (
        echo     [WARNING]
    )
)

echo.
echo [PARTE 1] Completada.

:: ==============================================
:: PARTE 2: Copiar TODAS las DLLs a System32
:: ==============================================

echo.
echo [PARTE 2] Copiando DLLs a System32...
echo.

set "SOURCE=C:\Users\bruno\AppData\Roaming\Python\Python313\site-packages\nvidia"
set "DEST=C:\Windows\System32"

if not exist "%SOURCE%" (
    echo [ERROR] No se encontro la carpeta NVIDIA
    echo Ruta esperada: %SOURCE%
    echo.
    echo Verifica que los paquetes se instalaron correctamente.
    pause
    exit /b 1
)

set "TOTAL_COPIED=0"

:: Buscar todas las carpetas bin recursively
for /r "%SOURCE%" %%f in (*.dll) do (
    set "DLL_NAME=%%~nxf"
    copy /Y "%%f" "%DEST%\" >nul 2>&1
    if !errorlevel! equ 0 (
        echo   [OK] !DLL_NAME!
        set /a TOTAL_COPIED+=1
    )
)

echo.
echo Total DLLs copiadas: !TOTAL_COPIED!

:: ==============================================
:: PARTE 3: Verificar DLLs criticas
:: ==============================================

echo.
echo [PARTE 3] Verificando DLLs criticas...
echo.

set "ALL_OK=1"

set "CRITICAL_DLLS=cublasLt64_12.dll cublas64_12.dll cudart64_12.dll cudnn64_9.dll cudnn_cnn64_9.dll cudnn_ops64_9.dll cudnn_adv64_9.dll cufft64_11.dll curand64_10.dll cusolver64_11.dll cusparse64_12.dll"

for %%d in (%CRITICAL_DLLS%) do (
    if exist "%DEST%\%%d" (
        echo [OK] %%d
    ) else (
        echo [FALTA] %%d
        set "ALL_OK=0"
    )
)

:: ==============================================
:: PARTE 4: Agregar al PATH del usuario
:: ==============================================

echo.
echo [PARTE 4] Agregando NVIDIA al PATH...
echo.

set "NVIDIA_PATH=%SOURCE%\cublas\bin;%SOURCE%\cuda_runtime\bin;%SOURCE%\cudnn\bin"

:: Agregar a PATH del usuario (no requiere reinicio de apps)
setx PATH "%NVIDIA_PATH%;%PATH%" >nul 2>&1
echo [OK] PATH actualizado (tendra efecto en nuevas terminales)

:: ==============================================
:: RESULTADO FINAL
:: ==============================================

echo.
echo ================================================
if "%ALL_OK%"=="1" (
    echo  INSTALACION COMPLETADA EXITOSAMENTE!
    echo ================================================
    echo.
    echo IMPORTANTE:
    echo 1. CIERRA todas las terminales y aplicaciones Python
    echo 2. REINICIA el servidor srt2web
    echo 3. Si sigue fallando, REINICIA EL EQUIPO
) else (
    echo  ALGUNAS DLLs FALTAN
    echo ================================================
    echo.
    echo Pasos adicionales:
    echo 1. REINICIA EL EQUIPO
    echo 2. Ejecuta este script de nuevo
    echo 3. Verifica que pip install funciono correctamente
)
echo.
echo.
pause
