$ErrorActionPreference = 'Stop'
$acvWatch = [Diagnostics.Stopwatch]::StartNew()
$acvRoot = $PSScriptRoot
$acvRepo = Split-Path (Split-Path (Split-Path $acvRoot -Parent) -Parent) -Parent
$acvPublication = Join-Path $acvRepo 'docs/active-counterfactual-verification-publication-20260923/preservation-r6'
$acvDestination = 'D:/THESIS-BACKUPS/active-counterfactual-verification-20260923/preservation-r6'
$acvVolume = Get-Volume -DriveLetter D
if ($acvVolume.FileSystemLabel -ne 'THESIS_SSD' -or $acvVolume.UniqueId -ne '\\?\Volume{0a2f1ba9-0000-0000-0000-100000000000}\' -or $acvVolume.SizeRemaining -lt 40000000000) { throw 'Designated SSD identity/capacity' }
if (Test-Path -LiteralPath $acvDestination) { throw 'Existing exclusive backup; no overwrite/retry' }
if (Test-Path -LiteralPath (Join-Path $acvPublication 'DELIVERY.json')) { throw 'Existing receipt' }
$acvHead = (git -C $acvRepo rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Cannot read commit' }
$acvBranch = (git -C $acvRepo branch --show-current).Trim()
if ($acvBranch -ne 'active-counterfactual-verification-preparation-20260923') { throw 'Wrong branch' }
$acvRemote = git -C $acvRepo ls-remote origin ('refs/heads/'+$acvBranch)
if ($LASTEXITCODE -ne 0 -or -not $acvRemote -or $acvRemote.Split()[0] -ne $acvHead) { throw 'Remote hash mismatch' }
$acvStatus = git -C $acvRepo status --porcelain
if ($LASTEXITCODE -ne 0 -or $acvStatus) { throw 'Commit package before backup' }
$acvFiles = @()
foreach ($acvItem in @(@{label='source';root=$acvRoot},@{label='authority';root=$acvPublication})) {
    $acvPrefix = [IO.Path]::GetFullPath($acvItem.root)
    foreach ($acvFile in (Get-ChildItem -LiteralPath $acvItem.root -Recurse -File)) {
        if ($acvFile.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'No reparse payloads' }
        $acvFiles += [pscustomobject]@{file=$acvFile;relative=($acvItem.label+'/'+$acvFile.FullName.Substring($acvPrefix.Length).TrimStart('\','/'))}
    }
}
$acvTotal = ($acvFiles.file | Measure-Object Length -Sum).Sum
if ($acvTotal -gt 250000000 -or $acvFiles.Count -gt 250) { throw 'Small package bound exceeded' }
$acvTarget = [IO.Path]::GetFullPath($acvDestination)
if ($acvTarget -ne 'D:\THESIS-BACKUPS\active-counterfactual-verification-20260923\preservation-r6') { throw 'Unexpected destination' }
New-Item -ItemType Directory -Path $acvDestination | Out-Null
$acvEntries = @()
foreach ($acvItem in $acvFiles) {
    $acvFile = $acvItem.file
    $acvOut = Join-Path $acvDestination $acvItem.relative
    $acvParent = Split-Path $acvOut -Parent
    if (-not (Test-Path -LiteralPath $acvParent)) { New-Item -ItemType Directory -Path $acvParent | Out-Null }
    if (Test-Path -LiteralPath $acvOut) { throw 'Existing member' }
    $acvHash = (Get-FileHash -LiteralPath $acvFile.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    Copy-Item -LiteralPath $acvFile.FullName -Destination $acvOut
    if ((Get-FileHash -LiteralPath $acvOut -Algorithm SHA256).Hash.ToLowerInvariant() -ne $acvHash -or (Get-Item -LiteralPath $acvOut).Length -ne $acvFile.Length) { throw ('Readback mismatch '+$acvItem.relative) }
    $acvEntries += [pscustomobject]@{path=$acvItem.relative;bytes=$acvFile.Length;sha256=$acvHash;readback_match=$true}
}
$acvReceipt = [ordered]@{status='VERIFIED';package_commit=$acvHead;remote_head_verified=$true;branch=$acvBranch;
    destination=$acvTarget;ssd_volume=$acvVolume.UniqueId;free_bytes_before=$acvVolume.SizeRemaining;
    payload_files=$acvEntries.Count;payload_bytes=$acvTotal;members=$acvEntries;
    generated_utc=[DateTime]::UtcNow.ToString('o');wall_seconds_through_payload_readback=$acvWatch.Elapsed.TotalSeconds;
    historical_archives_transferred=0;original_scientific_package_rebacked=$false;
    note='Only new preservation-r6 source and authority/test/preparation records. Every payload and receipt read back. Not a substitute for final research archive preservation.'}
$acvReceiptPath = Join-Path $acvPublication 'DELIVERY.json'
[IO.File]::WriteAllText($acvReceiptPath,($acvReceipt | ConvertTo-Json -Depth 8)+"`n",[Text.UTF8Encoding]::new($false))
$acvReceiptOut = Join-Path $acvDestination 'DELIVERY.json'
Copy-Item -LiteralPath $acvReceiptPath -Destination $acvReceiptOut
$acvReceiptHash = (Get-FileHash -LiteralPath $acvReceiptPath -Algorithm SHA256).Hash
if ((Get-FileHash -LiteralPath $acvReceiptOut -Algorithm SHA256).Hash -ne $acvReceiptHash) { throw 'Receipt readback mismatch' }
[pscustomobject]@{status='VERIFIED';payload_files=$acvEntries.Count;payload_bytes=$acvTotal;receipt_sha256=$acvReceiptHash;
    wall_seconds=$acvWatch.Elapsed.TotalSeconds;destination=$acvDestination} | ConvertTo-Json
