# One bounded, offline OS-only first boot. No research inputs or runtime install.
[CmdletBinding()]
param([switch]$Boot)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$c0BootId=[guid]'8af7472f-a299-4d7d-b3c4-62e81e568de0'
$c0BootName='WM-DIAG0-A2-C0-PREP-v1'
$c0BootVMRoot='C:\Users\Chris\thesis-vm\wm-diag0-a2-c0-prep-v1'
$c0BootRuntime='C:\Users\Chris\thesis-vm\wm-diag0-a2-c0-runtime-v1'
$c0BootOS=Join-Path $c0BootRuntime 'os-image-v1\ubuntu-minimal.vhdx'
$c0BootISO=Join-Path $c0BootRuntime 'guest-boot-v1\cidata.iso'
$c0BootExport=Join-Path $c0BootRuntime 'guest-boot-v1\boot-report.vhd'
$c0BootPython='C:\Users\Chris\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$c0BootValidator=Join-Path $PSScriptRoot 'validate_report.py'
$c0BootWatch=Join-Path $PSScriptRoot 'Stop-Offline-Boot.ps1'
if (-not $Boot) { [pscustomobject]@{Mode='PLAN_ONLY';VMName=$c0BootName;GuestMemoryBytes=1073741824;LogicalCPUs=4;Offline=$true;BootAttempts=1;StopDeadlineSeconds=120;CombinedStorageReservationBytes=4000000000;ReportDiskBytes=8388608;InstallsRuntime=$false;RealCheckpointLoadingAuthorized=$false;GateReady=$false} | ConvertTo-Json; return }
$c0BootPrincipal=[Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $c0BootPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Use your existing administrator PowerShell. No changes made.' }
if ($env:COMPUTERNAME -ne 'DESKTOP-7N8FN7C') { throw 'Wrong host.' }
if ([int64](Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory * 1024 -lt 3221225472) { throw 'Need 3 GiB free RAM: 1 GiB guest plus 2 GiB host headroom. No VM started.' }
if ((Get-PSDrive C).Free -lt 3000000000) { throw 'Need 3 GB free disk headroom. No VM started.' }
foreach ($c0BootLeaf in @('GUEST-BOOT-V1-STARTED.json','GUEST-BOOT-V1-VERIFIED.json','GUEST-BOOT-V1-FAILED.json','GUEST-BOOT-V1-WATCHDOG-READY.json','GUEST-BOOT-V1-WATCHDOG.json')) {
    if (Test-Path -LiteralPath (Join-Path $c0BootVMRoot $c0BootLeaf)) { throw 'Boot already attempted; preserve evidence and report, do not repeat.' }
}
if (Test-Path -LiteralPath $c0BootExport) { throw 'Existing report disk; preserve and reconcile. No overwrite.' }
foreach ($c0BootPath in @($c0BootVMRoot,$c0BootRuntime,$c0BootOS,$c0BootISO)) {
    $c0BootItem=Get-Item -LiteralPath $c0BootPath -Force
    if (($c0BootItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Redirected dedicated path.' }
    $c0BootAncestor=[IO.DirectoryInfo]::new([IO.Path]::GetDirectoryName($c0BootPath))
    while ($null -ne $c0BootAncestor) { if (((Get-Item -LiteralPath $c0BootAncestor.FullName -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Redirected ancestor.' }; $c0BootAncestor=$c0BootAncestor.Parent }
}
$c0BootPins=@(
    @((Join-Path $c0BootVMRoot 'OS-DISK-V1-VERIFIED.json'),'F283B2144CA29310714638C657C41E54EBFEF5FEBEDE2A66F2A2ED02198BFC86'),
    @($c0BootOS,'5926B935C01C3627AB19066DD31DB6F4C9F8A6F304219751E4A1E24859E08CD8'),
    @($c0BootISO,'2A7BF46E5AA5063FEE2F43ED5DA495DE39E6A71274C4B67EAC8A449AC6A70C53'),
    @($c0BootWatch,'36A9915DE6A167B9F58F205272A37FB58BBA9189FE920DA60B83C55F6972731C'),
    @($c0BootValidator,'22AD4AFCEE83AA2EDC83D63FEF7D180390D8C85AB2805A7E07BB07CD6DC29109'))
foreach ($c0BootPin in $c0BootPins) { if ((Get-FileHash -LiteralPath $c0BootPin[0]).Hash -ne $c0BootPin[1]) { throw 'Bound input/code identity mismatch.' } }
$c0BootVM=Get-VM -Id $c0BootId
if ($c0BootVM.Name -ne $c0BootName -or $c0BootVM.State.ToString() -ne 'Off' -or $c0BootVM.Generation -ne 2) { throw 'VM identity/state mismatch.' }
foreach ($c0BootLocation in @($c0BootVM.ConfigurationLocation,$c0BootVM.SnapshotFileLocation,$c0BootVM.SmartPagingFilePath)) {
    $c0BootResolved=[IO.Path]::GetFullPath($c0BootLocation).TrimEnd('\')
    if ($c0BootResolved -ne $c0BootVMRoot -and -not $c0BootResolved.StartsWith(($c0BootVMRoot+'\'),[StringComparison]::OrdinalIgnoreCase)) { throw 'Unexpected VM storage location.' }
}
if ((Get-VMProcessor -VM $c0BootVM).Count -ne 4 -or (Get-VMMemory -VM $c0BootVM).Startup -ne 2147483648 -or (Get-VMMemory -VM $c0BootVM).DynamicMemoryEnabled) { throw 'Unexpected prior CPU/memory configuration.' }
if ($c0BootVM.AutomaticStartAction.ToString() -ne 'Nothing' -or $c0BootVM.AutomaticStopAction.ToString() -ne 'TurnOff' -or $c0BootVM.AutomaticCheckpointsEnabled -or $c0BootVM.CheckpointType.ToString() -ne 'Disabled') { throw 'Unexpected lifecycle settings.' }
$c0BootDrives=@(Get-VMHardDiskDrive -VM $c0BootVM)
if ($c0BootDrives.Count -ne 1 -or $c0BootDrives[0].Path -ne $c0BootOS -or $c0BootDrives[0].ControllerNumber -ne 0 -or $c0BootDrives[0].ControllerLocation -ne 0 -or $c0BootDrives[0].ControllerType.ToString() -ne 'SCSI') { throw 'Unexpected disk attachment; no guest started.' }
$c0BootDVDs=@(Get-VMDvdDrive -VM $c0BootVM)
if ($c0BootDVDs.Count -gt 1 -or @($c0BootDVDs | Where-Object { -not [string]::IsNullOrEmpty($_.Path) -or $_.ControllerLocation -eq 10 }).Count -gt 0) { throw 'Unexpected DVD attachment.' }
if (@(Get-VMNetworkAdapter -VM $c0BootVM | Where-Object { -not [string]::IsNullOrEmpty($_.SwitchName) }).Count -ne 0 -or @(Get-VMIntegrationService -VM $c0BootVM | Where-Object Enabled).Count -ne 0) { throw 'Network/integration boundary mismatch.' }
$c0BootOSInfo=Get-VHD -Path $c0BootOS
if ($c0BootOSInfo.VhdFormat.ToString() -ne 'VHDX' -or $c0BootOSInfo.Size -ne 2361393152 -or $c0BootOSInfo.BlockSize -ne 8388608 -or -not [string]::IsNullOrEmpty($c0BootOSInfo.ParentPath)) { throw 'Unexpected OS disk format.' }
function Write-C0BootReceipt([string]$Leaf,[object]$Value) {
    $c0BootData=[Text.Encoding]::UTF8.GetBytes(($Value | ConvertTo-Json -Depth 8))
    if ($c0BootData.Length -gt 32768) { throw 'Receipt exceeds 32 KiB.' }
    $c0BootStream=[IO.File]::Open((Join-Path $c0BootVMRoot $Leaf),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try { $c0BootStream.Write($c0BootData,0,$c0BootData.Length) } finally { $c0BootStream.Dispose() }
}
function Get-C0BootFootprint {
    $c0BootMembers=@(Get-ChildItem -LiteralPath $c0BootVMRoot,$c0BootRuntime -Recurse -Force)
    if (@($c0BootMembers | Where-Object { ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 }).Count -gt 0) { throw 'Redirected output member.' }
    [int64](($c0BootMembers | Where-Object { -not $_.PSIsContainer } | Measure-Object Length -Sum).Sum)
}
$c0BootTimer=[Diagnostics.Stopwatch]::StartNew()
$c0BootBefore=Get-C0BootFootprint
if ($c0BootBefore -gt 1600000000) { throw 'Unexpected starting footprint; reconcile before boot.' }
$c0BootFirmwareBefore=Get-VMFirmware -VM $c0BootVM
Write-C0BootReceipt 'GUEST-BOOT-V1-STARTED.json' ([ordered]@{Study='WM-DIAG0-A2-C0';RecordedUTC=[DateTime]::UtcNow.ToString('o');VMId=$c0BootId.ToString();CombinedBytesBefore=$c0BootBefore;OSBuildDiskBeforeSHA256=$c0BootPins[1][1];OldMemoryBytes=2147483648;OldSecureBoot=$c0BootFirmwareBefore.SecureBoot.ToString();OldSecureBootTemplate=$c0BootFirmwareBefore.SecureBootTemplate;Inputs='Authenticated OS, two-member reviewed CIDATA ISO, empty fixed report disk only';RealCheckpointLoadingAuthorized=$false})
$c0BootStartJob=$null
try {
    # Only the new disposable OS-build disk is writable; original signed QCOW2 is preserved.
    New-VHD -Path $c0BootExport -Fixed -SizeBytes 8388608 | Out-Null
    $c0BootExportInfo=Get-VHD -Path $c0BootExport
    if ($c0BootExportInfo.VhdFormat.ToString() -ne 'VHD' -or $c0BootExportInfo.VhdType.ToString() -ne 'Fixed' -or $c0BootExportInfo.Size -ne 8388608 -or (Get-Item -LiteralPath $c0BootExport).Length -ne 8389120 -or -not [string]::IsNullOrEmpty($c0BootExportInfo.ParentPath)) { throw 'Unexpected fixed report container; no boot.' }
    Set-VMMemory -VMName $c0BootName -DynamicMemoryEnabled $false -StartupBytes 1073741824
    Add-VMHardDiskDrive -VM $c0BootVM -ControllerType SCSI -ControllerNumber 0 -ControllerLocation 10 -Path $c0BootExport
    if ($c0BootDVDs.Count -eq 0) { Add-VMDvdDrive -VM $c0BootVM -ControllerNumber 0 -ControllerLocation 20 -Path $c0BootISO } else { Set-VMDvdDrive -VMDvdDrive $c0BootDVDs[0] -Path $c0BootISO }
    # Keep Secure Boot ON using Microsoft's Linux-capable guest template; no host security changes.
    Set-VMFirmware -VM $c0BootVM -EnableSecureBoot On -SecureBootTemplate MicrosoftUEFICertificateAuthority -FirstBootDevice $c0BootDrives[0]
    if ((Get-VMMemory -VM $c0BootVM).Startup -ne 1073741824 -or (Get-VMMemory -VM $c0BootVM).DynamicMemoryEnabled -or (Get-VMFirmware -VM $c0BootVM).SecureBoot.ToString() -ne 'On') { throw 'Guest configuration readback mismatch.' }
    $c0BootNewDrives=@(Get-VMHardDiskDrive -VM $c0BootVM)
    $c0BootNewDVDs=@(Get-VMDvdDrive -VM $c0BootVM)
    if ($c0BootNewDrives.Count -ne 2 -or @($c0BootNewDrives | Where-Object { $_.Path -notin @($c0BootOS,$c0BootExport) }).Count -ne 0 -or $c0BootNewDVDs.Count -ne 1 -or $c0BootNewDVDs[0].Path -ne $c0BootISO) { throw 'Final input allowlist readback mismatch.' }
    $c0BootShell=Join-Path $PSHOME 'powershell.exe'
    if (-not (Test-Path -LiteralPath $c0BootShell)) { $c0BootShell=Join-Path $PSHOME 'pwsh.exe' }
    $c0BootWatchProcess=Start-Process -FilePath $c0BootShell -ArgumentList @('-NoProfile','-NonInteractive','-File',('"'+$c0BootWatch+'"'),'-Run') -WindowStyle Hidden -PassThru
    $c0BootReadyPath=Join-Path $c0BootVMRoot 'GUEST-BOOT-V1-WATCHDOG-READY.json'
    for ($c0BootWait=0; $c0BootWait -lt 20 -and -not (Test-Path -LiteralPath $c0BootReadyPath); $c0BootWait++) { Start-Sleep -Milliseconds 250 }
    if ($c0BootWatchProcess.HasExited -or -not (Test-Path -LiteralPath $c0BootReadyPath) -or (Get-Item -LiteralPath $c0BootReadyPath).Length -gt 4096) { throw 'Independent watchdog not ready; no boot.' }
    $c0BootReady=Get-Content -LiteralPath $c0BootReadyPath -Raw | ConvertFrom-Json
    if ($c0BootReady.PID -ne $c0BootWatchProcess.Id -or $c0BootReady.VMId -ne $c0BootId.ToString() -or $c0BootReady.Mode -ne 'OFFLINE_BOOT_WATCHDOG_READY') { throw 'Watchdog readiness identity mismatch; no boot.' }
    $c0BootWatchStart=[Diagnostics.Stopwatch]::StartNew()
    $c0BootStartJob=Start-VM -VM $c0BootVM -AsJob
    if ($null -eq (Wait-Job -Job $c0BootStartJob -Timeout 10)) { Stop-Job -Job $c0BootStartJob; throw 'Start timeout; no repeat. Independent stop remains armed.' }
    Receive-Job -Job $c0BootStartJob -ErrorAction Stop | Out-Null
    $c0BootReachedRunning=$false
    while ($c0BootWatchStart.Elapsed.TotalSeconds -lt 110) {
        $c0BootState=(Get-VM -Id $c0BootId).State.ToString()
        if ($c0BootState -eq 'Running') { $c0BootReachedRunning=$true }
        if ($c0BootReachedRunning -and $c0BootState -eq 'Off') { break }
        if ($c0BootWatchProcess.HasExited -or (Get-C0BootFootprint) -gt 3980000000) { throw 'Watchdog ended early or storage guard triggered.' }
        Start-Sleep -Milliseconds 500
    }
    if ((Get-VM -Id $c0BootId).State.ToString() -ne 'Off') { Stop-VM -VM (Get-VM -Id $c0BootId) -TurnOff -Force -Confirm:$false; throw 'Guest did not finish within bounded window. Preserve disk/report and diagnose; no retry.' }
    if (-not $c0BootReachedRunning) { throw 'Running state not independently observed.' }
    if (-not $c0BootWatchProcess.WaitForExit(130000)) { throw 'Watchdog completion unavailable; do not repeat boot.' }
    $c0BootWatchReceipt=Join-Path $c0BootVMRoot 'GUEST-BOOT-V1-WATCHDOG.json'
    if (-not (Test-Path -LiteralPath $c0BootWatchReceipt) -or (Get-Item -LiteralPath $c0BootWatchReceipt).Length -gt 4096) { throw 'Watchdog receipt unavailable.' }
    $c0BootWatchResult=Get-Content -LiteralPath $c0BootWatchReceipt -Raw | ConvertFrom-Json
    if ($c0BootWatchResult.State -ne 'Off' -or $c0BootWatchResult.Reason -ne '120_SECOND_DEADLINE' -or $c0BootWatchResult.VMId -ne $c0BootId.ToString()) { throw 'Independent Off/storage readback failed.' }
    # Fixed VHD payload and footer only. No filesystem mount or guest code executed on host.
    $c0BootRawReport=& $c0BootPython -I -B $c0BootValidator $c0BootExport
    if ($LASTEXITCODE -ne 0 -or [Text.Encoding]::UTF8.GetByteCount([string]$c0BootRawReport) -gt 32768) { throw 'Independent data-only report validation failed.' }
    $c0BootReport=[string]$c0BootRawReport | ConvertFrom-Json
    $c0BootFinalBytes=Get-C0BootFootprint
    if ($c0BootFinalBytes -gt 3980000000) { throw 'Final storage bound exceeded.' }
    $c0BootFinalOSHash=(Get-FileHash -LiteralPath $c0BootOS).Hash
    $c0BootTimer.Stop()
    $c0BootResult=[ordered]@{Study='WM-DIAG0-A2-C0';RecordedUTC=[DateTime]::UtcNow.ToString('o');Status='OFFLINE_OS_FIRST_BOOT_AND_DATA_REPORT_VERIFIED';VMId=$c0BootId.ToString();FinalState=(Get-VM -Id $c0BootId).State.ToString();GuestReport=$c0BootReport;LogicalCPUs=4;StaticMemoryBytes=1073741824;ConnectedNetworkAdapters=0;EnabledIntegrationServices=0;MaximumObservedCombinedBytes=$c0BootWatchResult.MaximumObservedCombinedBytes;AfterStopCombinedBytes=$c0BootFinalBytes;OSBuildDiskAfterSHA256=$c0BootFinalOSHash;OriginalSignedOSAcquisitionPreserved=$true;ReportDiskSHA256=(Get-FileHash -LiteralPath $c0BootExport).Hash;ElapsedSeconds=$c0BootTimer.Elapsed.TotalSeconds;RuntimeInstalled=$false;ActualArtificialCheckpointGateTested=$false;GateReady=$false;RealCheckpointLoadingAuthorized=$false;Note='Trusted OS-only boot. Report channel validated as data, not attestation of full conversion isolation. Storage sampled, not a hard host filesystem quota.'}
    if ($c0BootResult.FinalState -ne 'Off') { throw 'Final Off readback failed.' }
    Write-C0BootReceipt 'GUEST-BOOT-V1-VERIFIED.json' $c0BootResult
    [pscustomobject]$c0BootResult | ConvertTo-Json -Depth 8
} catch {
    $c0BootFailure=$_
    if ($null -ne $c0BootStartJob -and $c0BootStartJob.State -eq 'Running') { try { Stop-Job -Job $c0BootStartJob } catch { Write-Warning 'Start job cancellation failed; watchdog remains armed.' } }
    try { $c0BootStopTarget=Get-VM -Id $c0BootId; if ($c0BootStopTarget.State.ToString() -ne 'Off') { Stop-VM -VM $c0BootStopTarget -TurnOff -Force -Confirm:$false } } catch { Write-Warning 'Immediate stop failed. Check this exact VM; independent watchdog remains armed if its readiness was established.' }
    try { Write-C0BootReceipt 'GUEST-BOOT-V1-FAILED.json' ([ordered]@{Status='OFFLINE_BOOT_PARTIAL_PRESERVED_NO_RETRY';Error=$c0BootFailure.Exception.Message;VMId=$c0BootId.ToString();ElapsedSeconds=$c0BootTimer.Elapsed.TotalSeconds;GateReady=$false;RealCheckpointLoadingAuthorized=$false}) } catch { Write-Warning 'Failure receipt unavailable.' }
    throw $c0BootFailure
}
