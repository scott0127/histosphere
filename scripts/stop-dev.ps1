param(
  [int[]]$Ports = @(3000, 8000),
  [switch]$Supabase
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")

function Write-CleanupLog {
  param([string]$Message)
  Write-Host "[dev-cleanup] $Message" -ForegroundColor Cyan
}

function Stop-ProcessTree {
  param([int]$ProcessId)
  if ($ProcessId -eq $PID) {
    return
  }

  # Guard before walking descendants: PID 4 is the parent of critical Windows processes.
  if ($ProcessId -le 4) {
    Write-Warning "Skipping Windows system PID $ProcessId; it must not be terminated."
    return
  }
  $Process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
  if (-not $Process) {
    return
  }
  if ($Process.SessionId -eq 0) {
    Write-Warning "Skipping service/system process $ProcessId ($($Process.ProcessName)). Choose another port."
    return
  }

  $Children = Get-CimInstance Win32_Process -Filter "ParentProcessId = $ProcessId" -ErrorAction SilentlyContinue
  foreach ($Child in $Children) {
    Stop-ProcessTree -ProcessId $Child.ProcessId
  }

  Write-CleanupLog "Stopping PID $ProcessId ($($Process.ProcessName))"
  Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
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
  Push-Location $Root
  try {
    pnpm supabase:stop
    if ($LASTEXITCODE -ne 0) {
      throw "Supabase CLI could not stop the local stack."
    }
  }
  finally {
    Pop-Location
  }
  Write-CleanupLog "Supabase stopped with its database backup preserved."
}
