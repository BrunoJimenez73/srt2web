# Copiar todas las DLLs de NVIDIA a System32
$dest = "C:\Windows\System32"
$srcPaths = @(
    "C:\Python313\Lib\site-packages\nvidia",
    "C:\Users\bruno\AppData\Roaming\Python\Python313\site-packages\nvidia"
)

$count = 0
foreach ($src in $srcPaths) {
    if (Test-Path $src) {
        Get-ChildItem -Path $src -Filter "*.dll" -Recurse | ForEach-Object {
            try {
                Copy-Item -Path $_.FullName -Destination $dest -Force -ErrorAction Stop
                Write-Host "[OK] $($_.Name)"
                $count++
            } catch {
                Write-Host "[ERROR] $($_.Name): $_"
            }
        }
    }
}

Write-Host ""
Write-Host "Total DLLs copiadas: $count"
Write-Host "Presiona Enter para salir..."
Read-Host
