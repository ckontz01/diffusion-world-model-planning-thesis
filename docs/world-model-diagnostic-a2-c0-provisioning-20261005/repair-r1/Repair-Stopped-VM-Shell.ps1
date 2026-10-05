# One targeted repair of the existing failed shell. Never creates/starts/deletes a VM.
[CmdletBinding()]
param([switch]$Repair)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$c0R1Name = 'WM-DIAG0-A2-C0-PREP-v1'
$c0R1Id = [guid]'8af7472f-a299-4d7d-b3c4-62e81e568de0'
$c0R1Root = 'C:\Users\Chris\thesis-vm\wm-diag0-a2-c0-prep-v1'
$c0R1Memory = [int64]2147483648
if (-not $Repair) {
    [pscustomobject]@{ Mode = 'PLAN_ONLY'; VMName = $c0R1Name; VMId = $c0R1Id.ToString(); Repair = 'Static StartupBytes only; finish disconnected-adapter/integration-service configuration and readback'; CreatesVM = $false; StartsVM = $false; GateReady = $false } | ConvertTo-Json
    return
}
$c0R1Principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $c0R1Principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Use your administrator PowerShell window. No changes made.' }
if ($env:COMPUTERNAME -ne 'DESKTOP-7N8FN7C') { throw 'Unexpected host; no changes made.' }
foreach ($c0R1Leaf in @('REPAIR-R1-STARTED.json', 'REPAIR-R1-VERIFIED.json', 'REPAIR-R1-FAILED.json', 'CREATION-VERIFIED.json')) {
    if (Test-Path -LiteralPath (Join-Path $c0R1Root $c0R1Leaf)) { throw 'Repair/verification receipt already exists. Preserve it; do not rerun.' }
}
$c0R1StartedPath = Join-Path $c0R1Root 'CREATION-STARTED.json'
$c0R1FailedPath = Join-Path $c0R1Root 'CREATION-FAILED.json'
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $c0R1StartedPath).Hash -ne '56DAACF575FF05E83FFDB8955D37F4A8E845264A2C025BA92E97DCE838A6A89E' -or (Get-FileHash -Algorithm SHA256 -LiteralPath $c0R1FailedPath).Hash -ne 'AFA91473350E898CFDDA2039EF2CD18235129620D58D9B41D8087127630215F0') { throw 'Historical receipt identity mismatch; no changes made.' }
$c0R1Ancestor = [IO.DirectoryInfo]::new($c0R1Root)
while ($null -ne $c0R1Ancestor) {
    $c0R1Item = Get-Item -LiteralPath $c0R1Ancestor.FullName -Force
    if (($c0R1Item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Redirected root ancestor; no changes made.' }
    $c0R1Ancestor = $c0R1Ancestor.Parent
}
$c0R1VM = Get-VM -Id $c0R1Id -ErrorAction Stop
$c0R1Configuration = [IO.Path]::GetFullPath($c0R1VM.ConfigurationLocation).TrimEnd('\')
if ($c0R1VM.Name -ne $c0R1Name -or $c0R1VM.State.ToString() -ne 'Off' -or $c0R1VM.Generation -ne 2 -or -not $c0R1Configuration.StartsWith(($c0R1Root + '\'), [StringComparison]::OrdinalIgnoreCase)) { throw 'Existing VM identity/state/path mismatch. No changes made.' }
if ((Get-VMProcessor -VM $c0R1VM).Count -ne 4) { throw 'Unexpected CPU count; no changes made.' }
if ($c0R1VM.AutomaticStartAction.ToString() -ne 'Nothing' -or $c0R1VM.AutomaticStopAction.ToString() -ne 'TurnOff' -or $c0R1VM.AutomaticCheckpointsEnabled -or $c0R1VM.CheckpointType.ToString() -ne 'Disabled') { throw 'Unexpected lifecycle/checkpoint state; no changes made.' }
if (@(Get-VMHardDiskDrive -VM $c0R1VM).Count -ne 0 -or @(Get-VMDvdDrive -VM $c0R1VM | Where-Object { -not [string]::IsNullOrEmpty($_.Path) }).Count -ne 0) { throw 'Unexpected disk or mounted media; no changes made.' }
if (@(Get-VMNetworkAdapter -VM $c0R1VM | Where-Object { -not [string]::IsNullOrEmpty($_.SwitchName) }).Count -ne 0) { throw 'Unexpected network attachment; no changes made.' }

function Write-C0R1Receipt {
    param([string]$Leaf, [object]$Value)
    $c0R1Bytes = [Text.Encoding]::UTF8.GetBytes(($Value | ConvertTo-Json -Depth 6))
    if ($c0R1Bytes.Length -gt 32768) { throw 'Receipt exceeds 32 KiB cap.' }
    $c0R1File = [IO.File]::Open((Join-Path $c0R1Root $Leaf), [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    try { $c0R1File.Write($c0R1Bytes, 0, $c0R1Bytes.Length) } finally { $c0R1File.Dispose() }
}
$c0R1Timer = [Diagnostics.Stopwatch]::StartNew()
Write-C0R1Receipt -Leaf 'REPAIR-R1-STARTED.json' -Value ([ordered]@{ VMName = $c0R1Name; VMId = $c0R1Id.ToString(); DiagnosedFault = 'Static memory call included dynamic-only bounds'; NoCreateOrStart = $true; GateReady = $false })
try {
    # MinimumBytes/MaximumBytes/Buffer apply only to dynamic memory. Static total
    # allocation is StartupBytes; do not enable dynamic memory to hide the error.
    Set-VMMemory -VM $c0R1VM -DynamicMemoryEnabled $false -StartupBytes $c0R1Memory
    Get-VMNetworkAdapter -VM $c0R1VM | Disconnect-VMNetworkAdapter
    Get-VMIntegrationService -VM $c0R1VM | Disable-VMIntegrationService
    $c0R1After = Get-VM -Id $c0R1Id
    $c0R1MemoryAfter = Get-VMMemory -VM $c0R1After
    $c0R1CPUAfter = Get-VMProcessor -VM $c0R1After
    if ($c0R1After.State.ToString() -ne 'Off' -or $c0R1After.Name -ne $c0R1Name -or $c0R1MemoryAfter.Startup -ne $c0R1Memory -or $c0R1MemoryAfter.DynamicMemoryEnabled -or $c0R1CPUAfter.Count -ne 4) { throw 'State/memory/CPU readback mismatch.' }
    if (@(Get-VMNetworkAdapter -VM $c0R1After | Where-Object { -not [string]::IsNullOrEmpty($_.SwitchName) }).Count -ne 0 -or @(Get-VMIntegrationService -VM $c0R1After | Where-Object Enabled).Count -ne 0) { throw 'Network/integration-service readback mismatch.' }
    if (@(Get-VMHardDiskDrive -VM $c0R1After).Count -ne 0 -or @(Get-VMDvdDrive -VM $c0R1After | Where-Object { -not [string]::IsNullOrEmpty($_.Path) }).Count -ne 0) { throw 'Unexpected disk/media after repair.' }
    if ($c0R1After.AutomaticStartAction.ToString() -ne 'Nothing' -or $c0R1After.AutomaticStopAction.ToString() -ne 'TurnOff' -or $c0R1After.AutomaticCheckpointsEnabled -or $c0R1After.CheckpointType.ToString() -ne 'Disabled') { throw 'Lifecycle/checkpoint readback mismatch.' }
    $c0R1Members = @(Get-ChildItem -LiteralPath $c0R1Root -Recurse -Force -ErrorAction Stop)
    if (@($c0R1Members | Where-Object { ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 }).Count -ne 0) { throw 'Unexpected redirected VM member.' }
    $c0R1Size = [int64](($c0R1Members | Where-Object { -not $_.PSIsContainer } | Measure-Object Length -Sum).Sum)
    if ($c0R1Size + 32768 -gt 64000000) { throw 'Metadata exceeds original reservation; preserve partials and report.' }
    $c0R1Timer.Stop()
    $c0R1Result = [ordered]@{ Study = 'WM-DIAG0-A2-C0'; RecordedUTC = [DateTime]::UtcNow.ToString('o'); Status = 'EXISTING_STOPPED_VM_SHELL_REPAIRED'; VMName = $c0R1Name; VMId = $c0R1Id.ToString(); State = $c0R1After.State.ToString(); LogicalCPUs = $c0R1CPUAfter.Count; MemoryBytes = $c0R1MemoryAfter.Startup; DynamicMemory = $c0R1MemoryAfter.DynamicMemoryEnabled; ConnectedNetworkAdapters = 0; EnabledIntegrationServices = 0; AttachedDisks = 0; MountedOSMedia = 0; MetadataBytesBeforeFinalReceipt = $c0R1Size; ElapsedRepairSeconds = $c0R1Timer.Elapsed.TotalSeconds; OriginalFailurePreserved = $true; OSAndRuntimeInstalled = $false; GateReady = $false; RealCheckpointLoadingAuthorized = $false }
    Write-C0R1Receipt -Leaf 'REPAIR-R1-VERIFIED.json' -Value $c0R1Result
    [pscustomobject]$c0R1Result | ConvertTo-Json
}
catch {
    $c0R1Timer.Stop()
    try { Write-C0R1Receipt -Leaf 'REPAIR-R1-FAILED.json' -Value ([ordered]@{ Status = 'REPAIR_PARTIAL_PRESERVED_DO_NOT_RETRY'; Error = $_.Exception.Message; ErrorId = $_.FullyQualifiedErrorId; ElapsedSeconds = $c0R1Timer.Elapsed.TotalSeconds; VMId = $c0R1Id.ToString(); GateReady = $false }) }
    catch { Write-Warning ('Repair failure receipt could not be written: ' + $_.Exception.Message) }
    throw
}
