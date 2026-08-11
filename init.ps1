param([switch]$Quick)

# init.ps1 - Verificacion del arnes srt2web
# Exit code 0 = entorno listo. Exit code 1 = bloqueante.

$EXIT_CODE = 0

function Ok   { $args | ForEach-Object { Write-Host "[OK]   $_" -ForegroundColor Green } }
function Warn { $args | ForEach-Object { Write-Host "[WARN] $_" -ForegroundColor Yellow } }
function Fail { $args | ForEach-Object { Write-Host "[FAIL] $_" -ForegroundColor Red }; $script:EXIT_CODE = 1 }

$VENV_PYTHON = ".\venv\Scripts\python.exe"
if (-not (Test-Path $VENV_PYTHON)) { $VENV_PYTHON = "python" }

Write-Host "--- 1. Entorno Python ---" -ForegroundColor Cyan
$pyVer = & $VENV_PYTHON --version 2>&1
if ($LASTEXITCODE -eq 0) { Ok "Python: $pyVer" } else { Fail "Python no disponible"; exit 1 }

Write-Host "`n--- 2. Archivos base del arnes ---" -ForegroundColor Cyan
$baseFiles = @("AGENTS.md", "CHECKPOINTS.md", "feature_list.json")
foreach ($f in $baseFiles) {
    if (Test-Path $f) { Ok "Existe $f" } else { Fail "Falta $f" }
}

Write-Host "`n--- 3. Feature tracking (harness.db) ---" -ForegroundColor Cyan
if (Test-Path "harness.db") {
    $healthResult = & $VENV_PYTHON -m harness health 2>&1
    if ($LASTEXITCODE -eq 0) { Ok "harness.db: saludable" } else { Fail "harness.db: problemas detectados"; Write-Host $healthResult -ForegroundColor Red }
} else {
    Warn "harness.db no existe - ejecutando migracion desde feature_list.json"
    & $VENV_PYTHON -m harness migrate 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { Ok "harness.db creado via migracion" } else { Fail "Migracion fallida" }
}
# Legacy JSON validation (backward compat)
if (Test-Path "feature_list.json") {
    try {
        $data = Get-Content "feature_list.json" -Raw -Encoding UTF8 | ConvertFrom-Json
        $featureCount = $data.features.Count
        Ok "feature_list.json existe ($featureCount features, legacy)"
    } catch {
        Warn "feature_list.json con problemas (no bloqueante si harness.db existe)"
    }
} else {
    Warn "feature_list.json no encontrado (usa harness.db)"
}

Write-Host "`n--- 4. Tests Python (obligatorio) ---" -ForegroundColor Cyan
$pytestArgs = @("-q", "--tb=short")
if ($Quick) {
    $pytestArgs += @("-m", "not slow", "-n", "auto", "--basetemp", ".\tmpsrt2web-pytest")
    Warn "Modo quick: saltando tests marcados como slow (Whisper/TTS reales)"
}
$testResult = & $VENV_PYTHON -m pytest tests/unit/ @pytestArgs 2>&1
if ($LASTEXITCODE -eq 0) { Ok "Tests Python: todos pasan" } else { Fail "Tests Python fallan"; Write-Host $testResult -ForegroundColor Red }

Write-Host "`n--- 5. Tipado Python con mypy --strict ---" -ForegroundColor Cyan
$mypyResult = & $VENV_PYTHON -m mypy core/ server/ modules/ --config-file pyproject.toml 2>&1
if ($LASTEXITCODE -eq 0) { Ok "mypy: 0 errores en core/, server/ y modules/" } else { Fail "mypy encontro errores:"; Write-Host $mypyResult -ForegroundColor Red }

Write-Host "`n--- 6. TypeScript (obligatorio) ---" -ForegroundColor Cyan
Push-Location frontend
try {
    $env:ASTRO_TELEMETRY_DISABLED = '1'
    if (Test-Path "node_modules/.bin/tsc") {
        $tscResult = & "node_modules/.bin/tsc" --noEmit 2>&1
    } else {
        $tscResult = & "npx" tsc --noEmit 2>&1
    }
    if ($LASTEXITCODE -eq 0) { Ok "TypeScript: 0 errores" } else { Fail "TypeScript tiene errores:"; Write-Host $tscResult -ForegroundColor Red }
} finally { Pop-Location }

Write-Host "`n--- 7. Tests frontend (obligatorio en Quick, informativo en full) ---" -ForegroundColor Cyan
Push-Location frontend
try {
    $env:ASTRO_TELEMETRY_DISABLED = '1'
    if (Test-Path "node_modules/.bin/vitest") {
        $npmResult = & "node_modules/.bin/vitest" run 2>&1
    } else {
        $npmResult = & "npm" test 2>&1
    }
    if ($LASTEXITCODE -eq 0) { Ok "Frontend tests: pasan" } else { Warn "Frontend tests fallan (no bloqueante en Quick)" }
} finally { Pop-Location }

if (-not $Quick) {
    Write-Host "`n--- 8. Build frontend (informativo) ---" -ForegroundColor Cyan
    Push-Location frontend
    try {
        $env:ASTRO_TELEMETRY_DISABLED = '1'
        $buildResult = & "npm" run build:local 2>&1
        if ($LASTEXITCODE -eq 0) { Ok "Frontend build: exitoso" } else { Warn "Frontend build falla (no bloqueante)" }
    } finally { Pop-Location }
}

Write-Host "`n--- 9. Herramientas dev ---" -ForegroundColor Cyan
$ruffCheck = & $VENV_PYTHON -c "import ruff" 2>&1
if ($LASTEXITCODE -eq 0) { Ok "ruff disponible" } else { Warn "ruff no instalado (pip install ruff)" }
$mkdocsCheck = & $VENV_PYTHON -c "import mkdocs" 2>&1
if ($LASTEXITCODE -eq 0) { Ok "mkdocs disponible" } else { Warn "mkdocs no instalado (pip install mkdocs)" }

Write-Host "`n--- Resumen ---" -ForegroundColor Cyan
if ($EXIT_CODE -eq 0) { Ok "Entorno listo." } else { Fail "Hay errores bloqueantes. Revisa arriba." }
exit $EXIT_CODE
