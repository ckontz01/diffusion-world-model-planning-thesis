# Authorized VM preparation only. No OS/disk/download/start/checkpoint/model work.
# Default is a non-mutating plan; -Create performs one exclusive local creation.
[CmdletBinding()]
param([switch]$Create)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$c0VmName = 'WM-DIAG0-A2-C0-PREP-v1'
$c0VmRoot = 'C:\Users\Chris\thesis-vm\wm-diag0-a2-c0-prep-v1'
$c0VmMemory = [int64]2147483648
$c0MetadataReservation = [int64]64000000
$c0Plan = [ordered]@{
    Study = 'WM-DIAG0-A2-C0'
    VMName = $c0VmName
    Root = $c0VmRoot
    Mode = 'PLAN_ONLY'
    MemoryBytes = $c0VmMemory
    LogicalCPUs = 4
    Generation = 2
    OS = 'NONE'
    Disk = 'NONE'
    Network = 'DISCONNECTED'
    StartVM = $false
    GateReady = $false
    MetadataReservationBytes = $c0MetadataReservation
}
if (-not $Create) {
    [pscustomobject]$c0Plan | ConvertTo-Json
    return
}

# No self-elevation, policy changes, alternative credentials or remote session.
$c0Identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$c0Principal = [Security.Principal.WindowsPrincipal]::new($c0Identity)
if (-not $c0Principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Use your administrator PowerShell window. No changes were made.'
}
if ($env:COMPUTERNAME -ne 'DESKTOP-7N8FN7C') { throw 'Unexpected host; no changes made.' }
$c0ExistingVMs = @(Get-VM -ErrorAction Stop)
if (@($c0ExistingVMs | Where-Object Name -eq $c0VmName).Count -ne 0) {
    throw 'Target VM already exists. Do not rerun or overwrite it; return its status.'
}
if (Test-Path -LiteralPath $c0VmRoot) {
    throw 'Target directory already exists. Preserve it and return its contents/status; do not retry.'
}
# Reject redirected ancestors before creating an exact dedicated target.
$c0Ancestor = [IO.DirectoryInfo]::new($c0VmRoot).Parent
while ($null -ne $c0Ancestor) {
    if (Test-Path -LiteralPath $c0Ancestor.FullName) {
        $c0AncestorItem = Get-Item -LiteralPath $c0Ancestor.FullName -Force
        if (($c0AncestorItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw 'Target ancestor is a reparse point; no changes made.'
        }
    }
    $c0Ancestor = $c0Ancestor.Parent
}
$c0CurrentOS = Get-CimInstance Win32_OperatingSystem
if (([int64]$c0CurrentOS.FreePhysicalMemory * 1024) -lt 4294967296) {
    throw 'Less than 4 GiB RAM free (2 GiB guest + 2 GiB host headroom); no changes made.'
}
if ((Get-Volume -DriveLetter C).SizeRemaining -lt 1073741824) {
    throw 'Less than 1 GiB free on C; no changes made.'
}

function Write-C0ExclusiveReceipt {
    param([string]$Leaf, [object]$Value)
    $c0ReceiptBytes = [Text.Encoding]::UTF8.GetBytes(($Value | ConvertTo-Json -Depth 6))
    if ($c0ReceiptBytes.Length -gt 32768) { throw 'Receipt exceeds its 32 KiB cap.' }
    $c0ReceiptFile = [IO.File]::Open((Join-Path $c0VmRoot $Leaf), [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    try { $c0ReceiptFile.Write($c0ReceiptBytes, 0, $c0ReceiptBytes.Length) }
    finally { $c0ReceiptFile.Dispose() }
}

$c0ParentRoot = Split-Path -Parent $c0VmRoot
if (-not (Test-Path -LiteralPath $c0ParentRoot)) {
    $null = New-Item -ItemType Directory -Path $c0ParentRoot -ErrorAction Stop
}
$null = New-Item -ItemType Directory -Path $c0VmRoot -ErrorAction Stop
$c0Timer = [Diagnostics.Stopwatch]::StartNew()
$c0Plan.Mode = 'CREATION_STARTED'
Write-C0ExclusiveReceipt -Leaf 'CREATION-STARTED.json' -Value $c0Plan
try {
    # No existing disk, SwitchName, credentials, clone, remote host or OS media.
    $null = New-VM -Name $c0VmName -Generation 2 -NoVHD -MemoryStartupBytes $c0VmMemory -Path $c0VmRoot -ErrorAction Stop
    Set-VM -Name $c0VmName -AutomaticStartAction Nothing -AutomaticStopAction TurnOff -AutomaticCheckpointsEnabled $false -CheckpointType Disabled -SnapshotFileLocation $c0VmRoot -SmartPagingFilePath $c0VmRoot
    Set-VMProcessor -VMName $c0VmName -Count 4 -ExposeVirtualizationExtensions $false
    Set-VMMemory -VMName $c0VmName -DynamicMemoryEnabled $false -StartupBytes $c0VmMemory -MinimumBytes $c0VmMemory -MaximumBytes $c0VmMemory
    Get-VMNetworkAdapter -VMName $c0VmName | Disconnect-VMNetworkAdapter
    Get-VMIntegrationService -VMName $c0VmName | Disable-VMIntegrationService

    $c0CreatedVM = Get-VM -Name $c0VmName
    $c0CreatedMemory = Get-VMMemory -VMName $c0VmName
    $c0CreatedCPU = Get-VMProcessor -VMName $c0VmName
    $c0Adapters = @(Get-VMNetworkAdapter -VMName $c0VmName)
    $c0Disks = @(Get-VMHardDiskDrive -VMName $c0VmName)
    $c0DVDs = @(Get-VMDvdDrive -VMName $c0VmName)
    $c0Services = @(Get-VMIntegrationService -VMName $c0VmName)
    $c0VMFiles = @(Get-ChildItem -LiteralPath $c0VmRoot -Recurse -Force -ErrorAction Stop)
    if (@($c0VMFiles | Where-Object { ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 }).Count -ne 0) { throw 'Unexpected redirected VM member.' }
    $c0SizeMeasure = $c0VMFiles | Where-Object { -not $_.PSIsContainer } | Measure-Object -Property Length -Sum
    $c0MetadataBytes = [int64]$c0SizeMeasure.Sum
    if ($c0CreatedVM.State.ToString() -ne 'Off') { throw 'VM is unexpectedly not Off. Do not start or retry.' }
    if ($c0CreatedCPU.Count -ne 4 -or $c0CreatedMemory.Startup -ne $c0VmMemory -or $c0CreatedMemory.DynamicMemoryEnabled) { throw 'CPU/memory readback mismatch.' }
    if ($c0CreatedVM.AutomaticStartAction.ToString() -ne 'Nothing' -or $c0CreatedVM.AutomaticStopAction.ToString() -ne 'TurnOff' -or $c0CreatedVM.AutomaticCheckpointsEnabled -or $c0CreatedVM.CheckpointType.ToString() -ne 'Disabled') { throw 'Automatic lifecycle/checkpoint readback mismatch.' }
    if (@($c0Adapters | Where-Object { -not [string]::IsNullOrEmpty($_.SwitchName) }).Count -ne 0) { throw 'Unexpected network connection.' }
    if ($c0Disks.Count -ne 0 -or @($c0DVDs | Where-Object { -not [string]::IsNullOrEmpty($_.Path) }).Count -ne 0) { throw 'Unexpected disk or mounted media.' }
    if (@($c0Services | Where-Object Enabled).Count -ne 0) { throw 'Unexpected enabled integration service.' }
    if ($c0MetadataBytes + 32768 -gt $c0MetadataReservation) { throw 'VM metadata exceeds 64 MB reservation. Preserve partials and report; no automatic cleanup/retry.' }
    $c0Timer.Stop()
    $c0Result = [ordered]@{
        Study = 'WM-DIAG0-A2-C0'
        RecordedUTC = [DateTime]::UtcNow.ToString('o')
        Status = 'STOPPED_EMPTY_VM_SHELL_CREATED'
        VMName = $c0VmName
        VMId = $c0CreatedVM.Id.ToString()
        Root = $c0VmRoot
        State = $c0CreatedVM.State.ToString()
        LogicalCPUs = $c0CreatedCPU.Count
        MemoryBytes = $c0CreatedMemory.Startup
        DynamicMemory = $c0CreatedMemory.DynamicMemoryEnabled
        ConnectedNetworkAdapters = 0
        AttachedDisks = 0
        MountedOSMedia = 0
        EnabledIntegrationServices = 0
        MeasuredMetadataBytesBeforeFinalReceipt = $c0MetadataBytes
        ElapsedCreationSeconds = $c0Timer.Elapsed.TotalSeconds
        GateReady = $false
        OSAndRuntimeInstalled = $false
        RealCheckpointLoadingAuthorized = $false
    }
    Write-C0ExclusiveReceipt -Leaf 'CREATION-VERIFIED.json' -Value $c0Result
    [pscustomobject]$c0Result | ConvertTo-Json
}
catch {
    $c0Timer.Stop()
    $c0Failure = [ordered]@{ Status = 'PARTIAL_CREATION_PRESERVED_DO_NOT_RETRY'; Error = $_.Exception.Message; ErrorId = $_.FullyQualifiedErrorId; VMName = $c0VmName; Root = $c0VmRoot; ElapsedSeconds = $c0Timer.Elapsed.TotalSeconds; GateReady = $false }
    try { Write-C0ExclusiveReceipt -Leaf 'CREATION-FAILED.json' -Value $c0Failure }
    catch { Write-Warning ('Failure receipt could not be written: ' + $_.Exception.Message) }
    throw
}
