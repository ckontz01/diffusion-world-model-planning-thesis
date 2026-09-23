$ErrorActionPreference = 'Stop'
$acvWatch = [Diagnostics.Stopwatch]::StartNew()
$acvRoot = $PSScriptRoot
$acvRepo = Split-Path (Split-Path (Split-Path $acvRoot -Parent) -Parent) -Parent
$acvDestination = 'D:/THESIS-BACKUPS/active-counterfactual-verification-20260923/bindings-r1'
$acvVolume = Get-Volume -DriveLetter D
if ($acvVolume.FileSystemLabel -ne 'THESIS_SSD' -or $acvVolume.UniqueId -ne '\\?\Volume{0a2f1ba9-0000-0000-0000-100000000000}\') { throw 'Wrong designated SSD' }
if ($acvVolume.SizeRemaining -lt 40000000000) { throw 'Insufficient SSD free bytes' }
if (Test-Path -LiteralPath $acvDestination) { throw 'Existing exclusive backup; no overwrite/retry' }
if (Test-Path -LiteralPath (Join-Path $acvRoot 'DELIVERY.json')) { throw 'Existing receipt' }
$acvHead = (git -C $acvRepo rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Cannot read commit' }
$acvBranch = (git -C $acvRepo branch --show-current).Trim()
if ($acvBranch -ne 'active-counterfactual-verification-preparation-20260923') { throw 'Wrong branch' }
$acvRemote = git -C $acvRepo ls-remote origin ('refs/heads/'+$acvBranch)
if ($LASTEXITCODE -ne 0 -or -not $acvRemote -or $acvRemote.Split()[0] -ne $acvHead) { throw 'Remote hash mismatch' }
$acvStatus = git -C $acvRepo status --porcelain
if ($LASTEXITCODE -ne 0 -or $acvStatus) { throw 'Commit package before backup' }
$acvFiles = @(Get-ChildItem -LiteralPath $acvRoot -Recurse -File)
$acvTotal = ($acvFiles | Measure-Object Length -Sum).Sum
if ($acvTotal -gt 100000000 -or $acvFiles.Count -gt 200) { throw 'Small package bound exceeded' }
$acvSource = [IO.Path]::GetFullPath($acvRoot)
$acvTarget = [IO.Path]::GetFullPath($acvDestination)
if ($acvTarget -ne 'D:\THESIS-BACKUPS\active-counterfactual-verification-20260923\bindings-r1') { throw 'Unexpected destination' }
foreach ($acvFile in $acvFiles) {
    if ($acvFile.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'No reparse payloads' }
}
New-Item -ItemType Directory -Path $acvDestination | Out-Null
$acvEntries = @()
foreach ($acvFile in $acvFiles) {
    $acvRelative = $acvFile.FullName.Substring($acvSource.Length).TrimStart('\','/')
    $acvOut = Join-Path $acvDestination $acvRelative
    $acvParent = Split-Path $acvOut -Parent
    if (-not (Test-Path -LiteralPath $acvParent)) { New-Item -ItemType Directory -Path $acvParent | Out-Null }
    if (Test-Path -LiteralPath $acvOut) { throw 'Existing member' }
    $acvHash = (Get-FileHash -LiteralPath $acvFile.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    Copy-Item -LiteralPath $acvFile.FullName -Destination $acvOut
    if ((Get-FileHash -LiteralPath $acvOut -Algorithm SHA256).Hash.ToLowerInvariant() -ne $acvHash -or (Get-Item -LiteralPath $acvOut).Length -ne $acvFile.Length) { throw ('Readback mismatch '+$acvRelative) }
    $acvEntries += [pscustomobject]@{path=$acvRelative;bytes=$acvFile.Length;sha256=$acvHash;readback_match=$true}
}
$acvReceipt = [ordered]@{status='VERIFIED';package_commit=$acvHead;remote_head_verified=$true;branch=$acvBranch;
    reviewed_base='1c66038901fe39640add38aa796a816c06ccd1ae';source=$acvSource;destination=$acvTarget;
    ssd_volume=$acvVolume.UniqueId;free_bytes_before=$acvVolume.SizeRemaining;
    payload_files=$acvEntries.Count;payload_bytes=$acvTotal;members=$acvEntries;
    generated_utc=[DateTime]::UtcNow.ToString('o');wall_seconds_through_payload_readback=$acvWatch.Elapsed.TotalSeconds;
    research_execution_authorized=$false;historical_archives_transferred=0;accepted_preparation_rebacked=$false;
    note='Only the new bindings-r1 recovery source package. Every member and receipt read back. Existing bindings-v1/v2 and all historical archives untouched. This backup receipt is not execution authority.'}
$acvReceiptPath = Join-Path $acvRoot 'DELIVERY.json'
[IO.File]::WriteAllText($acvReceiptPath,($acvReceipt | ConvertTo-Json -Depth 8)+"`n",[Text.UTF8Encoding]::new($false))
$acvReceiptOut = Join-Path $acvDestination 'DELIVERY.json'
Copy-Item -LiteralPath $acvReceiptPath -Destination $acvReceiptOut
$acvReceiptHash = (Get-FileHash -LiteralPath $acvReceiptPath -Algorithm SHA256).Hash
if ((Get-FileHash -LiteralPath $acvReceiptOut -Algorithm SHA256).Hash -ne $acvReceiptHash) { throw 'Receipt readback mismatch' }
[pscustomobject]@{status='VERIFIED';payload_files=$acvEntries.Count;payload_bytes=$acvTotal;
    receipt_sha256=$acvReceiptHash;wall_seconds=$acvWatch.Elapsed.TotalSeconds;destination=$acvDestination} | ConvertTo-Json
