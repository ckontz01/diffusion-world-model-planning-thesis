param(
    [Parameter(Mandatory=$true)][string]$Approval,
    [Parameter(Mandatory=$true)][string]$ApprovalSha,
    [Parameter(Mandatory=$true)][string]$Control,
    [switch]$CheckOnly
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
# Native Windows only: do not call this through WSL interop.
if (-not $IsWindows) { throw 'Native Windows PowerShell required' }
$expectedVolume = '\\?\Volume{0a2f1ba9-0000-0000-0000-100000000000}\'
$sourceSha = '70e3838c83561b8b24ea2f2c2f6875c2674d7c9b391e682c1023ba3641238975'
$expectedControl = 'D:\THESIS-BACKUPS\cvl-bp1-recovery2-20260917\controls'
if ([IO.Path]::GetFullPath($Control) -ne $expectedControl) { throw 'Exact external control path required' }
if ((Get-FileHash -LiteralPath $Approval -Algorithm SHA256).Hash.ToLowerInvariant() -ne $ApprovalSha) { throw 'Approval hash mismatch' }
$approvalValue = Get-Content -Raw -LiteralPath $Approval | ConvertFrom-Json
if ($approvalValue.researcher_approved -ne $true -or $approvalValue.source_sha256 -ne $sourceSha -or
    $approvalValue.external_volume_id -ne $expectedVolume -or $approvalValue.completed_prefix -ne 148 -or
    $approvalValue.max_additional_replacement_attempts -ne 0) { throw 'Exact approved recovery scope required' }

function Read-ExternalVolume {
    $volume = Get-Volume -DriveLetter D
    if ($volume.FileSystemLabel -ne 'THESIS_SSD' -or $volume.UniqueId -ne $expectedVolume -or
        $volume.FileSystemType -ne 'NTFS' -or $volume.SizeRemaining -lt 40000000000) {
        throw 'Wrong/absent external volume or insufficient headroom; no fallback'
    }
    return $volume
}

function Write-NewJson([string]$Path, $Value) {
    $bytes = [Text.UTF8Encoding]::new($false).GetBytes(($Value | ConvertTo-Json -Depth 8 -Compress))
    $stream = [IO.File]::Open($Path, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::Read)
    try { $stream.Write($bytes, 0, $bytes.Length); $stream.Flush($true) } finally { $stream.Dispose() }
}

$volume = Read-ExternalVolume
if ($CheckOnly) { 'Native volume identity and 40GB reserve: PASS'; return }
if (Test-Path -LiteralPath (Join-Path $Control 'NATIVE-VOLUME-HALT.json')) { throw 'Existing halt record' }
Write-NewJson (Join-Path $Control 'NATIVE-VOLUME-CLAIM.json') @{
    approval_sha256=$ApprovalSha; pid=$PID; automatic_restart=$false
}
$deadline = [DateTimeOffset]::UtcNow.AddDays(7)
try {
    while ([DateTimeOffset]::UtcNow -lt $deadline) {
        if (Test-Path -LiteralPath (Join-Path $Control 'NATIVE-VOLUME-HALT.json')) { return }
        $volume = Read-ExternalVolume
        $record = @{
            approval_sha256=$ApprovalSha; source_sha256=$sourceSha; volume_id=$volume.UniqueId
            volume_label=$volume.FileSystemLabel; free_bytes=$volume.SizeRemaining
            utc=([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()/1000.0); native_windows=$true
        }
        $next = Join-Path $Control 'NATIVE-VOLUME-LIVE.json.next'
        Write-NewJson $next $record
        [IO.File]::Move($next, (Join-Path $Control 'NATIVE-VOLUME-LIVE.json'), $true)
        Start-Sleep -Seconds 20
    }
    throw 'Native volume monitor lifetime exhausted; no restart'
} catch {
    try { Write-NewJson (Join-Path $Control 'NATIVE-VOLUME-STOP.json') @{
        reason='Native external volume check stopped; inspect technical stderr'
        type=$_.Exception.GetType().FullName; automatic_restart=$false
    } } catch { }
    throw
}
