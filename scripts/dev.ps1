param(
  [int]$BackendPort = 8000,
  [int]$FrontendPort = 3000,
  [string]$HostAddress = "127.0.0.1",
  [switch]$Install,
  [switch]$UseSupabase,
  [switch]$StartSupabase,
  [switch]$KillExisting
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$ProjectName = Split-Path $Root -Leaf
$BackendDir = Join-Path $Root "backend"
$PythonExe = Join-Path $BackendDir ".venv\Scripts\python.exe"
$Requirements = Join-Path $BackendDir "requirements.txt"
$LogDir = Join-Path $Root ".dev-logs"
$SupabaseConfig = Join-Path $Root "supabase\config.toml"
$StartupStopwatch = [System.Diagnostics.Stopwatch]::StartNew()

function Write-DevLog {
  param([string]$Message)
  Write-Host "[dev] $Message" -ForegroundColor Cyan
}

function Write-Status {
  param(
    [string]$Name,
    [bool]$Ok,
    [string]$Message
  )
  $Label = if ($Ok) { "OK" } else { "WARN" }
  $Color = if ($Ok) { "Green" } else { "Yellow" }
  Write-Host ("[{0}] {1}: {2}" -f $Label, $Name, $Message) -ForegroundColor $Color
}

function Ensure-Command {
  param([string]$Name)
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "Required command '$Name' was not found in PATH."
  }
}

function Test-TcpPort {
  param(
    [string]$ComputerName,
    [int]$Port
  )
  try {
    $Client = [System.Net.Sockets.TcpClient]::new()
    $ConnectTask = $Client.ConnectAsync($ComputerName, $Port)
    $Connected = $ConnectTask.Wait(1000) -and $Client.Connected
    $Client.Dispose()
    return $Connected
  }
  catch {
    return $false
  }
}

function Test-HttpOk {
  param([string]$Url)
  try {
    $Response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
    return $Response.StatusCode -ge 200 -and $Response.StatusCode -lt 500
  }
  catch {
    return $false
  }
}

function Wait-HttpOk {
  param(
    [string]$Name,
    [string]$Url,
    [int]$TimeoutSeconds = 30
  )
  $Deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $Deadline) {
    if (Test-HttpOk $Url) {
      Write-Status $Name $true $Url
      return $true
    }
    Start-Sleep -Seconds 1
  }
  Write-Status $Name $false "not responding at $Url"
  return $false
}

function Get-TomlPort {
  param(
    [string]$Path,
    [string]$Section
  )

  $CurrentSection = ""
  foreach ($Line in Get-Content -LiteralPath $Path) {
    if ($Line -match '^\s*\[([^]]+)\]\s*$') {
      $CurrentSection = $Matches[1]
      continue
    }
    if ($CurrentSection -eq $Section -and $Line -match '^\s*port\s*=\s*(\d+)') {
      return [int]$Matches[1]
    }
  }

  throw "Could not find port for [$Section] in $Path."
}

function Test-WindowsExcludedPort {
  param([int]$Port)

  if (-not $IsWindows -and $env:OS -ne "Windows_NT") {
    return $false
  }

  $Ranges = netsh interface ipv4 show excludedportrange protocol=tcp 2>$null
  foreach ($Line in $Ranges) {
    if ($Line -match '^\s*(\d+)\s+(\d+)(\s+\*)?\s*$') {
      $Start = [int]$Matches[1]
      $End = [int]$Matches[2]
      $Administered = -not [string]::IsNullOrWhiteSpace($Matches[3])
      if (-not $Administered -and $Port -ge $Start -and $Port -le $End) {
        return $true
      }
    }
  }

  return $false
}

function Get-SupabaseStatus {
  Push-Location $Root
  try {
    # Supabase reports intentionally stopped optional services on stderr. Under
    # ErrorActionPreference=Stop, Windows PowerShell turns that into an exception
    # even when the JSON command itself succeeds.
    $PreviousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
      $StatusLines = & pnpm exec supabase status --output json 2>$null
      $StatusExitCode = $LASTEXITCODE
    }
    finally {
      $ErrorActionPreference = $PreviousErrorActionPreference
    }

    $StatusJson = $StatusLines -join "`n"
    if ($StatusExitCode -ne 0 -or [string]::IsNullOrWhiteSpace($StatusJson)) {
      return $null
    }
    $Status = $StatusJson | ConvertFrom-Json
    if (-not $Status.API_URL -or -not $Status.SERVICE_ROLE_KEY -or -not $Status.ANON_KEY) {
      return $null
    }
    return $Status
  }
  catch {
    return $null
  }
  finally {
    Pop-Location
  }
}

function Get-ListeningProcessIds {
  param([int]$Port)
  return @(
    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
      Select-Object -ExpandProperty OwningProcess -Unique
  )
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
    Write-DevLog "Stopping process $ProcessId ($($Process.ProcessName))"
    Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
  }
}

function Stop-ListeningProcesses {
  param([int[]]$Ports)
  foreach ($Port in $Ports) {
    foreach ($ProcessId in Get-ListeningProcessIds $Port) {
      Write-DevLog "Port $Port is held by PID $ProcessId; stopping it."
      Stop-ProcessTree -ProcessId $ProcessId
    }
  }
}

function Wait-PortFree {
  param(
    [int]$Port,
    [int]$TimeoutSeconds = 5
  )

  $Deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $Deadline) {
    $ProcessIds = Get-ListeningProcessIds $Port
    if ($ProcessIds.Count -eq 0) {
      return $true
    }
    Start-Sleep -Milliseconds 200
  }

  return $false
}

function Assert-PortFree {
  param([int]$Port)
  $ProcessIds = Get-ListeningProcessIds $Port
  if ($ProcessIds.Count -eq 0) {
    return
  }
  if ($KillExisting) {
    Write-Status "Port $Port" $false "occupied by PID(s): $($ProcessIds -join ', '); killing because -KillExisting was set"
    foreach ($ProcessId in $ProcessIds) {
      Stop-ProcessTree -ProcessId $ProcessId
    }
    if (-not (Wait-PortFree -Port $Port)) {
      $RemainingProcessIds = Get-ListeningProcessIds $Port
      throw "Port $Port is still occupied by PID(s): $($RemainingProcessIds -join ', ') after attempting to stop existing processes."
    }
    return
  }
  throw "Port $Port is already occupied by PID(s): $($ProcessIds -join ', '). Stop them first, or run scripts/dev.ps1 with -KillExisting."
}

function Reset-LogFiles {
  param(
    [string[]]$Paths,
    [int]$TimeoutSeconds = 10
  )

  $Deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ($true) {
    try {
      foreach ($Path in $Paths) {
        Set-Content -LiteralPath $Path -Value "" -Force
      }
      return
    }
    catch {
      if ((Get-Date) -ge $Deadline) {
        throw "Could not clear dev log files after stopping existing dev servers. Last error: $($_.Exception.Message)"
      }
      Start-Sleep -Milliseconds 250
    }
  }
}

function Test-DockerRunning {
  if (-not (Get-Command "docker" -ErrorAction SilentlyContinue)) {
    Write-Status "Docker" $false "docker command not found"
    return $false
  }

  for ($Attempt = 1; $Attempt -le 5; $Attempt++) {
    $Output = & cmd.exe /c "docker info >NUL 2>NUL"
    $ExitCode = $LASTEXITCODE
    if ($ExitCode -eq 0) {
      Write-Status "Docker" $true "daemon is running"
      return $true
    }
    Start-Sleep -Seconds 2
  }

  Write-Status "Docker" $false "Docker Desktop UI may be open, but the Docker daemon/CLI is not ready"
  return $false
}

function Test-SupabaseRunning {
  param(
    [int]$ApiPort,
    [switch]$Quiet
  )

  $DbContainer = "supabase_db_$ProjectName"
  $KongContainer = "supabase_kong_$ProjectName"

  $DbStatus = & cmd.exe /c "docker inspect --format ""{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}"" $DbContainer 2>NUL"
  if ($LASTEXITCODE -ne 0) {
    if (-not $Quiet) {
      Write-Status "Supabase" $false "DB container '$DbContainer' is missing; local stack is incomplete"
    }
    return $false
  }

  $KongStatus = & cmd.exe /c "docker inspect --format ""{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}"" $KongContainer 2>NUL"
  if ($LASTEXITCODE -ne 0) {
    if (-not $Quiet) {
      Write-Status "Supabase" $false "Kong container '$KongContainer' is missing"
    }
    return $false
  }

  $SupabasePortOpen = Test-TcpPort $HostAddress $ApiPort
  if ($DbStatus -match "^running (healthy|no-healthcheck)" -and $KongStatus -match "^running (healthy|no-healthcheck)" -and $SupabasePortOpen) {
    if (-not $Quiet) {
      Write-Status "Supabase" $true "local stack is running at http://${HostAddress}:$ApiPort"
    }
    return $true
  }

  if (-not $Quiet) {
    Write-Status "Supabase" $false "local stack is not healthy (db: $DbStatus, kong: $KongStatus, port $ApiPort open: $SupabasePortOpen)"
  }
  return $false
}

function Wait-SupabaseRunning {
  param(
    [int]$ApiPort,
    [int]$TimeoutSeconds = 90
  )

  $Deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $Deadline) {
    if (Test-SupabaseRunning -ApiPort $ApiPort -Quiet) {
      Test-SupabaseRunning -ApiPort $ApiPort | Out-Null
      return $true
    }
    Start-Sleep -Seconds 1
  }

  Test-SupabaseRunning -ApiPort $ApiPort | Out-Null
  return $false
}

Ensure-Command "python"
Ensure-Command "pnpm"

$BackendUrl = "http://${HostAddress}:$BackendPort"
$FrontendUrl = "http://${HostAddress}:$FrontendPort"
$BackendLog = Join-Path $LogDir "backend.log"
$BackendErrLog = Join-Path $LogDir "backend.err.log"
$FrontendLog = Join-Path $LogDir "frontend.log"
$FrontendErrLog = Join-Path $LogDir "frontend.err.log"
$SupabaseApiPort = Get-TomlPort -Path $SupabaseConfig -Section "api"

if (Test-WindowsExcludedPort -Port $SupabaseApiPort) {
  throw "Supabase ports are reserved by Windows. Run 'pnpm dev:repair:supabase-ports' once as Administrator, then run pnpm dev:full again."
}

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
Assert-PortFree $BackendPort
Assert-PortFree $FrontendPort
Reset-LogFiles -Paths @($BackendLog, $BackendErrLog, $FrontendLog, $FrontendErrLog)

$DockerRunning = Test-DockerRunning
$SupabaseRunning = $false
if ($DockerRunning) {
  $SupabaseRunning = Test-SupabaseRunning -ApiPort $SupabaseApiPort
}

if ($StartSupabase) {
  if (-not $DockerRunning) {
    throw "Cannot start Supabase because Docker Desktop is not running. Start Docker Desktop first, then run pnpm dev:full:supabase."
  }
  if (-not $SupabaseRunning) {
    $KongContainer = "supabase_kong_$ProjectName"
    $PublishedPorts = (& docker port $KongContainer 2>$null) -join "`n"
    if ($LASTEXITCODE -eq 0 -and $PublishedPorts -and $PublishedPorts -notmatch ":$SupabaseApiPort\s*$") {
      Write-DevLog "Supabase is using an older port configuration; stopping it safely before restart..."
      Push-Location $Root
      try {
        pnpm supabase:stop
        if ($LASTEXITCODE -ne 0) {
          throw "Could not stop the existing Supabase stack."
        }
      }
      finally {
        Pop-Location
      }
    }

    Write-DevLog "Starting local Supabase..."
    Push-Location $Root
    try {
      pnpm supabase:start
      if ($LASTEXITCODE -ne 0) {
        throw "Supabase CLI failed to start the local stack."
      }
    }
    finally {
      Pop-Location
    }
    $SupabaseRunning = Wait-SupabaseRunning -ApiPort $SupabaseApiPort
  }
}

if (-not $UseSupabase) {
  $UseSupabase = $true
}

if ($UseSupabase) {
  if (-not $SupabaseRunning) {
    throw "Supabase is required for dev runtime, but local Supabase is not healthy at port $SupabaseApiPort."
  }

  $SupabaseStatus = Get-SupabaseStatus
  if (-not $SupabaseStatus) {
    throw "Supabase is running, but its local connection settings could not be read."
  }

  $env:BACKEND_REPOSITORY = "supabase"
  $env:SUPABASE_URL = $SupabaseStatus.API_URL
  $env:SUPABASE_SERVICE_ROLE_KEY = $SupabaseStatus.SERVICE_ROLE_KEY
  $env:SUPABASE_KEY = $SupabaseStatus.SERVICE_ROLE_KEY
  $env:SUPABASE_KEY_SERVICE_ROLE = $SupabaseStatus.SERVICE_ROLE_KEY
  $env:VITE_SUPABASE_URL = $SupabaseStatus.API_URL
  $env:VITE_SUPABASE_ANON_KEY = $SupabaseStatus.ANON_KEY
}

if (-not (Test-Path $PythonExe)) {
  Write-DevLog "Creating backend virtual environment..."
  python -m venv (Join-Path $BackendDir ".venv")
  $Install = $true
}

if ($Install) {
  Write-DevLog "Installing backend Python dependencies..."
  & $PythonExe -m pip install -r $Requirements
}

Write-DevLog "Starting FastAPI backend at $BackendUrl"
$BackendCommand = "& `"$PythonExe`" -m uvicorn app.main:app --reload --host $HostAddress --port $BackendPort"
$BackendProcess = Start-Process `
  -FilePath "powershell" `
  -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $BackendCommand) `
  -WorkingDirectory $BackendDir `
  -RedirectStandardOutput $BackendLog `
  -RedirectStandardError $BackendErrLog `
  -WindowStyle Hidden `
  -PassThru

Write-DevLog "Starting Nuxt frontend at $FrontendUrl"
$env:NUXT_API_URL = $BackendUrl
$NuxtCmd = Join-Path $Root "node_modules\.bin\nuxt.cmd"
if (Test-Path $NuxtCmd) {
  $FrontendCommand = "& `"$NuxtCmd`" dev --host $HostAddress --port $FrontendPort"
}
else {
  $FrontendCommand = "pnpm dev --host $HostAddress --port $FrontendPort"
}
$FrontendProcess = Start-Process `
  -FilePath "powershell" `
  -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $FrontendCommand) `
  -WorkingDirectory $Root `
  -RedirectStandardOutput $FrontendLog `
  -RedirectStandardError $FrontendErrLog `
  -WindowStyle Hidden `
  -PassThru

Write-DevLog "Startup status"
Write-Status "Repository" $true $env:BACKEND_REPOSITORY
if ($env:BACKEND_REPOSITORY -eq "supabase") {
  Write-Status "Supabase URL" $true $env:SUPABASE_URL
}
$BackendReady = Wait-HttpOk "Backend" "$BackendUrl/health" 30
if (-not $BackendReady) {
  throw "FastAPI backend did not become ready. Check $BackendLog and $BackendErrLog."
}
$FrontendReady = Wait-HttpOk "Frontend" $FrontendUrl 90
if (-not $FrontendReady) {
  throw "Nuxt frontend did not become ready. Check $FrontendLog and $FrontendErrLog."
}
$SupabaseReady = Test-SupabaseRunning -ApiPort $SupabaseApiPort
if (-not $SupabaseReady) {
  throw "Supabase became unavailable during startup."
}

$StartupStopwatch.Stop()
Write-DevLog "Frontend: $FrontendUrl"
Write-DevLog "Backend:  $BackendUrl"
Write-DevLog "Logs:     $LogDir"
Write-DevLog ("Ready in {0:N1}s" -f $StartupStopwatch.Elapsed.TotalSeconds)
Write-DevLog "Press Ctrl+C to stop both servers."

try {
  while ($true) {
    if ($BackendProcess.HasExited) {
      throw "FastAPI backend exited with code $($BackendProcess.ExitCode). Check $BackendLog and $BackendErrLog."
    }
    if ($FrontendProcess.HasExited) {
      throw "Nuxt frontend exited with code $($FrontendProcess.ExitCode). Check $FrontendLog and $FrontendErrLog."
    }
    Start-Sleep -Seconds 1
  }
}
finally {
  Write-DevLog "Stopping dev servers..."
  if ($BackendProcess -and -not $BackendProcess.HasExited) {
    Stop-ProcessTree -ProcessId $BackendProcess.Id
  }
  if ($FrontendProcess -and -not $FrontendProcess.HasExited) {
    Stop-ProcessTree -ProcessId $FrontendProcess.Id
  }
  Stop-ListeningProcesses -Ports @($BackendPort, $FrontendPort)
  Write-DevLog "Stopped. If a browser still shows the app briefly, it is likely cached or a TIME_WAIT socket, not a running server."
}
