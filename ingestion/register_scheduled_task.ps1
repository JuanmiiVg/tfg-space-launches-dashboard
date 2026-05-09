# Script para crear la tarea programada de ingestion automática
# REQUIERE: Ejecutar como Administrador en PowerShell

param(
    [int]$IntervalMinutes = 60
)

$ErrorActionPreference = "Stop"

# Validar permisos de admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
if (-not $isAdmin) {
    Write-Error "Este script REQUIERE permisos de Administrador. Abre PowerShell como Administrador y vuelve a intentar."
    exit 1
}

$TaskName = "Space-Launches-Incremental-Ingestion"
$TaskDescription = "Ejecuta ingestion de datos de lanzamientos espaciales cada $IntervalMinutes minutos"
$ScriptPath = "c:\Users\juanm\Documents\GitHub\2526-bd-proyecto-final-juanmanuel\ingestion\schedule_batch.ps1"
$ProjectRoot = "c:\Users\juanm\Documents\GitHub\2526-bd-proyecto-final-juanmanuel"

# Verificar que el script existe
if (-not (Test-Path $ScriptPath)) {
    Write-Error "Script no encontrado: $ScriptPath"
    exit 1
}

Write-Host "Configurando tarea programada..."
Write-Host "  Nombre: $TaskName"
Write-Host "  Intervalo: $IntervalMinutes minutos"
Write-Host "  Script: $ScriptPath"

# Eliminar tarea anterior si existe
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "Eliminando tarea anterior..."
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Crear trigger (cada X minutos)
$Trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) -RepetitionDuration (New-TimeSpan -Days 10000) -Once -At (Get-Date)

# Crear acción (ejecutar PowerShell con el script)
$Action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`"" `
    -WorkingDirectory $ProjectRoot

# Crear configuración de tarea
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -MultipleInstances IgnoreNew

# Principal con usuario actual
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -RunLevel Highest

# Registrar tarea
Register-ScheduledTask -TaskName $TaskName `
    -Trigger $Trigger `
    -Action $Action `
    -Settings $Settings `
    -Principal $Principal `
    -Description $TaskDescription `
    -Force | Out-Null

Write-Host ""
Write-Host "Task created successfully!"
Write-Host "To verify: Get-ScheduledTask -TaskName Space-Launches-Incremental-Ingestion"
Write-Host "To view log: Get-Content $ProjectRoot\ingestion\batch_execution.log -Tail 20"
Write-Host "To delete: Unregister-ScheduledTask -TaskName Space-Launches-Incremental-Ingestion -Confirm:$false"
