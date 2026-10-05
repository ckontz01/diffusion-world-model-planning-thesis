# Attach one authenticated new OS disk. Never starts a guest or mounts its filesystem.
[CmdletBinding()]
param([switch]$Attach)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$c0DiskVMId=[guid]'8af7472f-a299-4d7d-b3c4-62e81e568de0'
$c0DiskVMName='WM-DIAG0-A2-C0-PREP-v1'
$c0DiskVMRoot='C:\Users\Chris\thesis-vm\wm-diag0-a2-c0-prep-v1'
$c0DiskPath='C:\Users\Chris\thesis-vm\wm-diag0-a2-c0-runtime-v1\os-image-v1\ubuntu-minimal.vhdx'
$c0DiskHash='5926B935C01C3627AB19066DD31DB6F4C9F8A6F304219751E4A1E24859E08CD8'
if (-not $Attach) { [pscustomobject]@{Mode='PLAN_ONLY';VMName=$c0DiskVMName;DiskPath=$c0DiskPath;StartsGuest=$false;ConnectsNetwork=$false;ChangesMemoryOrFirmware=$false;GateReady=$false} | ConvertTo-Json; return }
$c0DiskPrincipal=[Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $c0DiskPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Use your administrator PowerShell. No changes made.' }
if ($env:COMPUTERNAME -ne 'DESKTOP-7N8FN7C') { throw 'Wrong host. No changes made.' }
foreach ($c0DiskReceipt in @('OS-DISK-V1-STARTED.json','OS-DISK-V1-VERIFIED.json','OS-DISK-V1-FAILED.json')) { if (Test-Path -LiteralPath (Join-Path $c0DiskVMRoot $c0DiskReceipt)) { throw 'OS disk step already attempted; preserve/reconcile, do not rerun.' } }
foreach ($c0DiskTarget in @($c0DiskVMRoot,$c0DiskPath)) {
    $c0DiskItem=Get-Item -LiteralPath $c0DiskTarget -Force
    if (($c0DiskItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Redirected VM root or OS disk.' }
    $c0DiskAncestor=[IO.DirectoryInfo]::new([IO.Path]::GetDirectoryName($c0DiskTarget))
    while ($null -ne $c0DiskAncestor) { if (((Get-Item -LiteralPath $c0DiskAncestor.FullName -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Redirected target ancestor.' }; $c0DiskAncestor=$c0DiskAncestor.Parent }
}
if ((Get-FileHash -LiteralPath (Join-Path $c0DiskVMRoot 'FIRMWARE-CAPACITY-V1-VERIFIED.json')).Hash -ne 'FF886BBA40DD5813A53128D550FD2C1DE48CB20C1313BF444AE2C30A67D834D6' -or (Get-FileHash -LiteralPath (Join-Path $c0DiskVMRoot 'FIRMWARE-CAPACITY-V1-WATCHDOG.json')).Hash -ne '98AA4D581FB1B7AB596D1532FB169FCCFD359C275AC9DFEB5F1F4771A5FB7A54') { throw 'Firmware evidence identity mismatch.' }
$c0DiskVM=Get-VM -Id $c0DiskVMId
if ($c0DiskVM.Name -ne $c0DiskVMName -or $c0DiskVM.State.ToString() -ne 'Off' -or $c0DiskVM.Generation -ne 2 -or -not ([IO.Path]::GetFullPath($c0DiskVM.ConfigurationLocation)).StartsWith(($c0DiskVMRoot+'\'),[StringComparison]::OrdinalIgnoreCase)) { throw 'VM identity/state/path mismatch. No changes made.' }
if ((Get-VMProcessor -VM $c0DiskVM).Count -ne 4 -or (Get-VMMemory -VM $c0DiskVM).Startup -ne 2147483648 -or (Get-VMMemory -VM $c0DiskVM).DynamicMemoryEnabled) { throw 'Unexpected CPU/memory configuration.' }
if ($c0DiskVM.AutomaticStartAction.ToString() -ne 'Nothing' -or $c0DiskVM.AutomaticStopAction.ToString() -ne 'TurnOff' -or $c0DiskVM.AutomaticCheckpointsEnabled -or $c0DiskVM.CheckpointType.ToString() -ne 'Disabled') { throw 'Unexpected lifecycle settings.' }
if (@(Get-VMHardDiskDrive -VM $c0DiskVM).Count -ne 0 -or @(Get-VMDvdDrive -VM $c0DiskVM | Where-Object { -not [string]::IsNullOrEmpty($_.Path) }).Count -ne 0) { throw 'Unexpected existing disk/OS media. No changes made.' }
if (@(Get-VMNetworkAdapter -VM $c0DiskVM | Where-Object { -not [string]::IsNullOrEmpty($_.SwitchName) }).Count -ne 0 -or @(Get-VMIntegrationService -VM $c0DiskVM | Where-Object Enabled).Count -ne 0) { throw 'Unexpected network/integration connection. No changes made.' }
if ((Get-Item -LiteralPath $c0DiskPath).Length -ne 1157627904 -or (Get-FileHash -LiteralPath $c0DiskPath).Hash -ne $c0DiskHash) { throw 'OS disk byte/hash mismatch. No changes made.' }
$c0DiskInfo=Get-VHD -Path $c0DiskPath
if ($c0DiskInfo.VhdFormat.ToString() -ne 'VHDX' -or $c0DiskInfo.VhdType.ToString() -ne 'Dynamic' -or $c0DiskInfo.Size -ne 2361393152 -or $c0DiskInfo.BlockSize -ne 8388608 -or $c0DiskInfo.Attached -or -not [string]::IsNullOrEmpty($c0DiskInfo.ParentPath)) { throw 'Native OS disk format/state mismatch. No changes made.' }
function Write-C0DiskReceipt {
    param([string]$Leaf,[object]$Value)
    $c0DiskBytes=[Text.Encoding]::UTF8.GetBytes(($Value | ConvertTo-Json -Depth 6))
    if ($c0DiskBytes.Length -gt 32768) { throw 'Receipt exceeds 32 KiB.' }
    $c0DiskStream=[IO.File]::Open((Join-Path $c0DiskVMRoot $Leaf),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try { $c0DiskStream.Write($c0DiskBytes,0,$c0DiskBytes.Length) } finally { $c0DiskStream.Dispose() }
}
$c0DiskTimer=[Diagnostics.Stopwatch]::StartNew()
Write-C0DiskReceipt 'OS-DISK-V1-STARTED.json' ([ordered]@{RecordedUTC=[DateTime]::UtcNow.ToString('o');VMId=$c0DiskVMId.ToString();OSDiskPath=$c0DiskPath;OSDiskSHA256=$c0DiskHash;NoGuestStart=$true})
try {
    Add-VMHardDiskDrive -VM $c0DiskVM -ControllerType SCSI -ControllerNumber 0 -ControllerLocation 0 -Path $c0DiskPath
    $c0DiskAfter=Get-VM -Id $c0DiskVMId
    $c0DiskDrives=@(Get-VMHardDiskDrive -VM $c0DiskAfter)
    if ($c0DiskAfter.State.ToString() -ne 'Off' -or $c0DiskDrives.Count -ne 1 -or $c0DiskDrives[0].Path -ne $c0DiskPath -or $c0DiskDrives[0].ControllerType.ToString() -ne 'SCSI' -or $c0DiskDrives[0].ControllerNumber -ne 0 -or $c0DiskDrives[0].ControllerLocation -ne 0) { throw 'Stopped OS attachment readback mismatch.' }
    if ((Get-FileHash -LiteralPath $c0DiskPath).Hash -ne $c0DiskHash) { throw 'OS disk changed unexpectedly during stopped attachment.' }
    $c0DiskTimer.Stop()
    $c0DiskResult=[ordered]@{Study='WM-DIAG0-A2-C0';RecordedUTC=[DateTime]::UtcNow.ToString('o');Status='AUTHENTICATED_OS_DISK_ATTACHED_VM_OFF';VMId=$c0DiskVMId.ToString();State='Off';OSDiskPath=$c0DiskPath;OSDiskSHA256=$c0DiskHash;VirtualDiskBytes=$c0DiskInfo.Size;OSDiskFileBytes=1157627904;ConnectedNetworkAdapters=0;GuestBooted=$false;GuestRuntimeInstalled=$false;ElapsedSeconds=$c0DiskTimer.Elapsed.TotalSeconds;GateReady=$false;RealCheckpointLoadingAuthorized=$false}
    Write-C0DiskReceipt 'OS-DISK-V1-VERIFIED.json' $c0DiskResult
    [pscustomobject]$c0DiskResult | ConvertTo-Json
} catch {
    try { Write-C0DiskReceipt 'OS-DISK-V1-FAILED.json' ([ordered]@{Status='OS_DISK_PARTIAL_PRESERVED_NO_RETRY';VMId=$c0DiskVMId.ToString();Error=$_.Exception.Message;ElapsedSeconds=$c0DiskTimer.Elapsed.TotalSeconds;NoStartIssued=$true;GateReady=$false}) } catch { Write-Warning 'Failure receipt could not be written.' }
    throw
}
