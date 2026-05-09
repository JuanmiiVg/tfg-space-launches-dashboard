# Script para ejecutar ingestion incremental múltiples veces
# Uso: .\run-incremental.ps1 -Runs 10 -WaitSeconds 30

param(
    [int]$Runs = 10,
    [int]$WaitSeconds = 60,
    [switch]$ResetCursor,
    [switch]$ShowLogs
)

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot
$CursorFile = Join-Path $ProjectRoot "data/raw/.launch_library_cursor.json"

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "Space Launches - Ingestion Incremental" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Configuración:"
Write-Host "  Ejecuciones: $Runs"
Write-Host "  Espera entre runs: $WaitSeconds segundos"
Write-Host "  Reset cursor: $ResetCursor"
Write-Host ""

# Reset cursor si se solicita
if ($ResetCursor) {
    if (Test-Path $CursorFile) {
        Write-Host "Eliminando cursor anterior..." -ForegroundColor Yellow
        Remove-Item $CursorFile -Force
        Write-Host "Cursor eliminado" -ForegroundColor Green
    }
}

# Ejecutar ingestion múltiples veces
for ($i = 1; $i -le $Runs; $i++) {
    Write-Host ""
    Write-Host "===================================================" -ForegroundColor Cyan
    Write-Host "RUN $i de $Runs" -ForegroundColor Cyan
    Write-Host "===================================================" -ForegroundColor Cyan
    Write-Host ""

    # Mostrar estado del cursor antes
    if (Test-Path $CursorFile) {
        $cursor = Get-Content $CursorFile | ConvertFrom-Json
        Write-Host "Estado anterior:" -ForegroundColor Yellow
        Write-Host "  Páginas obtenidas: $($cursor.pages_fetched)"
        Write-Host "  Lanzamientos totales: $($cursor.launches_fetched)"
        Write-Host "  Rate limited: $($cursor.was_rate_limited)"
        Write-Host ""
    }

    # Ejecutar docker
    Write-Host "Iniciando docker..." -ForegroundColor Green
    $StartTime = Get-Date
    
    docker-compose run --rm ingestion
    
    $EndTime = Get-Date
    $Duration = ($EndTime - $StartTime).TotalSeconds
    
    # Verificar resultado
    $LastExitCode = $LASTEXITCODE
    if ($LastExitCode -eq 0) {
        Write-Host "[OK] Run $i completado en $([Math]::Round($Duration, 2))s" -ForegroundColor Green
        
        # Mostrar estado del cursor después
        if (Test-Path $CursorFile) {
            $cursor = Get-Content $CursorFile | ConvertFrom-Json
            Write-Host "Estado actual:" -ForegroundColor Cyan
            Write-Host "  Páginas obtenidas: $($cursor.pages_fetched)"
            Write-Host "  Lanzamientos totales: $($cursor.launches_fetched)"
            Write-Host "  Rate limited: $($cursor.was_rate_limited)"
            Write-Host "  Próxima URL: $($cursor.next_url.Substring(0, [Math]::Min(50, $cursor.next_url.Length)))..."
        }
    } else {
        Write-Host "✗ Run $i falló (exit code: $LastExitCode). Se detiene el lote." -ForegroundColor Red
        exit $LastExitCode
    }

    # Esperar entre runs (excepto en el último)
    if ($i -lt $Runs) {
        Write-Host ""
        Write-Host "Esperando $WaitSeconds segundos antes del siguiente run..." -ForegroundColor Yellow
        
        # Countdown
        for ($j = $WaitSeconds; $j -gt 0; $j--) {
            Write-Host "`r  $j segundos..." -NoNewline -ForegroundColor Yellow
            Start-Sleep -Seconds 1
        }
        Write-Host "`r  Listo!                 " -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "Proceso completado" -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Cyan
