# Independent finite safety helper. Only the exact disposable OS preparation VM.
[CmdletBinding()]
param([switch]$Run)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if (-not $Run) { [pscustomobject]@{Mode='PLAN_ONLY';StopDeadlineSeconds=120;Research=$false} | ConvertTo-Json; return }
$c0BootWatchId=[guid]'8af7472f-a299-4d7d-b3c4-62e81e568de0'
$c0BootWatchVMRoot='C:\Users\Chris\thesis-vm\wm-diag0-a2-c0-prep-v1'
$c0BootWatchRuntime='C:\Users\Chris\thesis-vm\wm-diag0-a2-c0-runtime-v1'
function Write-C0WatchReceipt([string]$Leaf,[object]$Value) {
    $c0WatchData=[Text.Encoding]::UTF8.GetBytes(($Value | ConvertTo-Json -Depth 5))
    if ($c0WatchData.Length -gt 4096) { throw 'Watchdog receipt cap.' }
    $c0WatchStream=[IO.File]::Open((Join-Path $c0BootWatchVMRoot $Leaf),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try { $c0WatchStream.Write($c0WatchData,0,$c0WatchData.Length) } finally { $c0WatchStream.Dispose() }
}
$c0BootWatchVM=Get-VM -Id $c0BootWatchId
if ($c0BootWatchVM.Name -ne 'WM-DIAG0-A2-C0-PREP-v1' -or $c0BootWatchVM.State.ToString() -ne 'Off' -or -not ([IO.Path]::GetFullPath($c0BootWatchVM.ConfigurationLocation)).StartsWith(($c0BootWatchVMRoot+'\'),[StringComparison]::OrdinalIgnoreCase)) { throw 'Watchdog initial identity/state mismatch.' }
Write-C0WatchReceipt 'GUEST-BOOT-V1-WATCHDOG-READY.json' ([ordered]@{PID=$PID;VMId=$c0BootWatchId.ToString();Mode='OFFLINE_BOOT_WATCHDOG_READY';RecordedUTC=[DateTime]::UtcNow.ToString('o')})
$c0BootWatchTimer=[Diagnostics.Stopwatch]::StartNew()
$c0BootWatchPeak=[int64]0
$c0BootWatchReason='120_SECOND_DEADLINE'
while ($c0BootWatchTimer.Elapsed.TotalSeconds -lt 120) {
    $c0BootWatchMembers=@(Get-ChildItem -LiteralPath $c0BootWatchVMRoot,$c0BootWatchRuntime -Recurse -Force)
    if (@($c0BootWatchMembers | Where-Object { ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 }).Count -gt 0) { $c0BootWatchReason='REDIRECTED_MEMBER'; break }
    $c0BootWatchSize=[int64](($c0BootWatchMembers | Where-Object { -not $_.PSIsContainer } | Measure-Object Length -Sum).Sum)
    $c0BootWatchPeak=[Math]::Max($c0BootWatchPeak,$c0BootWatchSize)
    if ($c0BootWatchSize -gt 3980000000) { $c0BootWatchReason='STORAGE_GUARD'; break }
    Start-Sleep -Milliseconds 500
}
$c0BootWatchVM=Get-VM -Id $c0BootWatchId
if ($c0BootWatchVM.Name -ne 'WM-DIAG0-A2-C0-PREP-v1' -or -not ([IO.Path]::GetFullPath($c0BootWatchVM.ConfigurationLocation)).StartsWith(($c0BootWatchVMRoot+'\'),[StringComparison]::OrdinalIgnoreCase)) { throw 'Watchdog final identity mismatch; no stop issued.' }
if ($c0BootWatchVM.State.ToString() -ne 'Off') { Stop-VM -VM $c0BootWatchVM -TurnOff -Force -Confirm:$false }
Write-C0WatchReceipt 'GUEST-BOOT-V1-WATCHDOG.json' ([ordered]@{VMId=$c0BootWatchId.ToString();State=(Get-VM -Id $c0BootWatchId).State.ToString();Reason=$c0BootWatchReason;MaximumObservedCombinedBytes=$c0BootWatchPeak;RecordedUTC=[DateTime]::UtcNow.ToString('o');ElapsedSeconds=$c0BootWatchTimer.Elapsed.TotalSeconds;Note='Sampled storage guard, not a hard filesystem quota.'})
