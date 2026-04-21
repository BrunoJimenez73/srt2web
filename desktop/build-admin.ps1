$ErrorActionPreference = "Stop"
$scriptPath = $MyInvocation.MyCommand.Path
$scriptDir = Split-Path $scriptPath -Parent

Write-Host "Building SRT2Web NSIS installer as Administrator..." -ForegroundColor Cyan

try {
    $env:NODE_OPTIONS = ""
    $process = Start-Process -FilePath "cmd.exe" -ArgumentList "/c cd /d `"$scriptDir`" && npm run build:win" -Verb RunAs -PassThru -WindowStyle Normal
    
    if ($process) {
        $process.WaitForExit()
        Write-Host "Build completed with exit code: $($process.ExitCode)" -ForegroundColor $(if ($process.ExitCode -eq 0) { "Green" } else { "Red" })
    }
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
}