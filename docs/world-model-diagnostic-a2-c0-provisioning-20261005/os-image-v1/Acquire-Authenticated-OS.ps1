[CmdletBinding()]
param([switch]$Acquire)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$c0OSRoot='C:\Users\Chris\thesis-vm\wm-diag0-a2-c0-runtime-v1\os-image-v1'
$c0OSURL='https://cloud-images.ubuntu.com/minimal/releases/jammy/release-20261001/ubuntu-22.04-minimal-cloudimg-amd64.img'
$c0OSSize=[int64]310607360
$c0OSHash='BD27C6F51053DD7E59BCBE6016C6FA853F54B1E423AF12273FF46A5176BFBF41'
if (-not $Acquire) { [pscustomobject]@{Mode='PLAN_ONLY';OSBytes=$c0OSSize;GuestBoot=$false;Research=$false} | ConvertTo-Json; return }
if (Test-Path -LiteralPath $c0OSRoot) { throw 'OS acquisition already exists; preserve/reconcile and do not retry.' }
if ((Get-PSDrive C).Free -lt 3000000000) { throw 'Not enough headroom for reserved offline preparation.' }
foreach ($c0OSReceipt in @(@('FIRMWARE-CAPACITY-V1-VERIFIED.json','FF886BBA40DD5813A53128D550FD2C1DE48CB20C1313BF444AE2C30A67D834D6'),@('FIRMWARE-CAPACITY-V1-WATCHDOG.json','98AA4D581FB1B7AB596D1532FB169FCCFD359C275AC9DFEB5F1F4771A5FB7A54'))) {
    if ((Get-FileHash -LiteralPath (Join-Path 'C:\Users\Chris\thesis-vm\wm-diag0-a2-c0-prep-v1' $c0OSReceipt[0])).Hash -ne $c0OSReceipt[1]) { throw 'Expected Off receipt identity mismatch.' }
}
if ((Get-FileHash -LiteralPath 'C:\Users\Chris\thesis-vm\wm-diag0-a2-c0-runtime-v1\os-metadata-v1\SHA256SUMS').Hash -ne '89533E7C045FAE48A9C78AE16CBCE304960AB1C89D5AFAD536A10F7401315C8F') { throw 'Authenticated checksum metadata changed.' }
$c0OSAncestor=[IO.DirectoryInfo]::new('C:\Users\Chris\thesis-vm\wm-diag0-a2-c0-runtime-v1')
while ($null -ne $c0OSAncestor) { if (((Get-Item -LiteralPath $c0OSAncestor.FullName).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Redirected OS acquisition ancestor.' }; $c0OSAncestor=$c0OSAncestor.Parent }
New-Item -ItemType Directory -Path $c0OSRoot | Out-Null
$c0OSPartial=Join-Path $c0OSRoot 'ubuntu-22.04-minimal-cloudimg-amd64.img.partial'
Add-Type -AssemblyName System.Net.Http
$c0OSClient=[Net.Http.HttpClient]::new()
$c0OSClient.Timeout=[TimeSpan]::FromSeconds(20)
$c0OSTimer=[Diagnostics.Stopwatch]::StartNew()
try {
    $c0OSResponse=$c0OSClient.GetAsync([uri]$c0OSURL,[Net.Http.HttpCompletionOption]::ResponseHeadersRead).GetAwaiter().GetResult()
    try {
        $c0OSResponse.EnsureSuccessStatusCode() | Out-Null
        if ($c0OSResponse.RequestMessage.RequestUri.AbsoluteUri -ne $c0OSURL -or $c0OSResponse.Content.Headers.ContentLength -ne $c0OSSize) { throw 'OS URL or declared byte size mismatch.' }
        $c0OSInput=$c0OSResponse.Content.ReadAsStreamAsync().GetAwaiter().GetResult()
        $c0OSOutput=[IO.File]::Open($c0OSPartial,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
        try {
            $c0OSBuffer=New-Object byte[] 1048576
            $c0OSCount=[int64]0
            while ($true) {
                $c0OSReadTask=$c0OSInput.ReadAsync($c0OSBuffer,0,$c0OSBuffer.Length)
                while (-not $c0OSReadTask.Wait(1000)) { if ($c0OSTimer.Elapsed.TotalSeconds -gt 180) { throw 'OS download timed out; preserve partial, no retry.' } }
                if ($c0OSTimer.Elapsed.TotalSeconds -gt 180) { throw 'OS download exceeded time cap.' }
                $c0OSRead=$c0OSReadTask.GetAwaiter().GetResult()
                if ($c0OSRead -eq 0) { break }
                $c0OSCount += $c0OSRead
                if ($c0OSCount -gt $c0OSSize) { throw 'OS source exceeds byte cap.' }
                $c0OSOutput.Write($c0OSBuffer,0,$c0OSRead)
            }
            if ($c0OSCount -ne $c0OSSize) { throw 'OS source incomplete; preserve partial.' }
        } finally { $c0OSOutput.Dispose(); $c0OSInput.Dispose() }
    } finally { $c0OSResponse.Dispose() }
    if ((Get-FileHash -LiteralPath $c0OSPartial).Hash -ne $c0OSHash) { throw 'Full OS hash mismatch; preserve partial.' }
    Move-Item -LiteralPath $c0OSPartial -Destination (Join-Path $c0OSRoot 'ubuntu-22.04-minimal-cloudimg-amd64.img')
    [pscustomobject]@{Mode='AUTHENTICATED_OFFICIAL_OS_IMAGE_ACQUIRED';Bytes=$c0OSCount;SHA256=$c0OSHash;ElapsedSeconds=$c0OSTimer.Elapsed.TotalSeconds;GuestBoot=$false;ResearchCheckpointLoaded=$false} | ConvertTo-Json
} finally { $c0OSClient.Dispose() }
