param([switch]$Quick)

# init.ps1 — Verificación del arnés srt2web
# Exit code 0 = entorno listo. Exit code 1 = bloqueante.

$EXIT_CODE = 0
$RED = "Red"
$GREEN = "Green"
$YELLOW = "Yellow"

function Ok   { Write-Host "[OK]   $args" -ForegroundColor $GREEN }
function Warn { Write-Host "[WARN] $args" -ForegroundColor $YELLOW }
function Fail { Write-Host "[FAIL] $args" -ForegroundColor $RED; $script:EXIT_CODE = 1 }

$VENV_PYTHON = ".\venv\Scripts\python.exe"
if (-not (Test-Path $VENV_PYTHON)) { $VENV_PYTHON = "python" }

Write-Host "── 1. Entorno Python ─────────────────────────────" -ForegroundColor Cyan
$pyVer = & $VENV_PYTHON --version 2>&1
if ($LASTEXITCODE -eq 0) { Ok "Python: $pyVer" } else { Fail "Python no disponible"; exit 1 }

Write-Host "`n── 2. Archivos base del arnés ─────────────────────" -ForegroundColor Cyan
$baseFiles = @("AGENTS.md", "CHECKPOINTS.md", "feature_list.json", "progress/current.md", "progress/history.md")
foreach ($f in $baseFiles) {
    if (Test-Path $f) { Ok "Existe $f" } else { Fail "Falta $f" }
}

Write-Host "`n── 3. feature_list.json ───────────────────────────" -ForegroundColor Cyan
try {
    $data = Get-Content "feature_list.json" -Raw | ConvertFrom-Json
    $inProgress = $data.features | Where-Object { $_.status -eq "in_progress" }
    if ($inProgress.Count -gt 1) { Fail "$($inProgress.Count) features en in_progress (máx 1)" }
    else { Ok "feature_list.json válido ($($data.features.Count) features)" }
} catch { Fail "feature_list.json inválido: $_" }

Write-Host "`n── 4. Tests Python (obligatorio) ──────────────────" -ForegroundColor Cyan
if ($Quick) {
    Warn "Modo quick: saltando tests"
} else {
    $testResult = & $VENV_PYTHON -m pytest tests/unit/ -q --tb=short 2>&1
    if ($LASTEXITCODE -eq 0) { Ok "Tests Python: todos pasan" } else { Fail "Tests Python fallan"; Write-Host $testResult -ForegroundColor $RED }
}

if (-not $Quick) {
    Write-Host "`n── 5. TypeScript (informativo) ─────────────────────" -ForegroundColor Cyan
    if (Test-Path "frontend/node_modules/.bin/tsc") {
        $tscResult = & "frontend/node_modules/.bin/tsc" --noEmit 2>&1
        if ($LASTEXITCODE -eq 0) { Ok "TypeScript: 0 errores" } else { Warn "TypeScript tiene errores (no bloqueante)" }
    } else { Warn "TypeScript no disponible (frontend/node_modules/.bin/tsc)" }

    Write-Host "`n── 6. Tests frontend (informativo) ──────────────────" -ForegroundColor Cyan
    if (Test-Path "frontend/node_modules/.bin/vitest") {
        $npmResult = & "npm" test --prefix frontend 2>&1
        if ($LASTEXITCODE -eq 0) { Ok "Frontend tests: pasan" } else { Warn "Frontend tests fallan (no bloqueante)" }
    } else { Warn "Vitest no disponible" }

    Write-Host "`n── 7. Build frontend (informativo) ─────────────────" -ForegroundColor Cyan
    if (Test-Path "frontend/node_modules/.bin/astro") {
        $buildResult = & "npm" run build:local --prefix frontend 2>&1
        if ($LASTEXITCODE -eq 0) { Ok "Frontend build: exitoso" } else { Warn "Frontend build falla (no bloqueante)" }
    } else { Warn "Astro no disponible" }
}

Write-Host "`n── 8. Resumen ─────────────────────────────────────" -ForegroundColor Cyan
if ($EXIT_CODE -eq 0) { Ok "Entorno listo." } else { Fail "Hay errores bloqueantes. Revisa arriba." }
exit $EXIT_CODE
