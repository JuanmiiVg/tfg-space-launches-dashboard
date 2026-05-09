# Script wrapper para ejecutar ingestion incremental desde programador de tareas
# Logs a un archivo para debugging

param(
    [int]$IntervalMinutes = 60
)

$ProjectRoot = "c:\Users\juanm\Documents\GitHub\2526-bd-proyecto-final-juanmanuel"
$LogFile = Join-Path $ProjectRoot "ingestion\batch_execution.log"
$ScriptPath = Join-Path $ProjectRoot "ingestion\run_incremental_ingestion.ps1"

# Crear carpeta de logs si no existe
$LogDir = Split-Path $LogFile
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

# Inicializar o limpiar log
$LogEntry = "`n[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Iniciando ingestion batch automática..."
Add-Content -Path $LogFile -Value $LogEntry

try {
    Set-Location $ProjectRoot
    
    # Ejecutar una corrida con pausa de 2 minutos entre intentos si 429
    & $ScriptPath -Runs 1 -PauseSeconds 120
    if ($LASTEXITCODE -ne 0) {
        throw "El lote incremental devolvió el código de salida $LASTEXITCODE."
    }
    
    $SuccessEntry = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Batch completada exitosamente."
    Add-Content -Path $LogFile -Value $SuccessEntry
}
catch {
    $ErrorEntry = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] ERROR: $_"
    Add-Content -Path $LogFile -Value $ErrorEntry
    exit 1
}

exit 0
