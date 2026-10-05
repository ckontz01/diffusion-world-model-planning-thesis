# Finite safety helper for the empty, diskless preparation VM only.
[CmdletBinding()]
param([switch]$Run)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if (-not $Run) { [pscustomobject]@{Mode='PLAN_ONLY'; StopsOnlyDedicatedVM=$true; SecondsBeforeStop=25; Research=$false} | ConvertTo-Json; return }
$c0WatchId = [guid]'8af7472f-a299-4d7d-b3c4-62e81e568de0'
$c0WatchRoot = 'C:\Users\Chris\thesis-vm\wm-diag0-a2-c0-prep-v1'
$c0WatchReadyBytes = [Text.Encoding]::UTF8.GetBytes(([ordered]@{Mode='WATCHDOG_READY'; PID=$PID; VMId=$c0WatchId.ToString(); RecordedUTC=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json))
$c0WatchReadyFile = [IO.File]::Open((Join-Path $c0WatchRoot 'FIRMWARE-CAPACITY-V1-WATCHDOG-READY.json'),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try { $c0WatchReadyFile.Write($c0WatchReadyBytes,0,$c0WatchReadyBytes.Length) } finally { $c0WatchReadyFile.Dispose() }
Start-Sleep -Seconds 25
$c0WatchVM = Get-VM -Id $c0WatchId -ErrorAction Stop
if ($c0WatchVM.Name -ne 'WM-DIAG0-A2-C0-PREP-v1' -or -not ([IO.Path]::GetFullPath($c0WatchVM.ConfigurationLocation)).StartsWith(($c0WatchRoot+'\'),[StringComparison]::OrdinalIgnoreCase)) { throw 'Watchdog identity mismatch; no stop issued.' }
if ($c0WatchVM.State.ToString() -ne 'Off') {
    Stop-VM -VM $c0WatchVM -TurnOff -Force -Confirm:$false
}
$c0WatchAfter = Get-VM -Id $c0WatchId
$c0WatchBytes = [Text.Encoding]::UTF8.GetBytes(([ordered]@{RecordedUTC=[DateTime]::UtcNow.ToString('o'); VMId=$c0WatchId.ToString(); State=$c0WatchAfter.State.ToString(); Mode='FINITE_DISKLESS_PREPARATION_STOP_ONLY'} | ConvertTo-Json))
if ($c0WatchBytes.Length -gt 4096) { throw 'Watchdog receipt too large.' }
$c0WatchFile = [IO.File]::Open((Join-Path $c0WatchRoot 'FIRMWARE-CAPACITY-V1-WATCHDOG.json'),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try { $c0WatchFile.Write($c0WatchBytes,0,$c0WatchBytes.Length) } finally { $c0WatchFile.Dispose() }
