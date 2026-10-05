# One finite diskless firmware start/stop, not OS installation or conversion.
[CmdletBinding()]
param([switch]$Measure)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$c0ProbeName = 'WM-DIAG0-A2-C0-PREP-v1'
$c0ProbeId = [guid]'8af7472f-a299-4d7d-b3c4-62e81e568de0'
$c0ProbeRoot = 'C:\Users\Chris\thesis-vm\wm-diag0-a2-c0-prep-v1'
$c0ProbeLimit = [int64]2300000000
if (-not $Measure) {
    [pscustomobject]@{Mode='PLAN_ONLY'; VMName=$c0ProbeName; VMId=$c0ProbeId.ToString(); DisksAndOS='None'; ExpectedObservationSeconds=8; IndependentStopAtSeconds=25; MaximumVMDirectoryBytes=$c0ProbeLimit; MinimumFreeRAMBytes=4294967296; Downloads=$false; GateReady=$false; RealCheckpointLoadingAuthorized=$false} | ConvertTo-Json
    return
}
$c0ProbePrincipal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $c0ProbePrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Run from your administrator PowerShell. No changes made.' }
if ($env:COMPUTERNAME -ne 'DESKTOP-7N8FN7C') { throw 'Wrong host. No changes made.' }
if ([int64](Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory * 1024 -lt 4294967296) { throw 'Need at least 4 GiB free RAM: 2 GiB guest plus 2 GiB host headroom. Close unneeded applications yourself, then run once. No VM started.' }
if ((Get-PSDrive C).Free -lt $c0ProbeLimit) { throw 'Insufficient reserved disk headroom. No VM started.' }
foreach ($c0ProbeLeaf in @('FIRMWARE-CAPACITY-V1-STARTED.json','FIRMWARE-CAPACITY-V1-VERIFIED.json','FIRMWARE-CAPACITY-V1-FAILED.json','FIRMWARE-CAPACITY-V1-WATCHDOG.json','FIRMWARE-CAPACITY-V1-WATCHDOG-READY.json')) {
    if (Test-Path -LiteralPath (Join-Path $c0ProbeRoot $c0ProbeLeaf)) { throw 'A capacity probe already exists; preserve it and report. Do not rerun.' }
}
if ((Get-FileHash -LiteralPath (Join-Path $c0ProbeRoot 'REPAIR-R1-VERIFIED.json') -Algorithm SHA256).Hash -ne 'BE3AC75863C72CFD00F1BE6134420A83E048F2EE2DE5FB5ACFE31A16BF2E34DE') { throw 'Repair receipt identity mismatch. No changes made.' }
$c0ProbeAncestor = [IO.DirectoryInfo]::new($c0ProbeRoot)
while ($null -ne $c0ProbeAncestor) {
    if (((Get-Item -LiteralPath $c0ProbeAncestor.FullName -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Redirected VM root. No changes made.' }
    $c0ProbeAncestor = $c0ProbeAncestor.Parent
}
$c0ProbeVM = Get-VM -Id $c0ProbeId
if ($c0ProbeVM.Name -ne $c0ProbeName -or $c0ProbeVM.State.ToString() -ne 'Off' -or $c0ProbeVM.Generation -ne 2) { throw 'VM identity/state mismatch. No changes made.' }
foreach ($c0ProbeLocation in @($c0ProbeVM.ConfigurationLocation,$c0ProbeVM.SnapshotFileLocation,$c0ProbeVM.SmartPagingFilePath)) {
    $c0ProbeResolved = [IO.Path]::GetFullPath($c0ProbeLocation).TrimEnd('\')
    if ($c0ProbeResolved -ne $c0ProbeRoot -and -not $c0ProbeResolved.StartsWith(($c0ProbeRoot+'\'),[StringComparison]::OrdinalIgnoreCase)) { throw 'VM output location is outside dedicated root. No VM started.' }
}
$c0ProbeMemory = Get-VMMemory -VM $c0ProbeVM
if ($c0ProbeMemory.Startup -ne 2147483648 -or $c0ProbeMemory.DynamicMemoryEnabled -or (Get-VMProcessor -VM $c0ProbeVM).Count -ne 4) { throw 'Unexpected CPU or memory settings. No changes made.' }
if ($c0ProbeVM.AutomaticStartAction.ToString() -ne 'Nothing' -or $c0ProbeVM.AutomaticStopAction.ToString() -ne 'TurnOff' -or $c0ProbeVM.AutomaticCheckpointsEnabled -or $c0ProbeVM.CheckpointType.ToString() -ne 'Disabled') { throw 'Unexpected lifecycle settings. No changes made.' }
if (@(Get-VMHardDiskDrive -VM $c0ProbeVM).Count -ne 0 -or @(Get-VMDvdDrive -VM $c0ProbeVM | Where-Object { -not [string]::IsNullOrEmpty($_.Path) }).Count -ne 0) { throw 'Probe requires no disks or OS media. No VM started.' }
if (@(Get-VMNetworkAdapter -VM $c0ProbeVM | Where-Object { -not [string]::IsNullOrEmpty($_.SwitchName) }).Count -ne 0 -or @(Get-VMIntegrationService -VM $c0ProbeVM | Where-Object Enabled).Count -ne 0) { throw 'Probe requires disconnected network and disabled integration services. No VM started.' }
$c0ProbeWatch = Join-Path $PSScriptRoot 'Stop-Only-Watchdog.ps1'
if ((Get-FileHash -LiteralPath $c0ProbeWatch -Algorithm SHA256).Hash -ne '839095A3C895D4BA3864E46034899328AE109717B907DD3E59A16396FF240E12') { throw 'Watchdog source mismatch. No VM started.' }
function Write-C0ProbeReceipt {
    param([string]$Leaf,[object]$Value)
    $c0ProbeData = [Text.Encoding]::UTF8.GetBytes(($Value | ConvertTo-Json -Depth 8))
    if ($c0ProbeData.Length -gt 32768) { throw 'Receipt exceeds 32 KiB cap.' }
    $c0ProbeStream = [IO.File]::Open((Join-Path $c0ProbeRoot $Leaf),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try { $c0ProbeStream.Write($c0ProbeData,0,$c0ProbeData.Length) } finally { $c0ProbeStream.Dispose() }
}
function Get-C0ProbeFootprint {
    $c0ProbeMembers = @(Get-ChildItem -LiteralPath $c0ProbeRoot -Recurse -Force -ErrorAction Stop)
    if (@($c0ProbeMembers | Where-Object { ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 }).Count -ne 0) { throw 'Redirected VM member.' }
    [int64](($c0ProbeMembers | Where-Object { -not $_.PSIsContainer } | Measure-Object Length -Sum).Sum)
}
$c0ProbeTimer = [Diagnostics.Stopwatch]::StartNew()
$c0ProbePeak = Get-C0ProbeFootprint
Write-C0ProbeReceipt 'FIRMWARE-CAPACITY-V1-STARTED.json' ([ordered]@{RecordedUTC=[DateTime]::UtcNow.ToString('o'); VMId=$c0ProbeId.ToString(); BeforeBytes=$c0ProbePeak; LimitBytes=$c0ProbeLimit; NoDisksOrOS=$true; RealCheckpointLoadingAuthorized=$false})
try {
    # A separate hidden process remains alive if the measurement process exits.
    # No execution-policy bypass, elevation request, network or guest input.
    $c0ProbePowerShell = Join-Path $PSHOME 'powershell.exe'
    if (-not (Test-Path -LiteralPath $c0ProbePowerShell)) { $c0ProbePowerShell = Join-Path $PSHOME 'pwsh.exe' }
    $c0ProbeWatchProcess = Start-Process -FilePath $c0ProbePowerShell -ArgumentList @('-NoProfile','-NonInteractive','-File',('"'+$c0ProbeWatch+'"'),'-Run') -WindowStyle Hidden -PassThru
    $c0ProbeReadyPath = Join-Path $c0ProbeRoot 'FIRMWARE-CAPACITY-V1-WATCHDOG-READY.json'
    for ($c0ProbeReadyWait=0; $c0ProbeReadyWait -lt 12 -and -not (Test-Path -LiteralPath $c0ProbeReadyPath); $c0ProbeReadyWait++) { Start-Sleep -Milliseconds 250 }
    if ($c0ProbeWatchProcess.HasExited -or -not (Test-Path -LiteralPath $c0ProbeReadyPath)) { throw 'Watchdog readiness not established; no VM start issued.' }
    if ((Get-Item -LiteralPath $c0ProbeReadyPath).Length -gt 4096) { throw 'Watchdog readiness receipt too large.' }
    $c0ProbeReady = Get-Content -LiteralPath $c0ProbeReadyPath -Raw | ConvertFrom-Json
    if ($c0ProbeReady.PID -ne $c0ProbeWatchProcess.Id -or $c0ProbeReady.VMId -ne $c0ProbeId.ToString() -or $c0ProbeReady.Mode -ne 'WATCHDOG_READY') { throw 'Watchdog readiness identity mismatch.' }
    $c0ProbeStartJob = Start-VM -VM $c0ProbeVM -AsJob
    if ($null -eq (Wait-Job -Job $c0ProbeStartJob -Timeout 8)) { throw 'VM start exceeded 8 seconds; preserve evidence and stop.' }
    Receive-Job -Job $c0ProbeStartJob -ErrorAction Stop | Out-Null
    if ((Get-VM -Id $c0ProbeId).State.ToString() -ne 'Running') { throw 'VM did not reach Running.' }
    for ($c0ProbeSample=0; $c0ProbeSample -lt 8; $c0ProbeSample++) {
        $c0ProbeSize = Get-C0ProbeFootprint
        $c0ProbePeak = [Math]::Max($c0ProbePeak,$c0ProbeSize)
        if ($c0ProbeSize + 100000 -gt $c0ProbeLimit) { throw 'Running state exceeded reserved capacity. Preserve partials, do not retry.' }
        Start-Sleep -Seconds 1
    }
    Stop-VM -VM (Get-VM -Id $c0ProbeId) -TurnOff -Force -Confirm:$false
    if ((Get-VM -Id $c0ProbeId).State.ToString() -ne 'Off') { throw 'VM Off readback failed. Watchdog remains scheduled.' }
    $c0ProbeTimer.Stop()
    $c0ProbeResult = [ordered]@{Study='WM-DIAG0-A2-C0'; RecordedUTC=[DateTime]::UtcNow.ToString('o'); Status='DISKLESS_FIRMWARE_CAPACITY_MEASURED'; VMId=$c0ProbeId.ToString(); FinalState='Off'; MaximumObservedLogicalVMDirectoryBytes=$c0ProbePeak; AfterStopLogicalVMDirectoryBytes=(Get-C0ProbeFootprint); ReservationBytes=$c0ProbeLimit; ElapsedSeconds=$c0ProbeTimer.Elapsed.TotalSeconds; DiskOrOSInstalled=$false; NoNetworkOrGuestInput=$true; GateReady=$false; RealCheckpointLoadingAuthorized=$false; Note='Sampled logical file size, not a hard filesystem quota or proof of future guest/runtime footprint. Watchdog performs a separate Off readback at 25 seconds.'}
    Write-C0ProbeReceipt 'FIRMWARE-CAPACITY-V1-VERIFIED.json' $c0ProbeResult
    [pscustomobject]$c0ProbeResult | ConvertTo-Json
}
catch {
    $c0ProbeFailure = $_
    try { $c0ProbeStopTarget = Get-VM -Id $c0ProbeId; if ($c0ProbeStopTarget.State.ToString() -ne 'Off') { Stop-VM -VM $c0ProbeStopTarget -TurnOff -Force -Confirm:$false } } catch { Write-Warning 'Immediate stop failed; independent 25-second stop helper remains scheduled. Check this exact VM in Hyper-V.' }
    try { Write-C0ProbeReceipt 'FIRMWARE-CAPACITY-V1-FAILED.json' ([ordered]@{Status='CAPACITY_PROBE_PARTIAL_PRESERVED_NO_RETRY'; Error=$c0ProbeFailure.Exception.Message; ElapsedSeconds=$c0ProbeTimer.Elapsed.TotalSeconds; VMId=$c0ProbeId.ToString(); GateReady=$false}) } catch { Write-Warning 'Failure receipt could not be written.' }
    throw $c0ProbeFailure
}
