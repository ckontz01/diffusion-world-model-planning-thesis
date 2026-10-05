# Read-only inventory. Does not create/start VMs, install software, change policy,
# download files, copy checkpoints or modify the host/guest environment.
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$c0HostIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
$c0HostPrincipal = [Security.Principal.WindowsPrincipal]::new($c0HostIdentity)
$c0Elevated = $c0HostPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
$c0Computer = Get-CimInstance Win32_ComputerSystem
$c0OperatingSystem = Get-CimInstance Win32_OperatingSystem
$c0SystemVolume = Get-Volume -DriveLetter C
$c0AvailableBytes = [int64]$c0OperatingSystem.FreePhysicalMemory * 1024
$c0GuestMemoryBytes = [int64]8589934592
$c0HostHeadroomBytes = [int64]2147483648

$c0Inventory = [ordered]@{
    Study = 'WM-DIAG0-A2-C0'
    Mode = 'READ_ONLY_HOST_PREFLIGHT'
    RecordedUTC = [DateTime]::UtcNow.ToString('o')
    ElevatedAdministratorSession = $c0Elevated
    TotalPhysicalMemoryBytes = [int64]$c0Computer.TotalPhysicalMemory
    AvailablePhysicalMemoryBytes = $c0AvailableBytes
    LogicalProcessors = [int]$c0Computer.NumberOfLogicalProcessors
    GuestMemoryCeilingBytes = $c0GuestMemoryBytes
    ProposedHostHeadroomBytes = $c0HostHeadroomBytes
    EnoughFreeMemoryFor8GiBGuestAndHeadroom = ($c0AvailableBytes -ge ($c0GuestMemoryBytes + $c0HostHeadroomBytes))
    SystemVolumeFreeBytes = [int64]$c0SystemVolume.SizeRemaining
    ExecutionPolicy = @(Get-ExecutionPolicy -List | ForEach-Object {
        [pscustomobject]@{ Scope = $_.Scope.ToString(); ExecutionPolicy = $_.ExecutionPolicy.ToString() }
    })
    HyperVInventoryStatus = 'NOT_QUERIED_UNELEVATED'
    HyperVHost = $null
    VirtualMachines = @()
    GateReady = $false
    MutationsPerformed = 0
}

if ($c0Elevated) {
    try {
        $c0HostConfiguration = Get-VMHost -ErrorAction Stop
        $c0VirtualMachines = @(Get-VM -ErrorAction Stop)
        $c0Inventory.HyperVHost = $c0HostConfiguration | Select-Object ComputerName, VirtualMachinePath, VirtualHardDiskPath, EnableEnhancedSessionMode
        $c0Inventory.VirtualMachines = @($c0VirtualMachines | Select-Object Name, State, Generation, ProcessorCount, MemoryStartup, AutomaticStartAction, AutomaticStopAction)
        $c0Inventory.HyperVInventoryStatus = 'READ_SUCCEEDED'
    }
    catch {
        $c0Inventory.HyperVInventoryStatus = 'READ_FAILED'
        $c0Inventory.HyperVError = $_.Exception.Message
        $c0Inventory.HyperVErrorId = $_.FullyQualifiedErrorId
    }
}

[pscustomobject]$c0Inventory | ConvertTo-Json -Depth 6
