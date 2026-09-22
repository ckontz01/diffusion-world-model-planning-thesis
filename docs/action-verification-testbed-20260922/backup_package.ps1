$ErrorActionPreference = 'Stop'
$avRoot = $PSScriptRoot
$avRepo = Split-Path (Split-Path $avRoot -Parent) -Parent
$avDestination = 'D:/THESIS-BACKUPS/action-verification-testbed-20260922/preparation-v1'
$avVolume = Get-Volume -DriveLetter D
if ($avVolume.FileSystemLabel -ne 'THESIS_SSD' -or $avVolume.UniqueId -ne '\\?\Volume{0a2f1ba9-0000-0000-0000-100000000000}\') { throw 'Wrong SSD volume' }
if ($avVolume.SizeRemaining -lt 40000000000) { throw 'Insufficient SSD free bytes' }
if (Test-Path -LiteralPath $avDestination) { throw 'Exclusive backup destination already exists; no overwrite or retry' }
if (Test-Path -LiteralPath (Join-Path $avRoot 'DELIVERY.json')) { throw 'Receipt already exists' }
$avHead = (git -C $avRepo rev-parse HEAD).Trim()
$avBranch = (git -C $avRepo branch --show-current).Trim()
if ($avBranch -ne 'action-verification-testbed-preparation-20260922') { throw 'Wrong branch' }
$avRemote = (git -C $avRepo ls-remote origin ('refs/heads/'+$avBranch))
if ($LASTEXITCODE -ne 0 -or $avRemote.Split()[0] -ne $avHead) { throw 'Remote head mismatch' }
if (git -C $avRepo status --porcelain) { throw 'Commit package before backup' }
$avFiles = @(Get-ChildItem -LiteralPath $avRoot -Recurse -File)
$avTotal = ($avFiles | Measure-Object Length -Sum).Sum
if ($avTotal -gt 25000000 -or $avFiles.Count -gt 64) { throw 'Not a small AV0 package' }
$avResolvedSource = [IO.Path]::GetFullPath($avRoot)
$avResolvedTarget = [IO.Path]::GetFullPath($avDestination)
if (-not $avResolvedTarget.StartsWith('D:\THESIS-BACKUPS\action-verification-testbed-20260922\')) { throw 'Unexpected destination' }
New-Item -ItemType Directory -Path $avDestination | Out-Null
$avEntries = @()
foreach ($avFile in $avFiles) {
    $avRelative = $avFile.FullName.Substring($avResolvedSource.Length).TrimStart('\','/')
    $avOut = Join-Path $avDestination $avRelative
    $avOutParent = Split-Path $avOut -Parent
    if (-not (Test-Path -LiteralPath $avOutParent)) { New-Item -ItemType Directory -Path $avOutParent | Out-Null }
    $avHash = (Get-FileHash -LiteralPath $avFile.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    Copy-Item -LiteralPath $avFile.FullName -Destination $avOut
    $avReadback = (Get-FileHash -LiteralPath $avOut -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($avReadback -ne $avHash -or (Get-Item -LiteralPath $avOut).Length -ne $avFile.Length) { throw ('Backup verification failed: '+$avRelative) }
    $avEntries += [pscustomobject]@{path=$avRelative;bytes=$avFile.Length;sha256=$avHash;readback_match=$true}
}
$avReceipt = [ordered]@{status='VERIFIED';package_commit=$avHead;remote_head_verified=$true;
    branch=$avBranch;source=$avResolvedSource;destination=$avResolvedTarget;
    ssd_volume=$avVolume.UniqueId;free_bytes_before=$avVolume.SizeRemaining;
    payload_files=$avEntries.Count;payload_bytes=$avTotal;members=$avEntries;
    generated_utc=[DateTime]::UtcNow.ToString('o');
    note='Receipt itself is copied and byte-hash read back separately; no historical archive opened or overwritten.'}
$avReceiptPath = Join-Path $avRoot 'DELIVERY.json'
[IO.File]::WriteAllText($avReceiptPath,($avReceipt | ConvertTo-Json -Depth 8)+"`n",[Text.UTF8Encoding]::new($false))
$avReceiptOut = Join-Path $avDestination 'DELIVERY.json'
Copy-Item -LiteralPath $avReceiptPath -Destination $avReceiptOut
$avReceiptHash = (Get-FileHash -LiteralPath $avReceiptPath -Algorithm SHA256).Hash
if ((Get-FileHash -LiteralPath $avReceiptOut -Algorithm SHA256).Hash -ne $avReceiptHash) { throw 'Receipt readback mismatch' }
[pscustomobject]@{status='VERIFIED';payload_files=$avEntries.Count;payload_bytes=$avTotal;
    receipt_bytes=(Get-Item $avReceiptPath).Length;receipt_sha256=$avReceiptHash;destination=$avDestination} | ConvertTo-Json
