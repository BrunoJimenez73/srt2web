# Script para instalar DLLs de CUDA (requiere ejecucion como Administrador)
# Creado para srt2web - Piper TTS GPU support

$ErrorActionPreference = "Stop"

$sourcePath = "C:\Users\bruno\AppData\Roaming\Python\Python313\site-packages\nvidia"
$destPath = "C:\Windows\System32"

Write-Host "================================================"
Write-Host " Instalando DLLs de CUDA para onnxruntime-gpu"
Write-Host "================================================"
Write-Host ""

# Verificar carpeta fuente
if (-not (Test-Path $sourcePath)) {
    Write-Host "[ERROR] No se encontro la carpeta NVIDIA en:" -ForegroundColor Red
    Write-Host "  $sourcePath"
    Write-Host ""
    Write-Host "Instala los paquetes primero:"
    Write-Host "  pip install nvidia-cublas-cu12 nvidia-cuda-runtime-cu12 nvidia-cudnn-cu12"
    Read-Host "Presiona Enter para salir"
    exit 1
}

Write-Host "[1/4] Verificando paquetes NVIDIA instalados..."
$packages = @("cublas", "cuda_runtime", "cudnn")
foreach ($pkg in $packages) {
    $pkgPath = Join-Path $sourcePath $pkg
    if (Test-Path $pkgPath) {
        Write-Host "  [OK] $pkg" -ForegroundColor Green
    } else {
        Write-Host "  [WARNING] $pkg no encontrado" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "[2/4] Copiando DLLs de NVIDIA..."

$totalCopied = 0
$totalFailed = 0

# Buscar todas las carpetas bin recursively y copiar DLLs
Get-ChildItem -Path $sourcePath -Directory | ForEach-Object {
    $binPath = Join-Path $_.FullName "bin"
    if (Test-Path $binPath) {
        Write-Host "  Procesando: $($_.Name)..." -NoNewline
        $copied = 0
        $failed = 0
        Get-ChildItem -Path $binPath -Filter "*.dll" | ForEach-Object {
            try {
                Copy-Item -Path $_.FullName -Destination $destPath -Force -ErrorAction Stop | Out-Null
                $copied++
            } catch {
                $failed++
            }
        }
        Write-Host " ($copied DLLs)" -ForegroundColor Green
        $totalCopied += $copied
        $totalFailed += $failed
    }
}

Write-Host ""
Write-Host "[3/4] Verificando DLLs criticas..."
Write-Host ""

$criticalDLLs = @(
    "cublasLt64_12.dll",
    "cublas64_12.dll",
    "cudart64_12.dll",
    "cudnn64_9.dll",
    "cudnn_cnn64_9.dll",
    "cudnn_ops64_9.dll",
    "cudnn_adv64_9.dll",
    "nvblas64_12.dll"
)

$allPresent = $true
foreach ($dll in $criticalDLLs) {
    $present = Test-Path (Join-Path $destPath $dll)
    if ($present) {
        Write-Host "  [OK] $dll" -ForegroundColor Green
    } else {
        Write-Host "  [FALTA] $dll" -ForegroundColor Red
        $allPresent = $false
    }
}

Write-Host ""
Write-Host "[4/4] Resumen..."
Write-Host "  DLLs copiadas: $totalCopied"
Write-Host "  DLLs fallidas: $totalFailed"
Write-Host ""

if ($allPresent) {
    Write-Host "================================================" -ForegroundColor Green
    Write-Host "  TODAS LAS DLLs INSTALADAS CORRECTAMENTE!" -ForegroundColor Green
    Write-Host "================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Ahora puedes reiniciar el servidor srt2web." -ForegroundColor Cyan
} else {
    Write-Host "================================================" -ForegroundColor Yellow
    Write-Host "  ALGUNAS DLLs FALTAN" -ForegroundColor Yellow
    Write-Host "================================================" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Asegurate de:"
    Write-Host "  1. Ejecutar este script como ADMINISTRADOR"
    Write-Host "  2. Tener todos los paquetes NVIDIA instalados:"
    Write-Host "     pip install nvidia-cublas-cu12 nvidia-cuda-runtime-cu12 nvidia-cudnn-cu12"
}

Write-Host ""
Read-Host "Presiona Enter para salir"
