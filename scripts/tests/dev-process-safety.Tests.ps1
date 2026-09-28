# Load only function definitions so these tests never start/stop real dev servers.
$RepoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent

foreach ($ScriptName in @('dev.ps1', 'stop-dev.ps1')) {
  $ScriptPath = Join-Path (Join-Path $RepoRoot 'scripts') $ScriptName
  $Tokens = $null
  $ParseErrors = $null
  $Ast = [System.Management.Automation.Language.Parser]::ParseFile($ScriptPath, [ref]$Tokens, [ref]$ParseErrors)
  if ($ParseErrors.Count -gt 0) {
    throw "PowerShell parse errors in ${ScriptName}: $ParseErrors"
  }
  foreach ($Definition in $Ast.FindAll({ param($Node) $Node -is [System.Management.Automation.Language.FunctionDefinitionAst] }, $false)) {
    . ([scriptblock]::Create($Definition.Extent.Text))
  }

  Describe "$ScriptName process-tree protection" {
    BeforeEach {
      $script:StoppedIds = @()
      Mock Get-Process { [pscustomobject]@{ ProcessName = 'python'; SessionId = 1 } }
      Mock Get-CimInstance { }
      Mock Stop-Process { param($Id) $script:StoppedIds += $Id }
      Mock Write-Warning { }
      Mock Write-Host { }
    }

    It 'never walks or terminates the Windows System/Idle tree' {
      Stop-ProcessTree -ProcessId 0
      Stop-ProcessTree -ProcessId 4
      Assert-MockCalled Get-Process -Times 0 -Exactly -Scope It
      Assert-MockCalled Get-CimInstance -Times 0 -Exactly -Scope It
      Assert-MockCalled Stop-Process -Times 0 -Exactly -Scope It
    }

    It 'protects service processes before enumerating their children' {
      Mock Get-Process { [pscustomobject]@{ ProcessName = 'service'; SessionId = 0 } }
      Stop-ProcessTree -ProcessId 22000
      Assert-MockCalled Get-CimInstance -Times 0 -Exactly -Scope It
      Assert-MockCalled Stop-Process -Times 0 -Exactly -Scope It
    }

    It 'does not stop the PowerShell process executing the script' {
      Stop-ProcessTree -ProcessId $PID
      Assert-MockCalled Get-Process -Times 0 -Exactly -Scope It
      Assert-MockCalled Get-CimInstance -Times 0 -Exactly -Scope It
      Assert-MockCalled Stop-Process -Times 0 -Exactly -Scope It
    }

    It 'does not traverse stale descendants after the parent exits' {
      Mock Get-Process { $null }
      Stop-ProcessTree -ProcessId 22000
      Assert-MockCalled Get-CimInstance -Times 0 -Exactly -Scope It
      Assert-MockCalled Stop-Process -Times 0 -Exactly -Scope It
    }

    It 'still terminates a normal development child before its parent' {
      Mock Get-CimInstance {
        param($ClassName, $Filter)
        if ($Filter -eq 'ParentProcessId = 22000') { [pscustomobject]@{ ProcessId = 22001 } }
      }
      Stop-ProcessTree -ProcessId 22000
      ($script:StoppedIds -join ',') | Should Be '22001,22000'
    }

    It 'also protects services encountered within a development process tree' {
      Mock Get-Process {
        param($Id)
        [pscustomobject]@{ ProcessName = 'process'; SessionId = $(if ($Id -eq 22001) { 0 } else { 1 }) }
      }
      Mock Get-CimInstance {
        param($ClassName, $Filter)
        if ($Filter -eq 'ParentProcessId = 22000') { [pscustomobject]@{ ProcessId = 22001 } }
      }
      Stop-ProcessTree -ProcessId 22000
      ($script:StoppedIds -join ',') | Should Be '22000'
      Assert-MockCalled Get-CimInstance -Times 0 -Exactly -Scope It -ParameterFilter { $Filter -eq 'ParentProcessId = 22001' }
    }

    if ($ScriptName -eq 'dev.ps1') {
      It 'rejects a System-owned port when its application cannot be identified' {
        $KillExisting = $true
        Mock Get-ListeningProcessIds { @(4, 22000) }
        Mock Get-HttpListeningProcessIds { @() }
        { Assert-PortFree -Port 8000 } | Should Throw 'PID 4'
        Assert-MockCalled Get-CimInstance -Times 0 -Exactly -Scope It
        Assert-MockCalled Stop-Process -Times 0 -Exactly -Scope It
      }

      It 'releases the HTTP.sys application without stopping PID 4 or another queue' {
        $KillExisting = $true
        Mock Get-ListeningProcessIds { @(4) }
        Mock Get-HttpListeningProcessIds { @(22000) }
        Mock Wait-PortFree { $true }
        Assert-PortFree -Port 8000
        ($script:StoppedIds -join ',') | Should Be '22000'
        Assert-MockCalled Wait-PortFree -Times 1 -Exactly -Scope It -ParameterFilter { $Port -eq 8000 }
      }

      It 'does not release HTTP.sys applications without KillExisting' {
        $KillExisting = $false
        Mock Get-ListeningProcessIds { @(4) }
        Mock Get-HttpListeningProcessIds { @(22000) }
        { Assert-PortFree -Port 8000 } | Should Throw 'already occupied'
        Assert-MockCalled Get-HttpListeningProcessIds -Times 0 -Exactly -Scope It
        Assert-MockCalled Stop-Process -Times 0 -Exactly -Scope It
      }

      It 'still protects a system service identified through HTTP.sys' {
        $KillExisting = $true
        Mock Get-ListeningProcessIds { @(4) }
        Mock Get-HttpListeningProcessIds { @(22000) }
        Mock Get-Process { [pscustomobject]@{ ProcessName = 'service'; SessionId = 0 } }
        Mock Wait-PortFree { $false }
        { Assert-PortFree -Port 8000 } | Should Throw 'still occupied'
        Assert-MockCalled Stop-Process -Times 0 -Exactly -Scope It
      }

      It 'still force-stops an ordinary listener and checks that the port is free' {
        $KillExisting = $true
        Mock Get-ListeningProcessIds { @(22000) }
        Mock Get-HttpListeningProcessIds { throw 'Should not inspect HTTP.sys' }
        Mock Wait-PortFree { $true }
        Assert-PortFree -Port 8000
        ($script:StoppedIds -join ',') | Should Be '22000'
        Assert-MockCalled Wait-PortFree -Times 1 -Exactly -Scope It
      }
    }
  }
}

Describe 'HTTP.sys ownership parsing' {
  It 'extracts only exact-port owners from their own request queues' {
    $LASTEXITCODE = 0
    Mock netsh.exe {
      @'
Snapshot of HTTP service state (Request Queue View):
-----------------------------------------------------
Request queue name: other app
    Processes:
        ID: 22001, image: C:\other.exe
    Registered URLs:
        HTTP://LOCALHOST:8200/
Request queue name: target app
    Controller process ID: 22002
    Processes:
        ID: 22000, image: C:\target.exe
    URL group ID: FF00000710000001
        Registered URLs:
            HTTP://LOCALHOST:8000/
Request queue name: misleading URLs
    Processes:
        ID: 22003, image: C:\other.exe
    Registered URLs:
        HTTP://LOCALHOST:80000/
        HTTP://LOCALHOST:8200/path:8000/
        HTTP://[2001:db8:8000::1]:3000/
Request queue name: IPv6 and wildcard prefixes
    Processes:
        ID: 22004, image: C:\target2.exe
    Registered URLs:
        HTTP://[::1]:8000/
        HTTP://+:8000/
        HTTP://*:8000/
'@ -split "`n"
    }
    $ActualOwnerIds = @(Get-HttpListeningProcessIds -Port 8000)
    Assert-MockCalled netsh.exe -Times 1 -Exactly -Scope It
    ($ActualOwnerIds -join ',') | Should Be '22000,22004'
  }

  It 'fails closed if HTTP.sys inspection fails' {
    $LASTEXITCODE = 1
    Mock netsh.exe { 'The handle is invalid.' }
    { Get-HttpListeningProcessIds -Port 8000 } | Should Throw 'Could not identify'
  }
}
