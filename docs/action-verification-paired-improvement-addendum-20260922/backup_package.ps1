$ErrorActionPreference = 'Stop'
$addWatch = [Diagnostics.Stopwatch]::StartNew()
$addRoot = $PSScriptRoot
$addRepo = Split-Path (Split-Path $addRoot -Parent) -Parent
$addDestination = 'D:/THESIS-BACKUPS/action-verification-paired-improvement-addendum-20260922/preparation-v1'
$addVolume = Get-Volume -DriveLetter D
if ($addVolume.FileSystemLabel -ne 'THESIS_SSD' -or $addVolume.UniqueId -ne '\\?\Volume{0a2f1ba9-0000-0000-0000-100000000000}\') { throw 'Wrong SSD volume' }
if ($addVolume.SizeRemaining -lt 40000000000) { throw 'Insufficient SSD free bytes' }
if (Test-Path -LiteralPath $addDestination) { throw 'Exclusive backup destination already exists; no overwrite or retry' }
if (Test-Path -LiteralPath (Join-Path $addRoot 'DELIVERY.json')) { throw 'Receipt already exists' }
$addHead = (git -C $addRepo rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Cannot read package commit' }
$addBranch = (git -C $addRepo branch --show-current).Trim()
if ($addBranch -ne 'action-verification-paired-improvement-addendum-20260922') { throw 'Wrong branch' }
$addRemote = (git -C $addRepo ls-remote origin ('refs/heads/'+$addBranch))
if ($LASTEXITCODE -ne 0 -or -not $addRemote -or $addRemote.Split()[0] -ne $addHead) { throw 'Remote head mismatch' }
$addStatus = git -C $addRepo status --porcelain
if ($LASTEXITCODE -ne 0 -or $addStatus) { throw 'Commit package before backup' }
$addFiles = @(Get-ChildItem -LiteralPath $addRoot -Recurse -File)
$addTotal = ($addFiles | Measure-Object Length -Sum).Sum
if ($addTotal -gt 25000000 -or $addFiles.Count -gt 64) { throw 'Not a small addendum package' }
$addResolvedSource = [IO.Path]::GetFullPath($addRoot)
$addResolvedTarget = [IO.Path]::GetFullPath($addDestination)
if (-not $addResolvedTarget.StartsWith('D:\THESIS-BACKUPS\action-verification-paired-improvement-addendum-20260922\')) { throw 'Unexpected destination' }
foreach ($addFile in $addFiles) {
    if ($addFile.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Reparse-point payload is not allowed' }
}
New-Item -ItemType Directory -Path $addDestination | Out-Null
$addEntries = @()
foreach ($addFile in $addFiles) {
    $addRelative = $addFile.FullName.Substring($addResolvedSource.Length).TrimStart('\','/')
    $addOut = Join-Path $addDestination $addRelative
    $addOutParent = Split-Path $addOut -Parent
    if (-not (Test-Path -LiteralPath $addOutParent)) { New-Item -ItemType Directory -Path $addOutParent | Out-Null }
    if (Test-Path -LiteralPath $addOut) { throw 'Unexpected existing destination member' }
    $addHash = (Get-FileHash -LiteralPath $addFile.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    Copy-Item -LiteralPath $addFile.FullName -Destination $addOut
    $addReadback = (Get-FileHash -LiteralPath $addOut -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($addReadback -ne $addHash -or (Get-Item -LiteralPath $addOut).Length -ne $addFile.Length) { throw ('Backup verification failed: '+$addRelative) }
    $addEntries += [pscustomobject]@{path=$addRelative;bytes=$addFile.Length;sha256=$addHash;readback_match=$true}
}
$addReceipt = [ordered]@{status='VERIFIED';package_commit=$addHead;remote_head_verified=$true;
    accepted_av0_commit='ca0a05d5ec1c9ab66d723529ac227c98de5b73e1';
    branch=$addBranch;source=$addResolvedSource;destination=$addResolvedTarget;
    ssd_volume=$addVolume.UniqueId;free_bytes_before=$addVolume.SizeRemaining;
    payload_files=$addEntries.Count;payload_bytes=$addTotal;members=$addEntries;
    generated_utc=[DateTime]::UtcNow.ToString('o');
    preservation_seconds_through_payload_verification=$addWatch.Elapsed.TotalSeconds;
    note='Only the new addendum package. Receipt is copied and byte-hash read back separately. No original AV0 files or historical archives copied, opened for backup, changed or overwritten.'}
$addReceiptPath = Join-Path $addRoot 'DELIVERY.json'
[IO.File]::WriteAllText($addReceiptPath,($addReceipt | ConvertTo-Json -Depth 8)+"`n",[Text.UTF8Encoding]::new($false))
$addReceiptOut = Join-Path $addDestination 'DELIVERY.json'
Copy-Item -LiteralPath $addReceiptPath -Destination $addReceiptOut
$addReceiptHash = (Get-FileHash -LiteralPath $addReceiptPath -Algorithm SHA256).Hash
if ((Get-FileHash -LiteralPath $addReceiptOut -Algorithm SHA256).Hash -ne $addReceiptHash) { throw 'Receipt readback mismatch' }
[pscustomobject]@{status='VERIFIED';payload_files=$addEntries.Count;payload_bytes=$addTotal;
    receipt_bytes=(Get-Item -LiteralPath $addReceiptPath).Length;receipt_sha256=$addReceiptHash;
    preservation_wall_seconds=$addWatch.Elapsed.TotalSeconds;destination=$addDestination} | ConvertTo-Json
