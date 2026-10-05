[CmdletBinding()]
param([switch]$Acquire)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$c0ToolsRoot='C:\Users\Chris\thesis-vm\wm-diag0-a2-c0-runtime-v1\os-tools-v1'
$c0ToolsContract=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'CONTRACT.json') -Raw | ConvertFrom-Json
if (-not $Acquire) { [pscustomobject]@{Mode='PLAN_ONLY';Bytes=2249114;InstallsPackages=$false;Root=$c0ToolsRoot;Research=$false} | ConvertTo-Json; return }
if (Test-Path -LiteralPath $c0ToolsRoot) { throw 'Tool package root already exists. Preserve/reconcile; do not rerun.' }
$c0ToolsAncestor=[IO.DirectoryInfo]::new('C:\Users\Chris\thesis-vm')
while ($null -ne $c0ToolsAncestor) { if (((Get-Item -LiteralPath $c0ToolsAncestor.FullName).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Redirected preparation ancestor.' }; $c0ToolsAncestor=$c0ToolsAncestor.Parent }
New-Item -ItemType Directory -Path $c0ToolsRoot | Out-Null
Add-Type -AssemblyName System.Net.Http
$c0ToolsClient=[Net.Http.HttpClient]::new()
$c0ToolsClient.Timeout=[TimeSpan]::FromSeconds(20)
$c0ToolsTimer=[Diagnostics.Stopwatch]::StartNew()
try {
    foreach ($c0ToolsPkg in $c0ToolsContract.expected_packages) {
        $c0ToolsURI=[uri]('https://archive.ubuntu.com/ubuntu/'+$c0ToolsPkg.filename)
        $c0ToolsLeaf=[IO.Path]::GetFileName($c0ToolsURI.AbsolutePath)
        $c0ToolsPartial=Join-Path $c0ToolsRoot ($c0ToolsLeaf+'.partial')
        $c0ToolsResponse=$c0ToolsClient.GetAsync($c0ToolsURI,[Net.Http.HttpCompletionOption]::ResponseHeadersRead).GetAwaiter().GetResult()
        try {
            $c0ToolsResponse.EnsureSuccessStatusCode() | Out-Null
            if ($c0ToolsResponse.RequestMessage.RequestUri.AbsoluteUri -ne $c0ToolsURI.AbsoluteUri -or $c0ToolsResponse.Content.Headers.ContentLength -ne $c0ToolsPkg.bytes) { throw 'Unexpected URL or package length.' }
            $c0ToolsInput=$c0ToolsResponse.Content.ReadAsStreamAsync().GetAwaiter().GetResult()
            $c0ToolsOutput=[IO.File]::Open($c0ToolsPartial,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
            try {
                $c0ToolsBuffer=New-Object byte[] 65536
                $c0ToolsCount=[int64]0
                while (($c0ToolsRead=$c0ToolsInput.Read($c0ToolsBuffer,0,$c0ToolsBuffer.Length)) -gt 0) {
                    $c0ToolsCount += $c0ToolsRead
                    if ($c0ToolsCount -gt $c0ToolsPkg.bytes -or $c0ToolsTimer.Elapsed.TotalSeconds -gt 60) { throw 'Download byte/time envelope exceeded.' }
                    $c0ToolsOutput.Write($c0ToolsBuffer,0,$c0ToolsRead)
                }
                if ($c0ToolsCount -ne $c0ToolsPkg.bytes) { throw 'Incomplete package; preserve partial.' }
            } finally { $c0ToolsOutput.Dispose(); $c0ToolsInput.Dispose() }
        } finally { $c0ToolsResponse.Dispose() }
        if ((Get-FileHash -LiteralPath $c0ToolsPartial -Algorithm SHA256).Hash.ToLowerInvariant() -ne $c0ToolsPkg.SHA256) { throw 'Package hash mismatch; preserve partial.' }
        Move-Item -LiteralPath $c0ToolsPartial -Destination (Join-Path $c0ToolsRoot $c0ToolsLeaf)
    }
    [pscustomobject]@{Mode='AUTHENTICATED_OS_TOOL_PACKAGES_ACQUIRED'; PackageBytes=2249114; ElapsedSeconds=$c0ToolsTimer.Elapsed.TotalSeconds; InstallsPackages=$false; Research=$false; Root=$c0ToolsRoot} | ConvertTo-Json
} finally { $c0ToolsClient.Dispose() }
