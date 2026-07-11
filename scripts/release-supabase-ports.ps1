param(
  [int]$StartPort = 54320,
  [int]$PortCount = 10,
  [switch]$Elevated
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$LogDir = Join-Path $Root ".dev-logs"
$RepairLog = Join-Path $LogDir "supabase-port-repair.log"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Write-RepairLog {
  param([string]$Message)
  $Line = "[{0:yyyy-MM-dd HH:mm:ss}] {1}" -f (Get-Date), $Message
  Add-Content -LiteralPath $RepairLog -Value $Line
  Write-Host "[ports] $Message" -ForegroundColor Cyan
}

function Test-Administrator {
  $Identity = [Security.Principal.WindowsIdentity]::GetCurrent()
  $Principal = [Security.Principal.WindowsPrincipal]::new($Identity)
  return $Principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-TcpExcludedRanges {
  $Ranges = @()
  foreach ($Line in (netsh interface ipv4 show excludedportrange protocol=tcp)) {
    if ($Line -match '^\s*(\d+)\s+(\d+)(\s+\*)?\s*$') {
      $Ranges += [pscustomobject]@{
        Start = [int]$Matches[1]
        End = [int]$Matches[2]
        Administered = -not [string]::IsNullOrWhiteSpace($Matches[3])
      }
    }
  }
  return $Ranges
}

function Get-ConflictingDynamicRanges {
  $EndPort = $StartPort + $PortCount - 1
  return @(
    Get-TcpExcludedRanges | Where-Object {
      -not $_.Administered -and $_.Start -le $EndPort -and $_.End -ge $StartPort
    }
  )
}

function Test-ManagedReservation {
  $EndPort = $StartPort + $PortCount - 1
  return [bool](
    Get-TcpExcludedRanges | Where-Object {
      $_.Administered -and $_.Start -eq $StartPort -and $_.End -eq $EndPort
    }
  )
}

if (-not (Test-Administrator)) {
  if ($Elevated) {
    throw "Administrator privileges were requested but not granted."
  }

  Set-Content -LiteralPath $RepairLog -Value ""
  Write-RepairLog "Requesting administrator privileges..."
  $Arguments = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$PSCommandPath`"",
    "-StartPort", $StartPort,
    "-PortCount", $PortCount,
    "-Elevated"
  )
  $Process = Start-Process -FilePath "powershell" -Verb RunAs -ArgumentList $Arguments -PassThru
  $Deadline = (Get-Date).AddMinutes(3)
  while (-not $Process.HasExited -and (Get-Date) -lt $Deadline) {
    Start-Sleep -Seconds 1
    $Process.Refresh()
  }
  if (-not $Process.HasExited) {
    throw "The elevated port repair did not finish within three minutes. Check $RepairLog."
  }
  Get-Content -LiteralPath $RepairLog | Select-Object -Skip 1
  exit $Process.ExitCode
}

Write-RepairLog "Repairing the Supabase port block $StartPort-$($StartPort + $PortCount - 1)."
$DockerWasRunning = (docker desktop status 2>$null) -match "running"

try {
  if ($DockerWasRunning) {
    Write-RepairLog "Stopping Docker Desktop temporarily."
    docker desktop stop | Out-Null
  }

  $WinNat = Get-Service WinNAT -ErrorAction Stop
  if ($WinNat.Status -ne "Stopped") {
    Write-RepairLog "Stopping WinNAT so its dynamic exclusions can be rebuilt."
    Stop-Service WinNAT -Force
    $WinNat.WaitForStatus("Stopped", [TimeSpan]::FromSeconds(30))
  }

  if (-not (Test-ManagedReservation)) {
    Write-RepairLog "Adding a persistent administrator-managed reservation for the Supabase block."
    & netsh interface ipv4 add excludedportrange protocol=tcp startport=$StartPort numberofports=$PortCount store=persistent | Out-Null
    if ($LASTEXITCODE -ne 0) {
      throw "Windows could not add the managed Supabase port reservation."
    }
  }

  Write-RepairLog "Starting WinNAT."
  Start-Service WinNAT
  (Get-Service WinNAT).WaitForStatus("Running", [TimeSpan]::FromSeconds(30))
}
finally {
  if ($DockerWasRunning) {
    Write-RepairLog "Starting Docker Desktop again."
    docker desktop start | Out-Null
  }
}

if ($DockerWasRunning) {
  $Deadline = (Get-Date).AddMinutes(2)
  while ((Get-Date) -lt $Deadline) {
    $DesktopStatus = (docker desktop status 2>$null) -join "`n"
    if ($LASTEXITCODE -eq 0 -and $DesktopStatus -match "running") {
      break
    }
    Start-Sleep -Seconds 2
  }
  $DesktopStatus = (docker desktop status 2>$null) -join "`n"
  if ($LASTEXITCODE -ne 0 -or $DesktopStatus -notmatch "running") {
    throw "Docker Desktop did not become ready after the port repair."
  }
  Start-Sleep -Seconds 3
}

$DynamicConflicts = Get-ConflictingDynamicRanges
if ($DynamicConflicts.Count -gt 0) {
  $Description = ($DynamicConflicts | ForEach-Object { "$($_.Start)-$($_.End)" }) -join ", "
  throw "WinNAT still dynamically excludes the Supabase block: $Description."
}
if (-not (Test-ManagedReservation)) {
  throw "The managed Supabase port reservation was not retained."
}

Write-RepairLog "Supabase ports are protected from WinNAT dynamic allocation and ready for explicit bindings."
