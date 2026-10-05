[CmdletBinding()]
param([switch]$Acquire)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$c0MetaRoot='C:\Users\Chris\thesis-vm\wm-diag0-a2-c0-runtime-v1\os-metadata-v1'
$c0MetaItems=@(
    @('SHA256SUMS','https://cloud-images.ubuntu.com/minimal/releases/jammy/release-20261001/SHA256SUMS'),
    @('SHA256SUMS.gpg','https://cloud-images.ubuntu.com/minimal/releases/jammy/release-20261001/SHA256SUMS.gpg'),
    @('ubuntu-cloud-public.asc','https://keyserver.ubuntu.com/pks/lookup?op=get&search=0xD2EB44626FDDC30B513D5BB71A5D6C4C7DB87C81')
)
if (-not $Acquire) { [pscustomobject]@{Mode='PLAN_ONLY';MaximumBytes=196608;PublicMetadataOnly=$true;Research=$false} | ConvertTo-Json; return }
if (Test-Path -LiteralPath $c0MetaRoot) { throw 'Metadata acquisition exists. Preserve/reconcile, do not rerun.' }
$c0MetaAncestor=[IO.DirectoryInfo]::new('C:\Users\Chris\thesis-vm')
while ($null -ne $c0MetaAncestor) { if (((Get-Item -LiteralPath $c0MetaAncestor.FullName).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Redirected metadata ancestor.' }; $c0MetaAncestor=$c0MetaAncestor.Parent }
New-Item -ItemType Directory -Path $c0MetaRoot | Out-Null
New-Item -ItemType Directory -Path (Join-Path $c0MetaRoot 'public-key-home') | Out-Null
Add-Type -AssemblyName System.Net.Http
$c0MetaClient=[Net.Http.HttpClient]::new()
$c0MetaClient.Timeout=[TimeSpan]::FromSeconds(20)
$c0MetaTimer=[Diagnostics.Stopwatch]::StartNew()
$c0MetaReceipts=@()
try {
    foreach ($c0MetaItem in $c0MetaItems) {
        $c0MetaURI=[uri]$c0MetaItem[1]
        $c0MetaPartial=Join-Path $c0MetaRoot ($c0MetaItem[0]+'.partial')
        $c0MetaResponse=$c0MetaClient.GetAsync($c0MetaURI,[Net.Http.HttpCompletionOption]::ResponseHeadersRead).GetAwaiter().GetResult()
        try {
            $c0MetaResponse.EnsureSuccessStatusCode() | Out-Null
            if ($c0MetaResponse.RequestMessage.RequestUri.AbsoluteUri -ne $c0MetaURI.AbsoluteUri) { throw 'Unexpected metadata redirect.' }
            $c0MetaInput=$c0MetaResponse.Content.ReadAsStreamAsync().GetAwaiter().GetResult()
            $c0MetaOutput=[IO.File]::Open($c0MetaPartial,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
            try {
                $c0MetaBuffer=New-Object byte[] 8192
                $c0MetaCount=0
                while (($c0MetaRead=$c0MetaInput.Read($c0MetaBuffer,0,$c0MetaBuffer.Length)) -gt 0) {
                    $c0MetaCount+=$c0MetaRead
                    if ($c0MetaCount -gt 65536 -or $c0MetaTimer.Elapsed.TotalSeconds -gt 60) { throw 'Metadata byte/time cap exceeded.' }
                    $c0MetaOutput.Write($c0MetaBuffer,0,$c0MetaRead)
                }
            } finally { $c0MetaOutput.Dispose(); $c0MetaInput.Dispose() }
        } finally { $c0MetaResponse.Dispose() }
        $c0MetaFinal=Join-Path $c0MetaRoot $c0MetaItem[0]
        Move-Item -LiteralPath $c0MetaPartial -Destination $c0MetaFinal
        $c0MetaReceipts+=[pscustomobject]@{Name=$c0MetaItem[0];Bytes=$c0MetaCount;SHA256=(Get-FileHash -LiteralPath $c0MetaFinal).Hash;URL=$c0MetaURI.AbsoluteUri}
    }
    [pscustomobject]@{Mode='PUBLIC_OS_METADATA_ACQUIRED_NOT_YET_SIGNATURE_VERIFIED';Members=$c0MetaReceipts;ElapsedSeconds=$c0MetaTimer.Elapsed.TotalSeconds;Research=$false} | ConvertTo-Json -Depth 5
} finally { $c0MetaClient.Dispose() }
