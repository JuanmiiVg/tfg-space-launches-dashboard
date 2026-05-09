param(
    [int]$Runs = 12,
    [int]$PauseSeconds = 120,
    [switch]$Rebuild,
    [switch]$ResetCursor
)

$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

if ($ResetCursor) {
    if (Test-Path "data/raw/.launch_library_cursor.json") {
        Remove-Item "data/raw/.launch_library_cursor.json" -Force
        Write-Host "[batch] Cursor eliminado."
    }
}

if ($Rebuild) {
    Write-Host "[batch] Rebuild de imagen ingestion..."
    docker compose build --no-cache ingestion
}

for ($i = 1; $i -le $Runs; $i++) {
    Write-Host "[batch] Corrida $i de $Runs"
    docker compose run --rm ingestion

    if ($LASTEXITCODE -ne 0) {
        Write-Host "[batch] Corrida con error. Se detiene el lote."
        exit $LASTEXITCODE
    }

    $latestManifest = Get-ChildItem -Path "data/raw/*/manifest.json" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if ($latestManifest) {
        $manifest = Get-Content $latestManifest.FullName | ConvertFrom-Json
        Write-Host "[batch] Ultimo manifest: $($latestManifest.Directory.Name)"
        Write-Host "[batch] LL launches: $($manifest.files.'launch_library_launches.jsonl')"
        Write-Host "[batch] SpaceX images: $($manifest.files.'spacex_launches_images.jsonl')"
        Write-Host "[batch] Weather: $($manifest.files.'open_meteo_samples.jsonl')"
    }

    if ($i -lt $Runs) {
        Write-Host "[batch] Esperando $PauseSeconds segundos..."
        Start-Sleep -Seconds $PauseSeconds
    }
}

Write-Host "[batch] Proceso incremental finalizado."
