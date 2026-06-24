param(
  [int[]]$Ports = @(3000, 8000),
  [switch]$Supabase
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$ProjectName = Split-Path $Root -Leaf

function Write-CleanupLog {
  param([string]$Message)
  Write-Host "[dev-cleanup] $Message" -ForegroundColor Cyan
}

function Stop-ProcessTree {
  param([int]$ProcessId)
  if ($ProcessId -eq $PID) {
    return
  }

  $Children = Get-CimInstance Win32_Process -Filter "ParentProcessId = $ProcessId" -ErrorAction SilentlyContinue
  foreach ($Child in $Children) {
    Stop-ProcessTree -ProcessId $Child.ProcessId
  }

  $Process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
  if ($Process) {
    Write-CleanupLog "Stopping PID $ProcessId ($($Process.ProcessName))"
    Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
  }
}

foreach ($Port in $Ports) {
  $Connections = @(
    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  )

  if ($Connections.Count -eq 0) {
    Write-CleanupLog "Port $Port is free."
    continue
  }

  $ProcessIds = @($Connections | Select-Object -ExpandProperty OwningProcess -Unique)
  foreach ($ProcessId in $ProcessIds) {
    Write-CleanupLog "Port $Port is held by PID $ProcessId."
    Stop-ProcessTree -ProcessId $ProcessId
  }
}

Write-CleanupLog "Done."

if ($Supabase) {
  Write-CleanupLog "Stopping local Supabase stack..."
  npx -y supabase@latest stop --no-backup

  $StaleContainers = @(
    docker ps -a --filter "name=supabase_" --format "{{.Names}}" |
      Where-Object { $_ -like "supabase_*_$ProjectName" }
  )

  foreach ($ContainerName in $StaleContainers) {
    Write-CleanupLog "Removing stale Supabase container $ContainerName"
    docker rm -f $ContainerName | Out-Null
  }

  Write-CleanupLog "Supabase stop requested. Volumes were not removed."
}
