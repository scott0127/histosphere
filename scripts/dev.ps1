param(
  [int]$BackendPort = 8000,
  [int]$FrontendPort = 3000,
  [string]$HostAddress = "127.0.0.1",
  [switch]$Install
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$BackendDir = Join-Path $Root "backend"
$PythonExe = Join-Path $BackendDir ".venv\Scripts\python.exe"
$Requirements = Join-Path $BackendDir "requirements.txt"

function Write-DevLog {
  param([string]$Message)
  Write-Host "[dev] $Message" -ForegroundColor Cyan
}

function Ensure-Command {
  param([string]$Name)
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "Required command '$Name' was not found in PATH."
  }
}

Ensure-Command "python"
Ensure-Command "pnpm"

if (-not (Test-Path $PythonExe)) {
  Write-DevLog "Creating backend virtual environment..."
  python -m venv (Join-Path $BackendDir ".venv")
  $Install = $true
}

if ($Install) {
  Write-DevLog "Installing backend Python dependencies..."
  & $PythonExe -m pip install -r $Requirements
}

$BackendUrl = "http://${HostAddress}:$BackendPort"
$FrontendUrl = "http://${HostAddress}:$FrontendPort"

Write-DevLog "Starting FastAPI backend at $BackendUrl"
$BackendJob = Start-Job -Name "histosphere-backend" -ArgumentList $BackendDir, $PythonExe, $HostAddress, $BackendPort -ScriptBlock {
  param($BackendDir, $PythonExe, $HostAddress, $BackendPort)
  Set-Location $BackendDir
  & $PythonExe -m uvicorn app.main:app --reload --host $HostAddress --port $BackendPort 2>&1 |
    ForEach-Object { $_.ToString() }
}

Write-DevLog "Starting Nuxt frontend at $FrontendUrl"
$FrontendJob = Start-Job -Name "histosphere-frontend" -ArgumentList $Root, $HostAddress, $FrontendPort, $BackendUrl -ScriptBlock {
  param($Root, $HostAddress, $FrontendPort, $BackendUrl)
  Set-Location $Root
  $env:NUXT_API_URL = $BackendUrl
  pnpm dev --host $HostAddress --port $FrontendPort 2>&1 |
    ForEach-Object { $_.ToString() }
}

Write-DevLog "Frontend: $FrontendUrl"
Write-DevLog "Backend:  $BackendUrl"
Write-DevLog "Press Ctrl+C to stop both servers."

try {
  while ($true) {
    foreach ($Job in @($BackendJob, $FrontendJob)) {
      Receive-Job -Job $Job -ErrorAction Continue
      if ($Job.State -in @("Failed", "Stopped", "Completed")) {
        throw "$($Job.Name) exited with state $($Job.State)."
      }
    }
    Start-Sleep -Milliseconds 500
  }
}
finally {
  Write-DevLog "Stopping dev servers..."
  Stop-Job -Job $BackendJob, $FrontendJob -ErrorAction SilentlyContinue
  Remove-Job -Job $BackendJob, $FrontendJob -Force -ErrorAction SilentlyContinue
}
