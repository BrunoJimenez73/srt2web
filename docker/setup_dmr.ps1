<#
.SYNOPSIS
    Sets up Docker Model Runner with Gemma 4 E4B for srt2web.
.DESCRIPTION
    - Enables Docker Model Runner
    - Pulls ai/gemma4:E4B
    - Configures maximum context (128K tokens)
    - Verifies the model is ready via API
#>

$ErrorActionPreference = "Stop"
$Model = "ai/gemma4:E4B"
$ContextSize = 131072  # 128K tokens

Write-Host "=== Docker Model Runner Setup for srt2web ===" -ForegroundColor Cyan
Write-Host ""

# 1. Check Docker
Write-Host "[1/5] Checking Docker..." -ForegroundColor Yellow
try {
    $dockerVersion = docker version --format "{{.Server.Version}}" 2>$null
    if (-not $dockerVersion) { throw "Docker not running" }
    Write-Host "  Docker $dockerVersion OK" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Docker is not running. Start Docker Desktop first." -ForegroundColor Red
    exit 1
}

# 2. Check Docker Model Runner
Write-Host "[2/5] Checking Docker Model Runner..." -ForegroundColor Yellow
try {
    $dmrVersion = docker model version 2>$null
    if (-not $dmrVersion) { throw "DMR not available" }
    Write-Host "  DMR version: $dmrVersion" -ForegroundColor Green
} catch {
    Write-Host "  Docker Model Runner is not available." -ForegroundColor Red
    Write-Host "  Open Docker Desktop -> Settings -> AI -> Enable Docker Model Runner" -ForegroundColor Yellow
    Write-Host "  Also enable: GPU-backed inference + Host-side TCP on port 12434" -ForegroundColor Yellow
    exit 1
}

# 3. Pull the model
Write-Host "[3/5] Pulling $Model ..." -ForegroundColor Yellow
try {
    docker model pull $Model
    Write-Host "  Model pulled successfully" -ForegroundColor Green
} catch {
    Write-Host "  ERROR pulling model: $_" -ForegroundColor Red
    exit 1
}

# 4. Configure max context
Write-Host "[4/5] Configuring context size = $ContextSize tokens..." -ForegroundColor Yellow
try {
    docker model configure --context-size $ContextSize $Model
    Write-Host "  Context size configured" -ForegroundColor Green
} catch {
    Write-Host "  WARNING: Could not configure context size: $_" -ForegroundColor Yellow
    Write-Host "  The model will use default context (4K)." -ForegroundColor Yellow
}

# 5. Verify API
Write-Host "[5/5] Verifying API endpoint..." -ForegroundColor Yellow
Start-Sleep -Seconds 2
try {
    $response = Invoke-RestMethod -Uri "http://localhost:12434/engines/v1/models" -TimeoutSec 5 -ErrorAction Stop
    $modelFound = $response.data | Where-Object { $_.id -like "*gemma4*E4B*" -or $_.id -like "*gemma4*" }
    if ($modelFound) {
        Write-Host "  Model ready at http://localhost:12434/engines/v1" -ForegroundColor Green
        Write-Host "  Model ID: $($modelFound.id)" -ForegroundColor Green
    } else {
        Write-Host "  Model pulled but not listed in API yet (may need a moment)." -ForegroundColor Yellow
        Write-Host "  Available models: $($response.data.id -join ', ')" -ForegroundColor Gray
    }
} catch {
    Write-Host "  WARNING: API not responding (TCP may be disabled): $_" -ForegroundColor Yellow
    Write-Host "  Enable 'Host-side TCP support' in Docker Desktop -> Settings -> AI" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Setup complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "To use DMR translator in srt2web:" -ForegroundColor White
Write-Host "  1. Set config.yaml: modules.dmr_translator.enabled = true" -ForegroundColor Gray
Write-Host "  2. Restart srt2web server" -ForegroundColor Gray
Write-Host ""
Write-Host "DMR API:" -ForegroundColor White
Write-Host "  OpenAI-compatible: http://localhost:12434/engines/v1/chat/completions" -ForegroundColor Gray
Write-Host "  Model: $Model (context: $ContextSize tokens)" -ForegroundColor Gray
