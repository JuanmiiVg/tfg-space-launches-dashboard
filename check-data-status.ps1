# Script para ver el estado actual de los datos (volumen, progreso)
# Uso: .\check-data-status.ps1

Write-Host ""
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "Estado de Datos - Space Launches" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""

$ProjectRoot = Get-Location
$RawPath = "data/raw"
$GoldPath = "data/gold"
$SilverPath = "data/silver"
$CursorFile = "data/raw/.launch_library_cursor.json"

# CURSOR STATUS
Write-Host "[CURSOR] Estado del Cursor Launch Library:" -ForegroundColor Yellow
if (Test-Path $CursorFile) {
    $cursor = Get-Content $CursorFile | ConvertFrom-Json
    Write-Host "  Actualizado: $($cursor.updated_at_utc)"
    Write-Host "  Páginas procesadas: $($cursor.pages_fetched)"
    Write-Host "  Lanzamientos acumulados: $($cursor.launches_fetched)"
    Write-Host "  Rate limited en última ejecución: $($cursor.was_rate_limited)"
    Write-Host "  Próxima URL: $($cursor.next_url.Substring(0, [Math]::Min(60, $cursor.next_url.Length)))..."
} else {
    Write-Host "  No se ha iniciado aún" -ForegroundColor Gray
}

Write-Host ""

# RAW DATA
Write-Host "[RAW] Datos RAW (ingesta bruta):" -ForegroundColor Yellow
$rawFolders = @()
if (Test-Path $RawPath) {
    $rawFolders = Get-ChildItem $RawPath -Directory | Where-Object { $_.Name -match "^\d+" } | Sort-Object Name -Descending
    
    if ($rawFolders.Count -gt 0) {
        Write-Host "  Últimas 5 ingestas:"
        $rawFolders | Select-Object -First 5 | ForEach-Object {
            $llFile = Join-Path $_.FullName "launch_library_launches.jsonl"
            $spacexFile = Join-Path $_.FullName "spacex_launches_images.jsonl"
            $weatherFile = Join-Path $_.FullName "open_meteo_samples.jsonl"
            
            $llCount = if (Test-Path $llFile) { (Get-Content $llFile | Measure-Object -Line).Lines } else { 0 }
            $spacexCount = if (Test-Path $spacexFile) { (Get-Content $spacexFile | Measure-Object -Line).Lines } else { 0 }
            $weatherCount = if (Test-Path $weatherFile) { (Get-Content $weatherFile | Measure-Object -Line).Lines } else { 0 }
            
            Write-Host "    $($_.Name): LL=$llCount, SpaceX=$spacexCount, Weather=$weatherCount" -ForegroundColor Cyan
        }
    } else {
        Write-Host "  No hay datos RAW aún" -ForegroundColor Gray
    }
} else {
    Write-Host "  Carpeta no existe" -ForegroundColor Gray
}

Write-Host ""

# SILVER DATA
Write-Host "[SILVER] Datos SILVER (normalizados):" -ForegroundColor Yellow
if (Test-Path $SilverPath) {
    $launches = Get-ChildItem "$SilverPath/launches" -Directory -ErrorAction SilentlyContinue
    $images = Get-ChildItem "$SilverPath/images" -Directory -ErrorAction SilentlyContinue
    $weather = Get-ChildItem "$SilverPath/weather" -Directory -ErrorAction SilentlyContinue
    
    Write-Host "  Launches: $(($launches | Measure-Object).Count) años"
    Write-Host "  Images: $(($images | Measure-Object).Count) fuentes"
    Write-Host "  Weather: $(($weather | Measure-Object).Count) años"
}

Write-Host ""

# GOLD DATA
Write-Host "[GOLD] Datos GOLD (agregados):" -ForegroundColor Yellow
if (Test-Path $GoldPath) {
    $companyMetrics = @(Get-ChildItem "$GoldPath/company_year_metrics" -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -match "^launch_year=" })
    $launchFeatures = @(Get-ChildItem "$GoldPath/launch_features" -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -match "^launch_year=" })
    
    Write-Host "  Company Year Metrics: $($companyMetrics.Count) años"
    Write-Host "  Launch Features: $($launchFeatures.Count) años"
}

Write-Host ""
Write-Host "[INFO] Próximos pasos:" -ForegroundColor Cyan
Write-Host "  1. Ejecutar: .\run-incremental.ps1 -Runs 20"
Write-Host "  2. Monitorear: .\check-data-status.ps1"
Write-Host "  3. Ver progreso del cursor: Get-Content data/raw/.launch_library_cursor.json"
Write-Host ""
