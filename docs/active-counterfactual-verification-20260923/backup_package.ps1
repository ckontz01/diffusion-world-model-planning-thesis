$ErrorActionPreference = 'Stop'
$acvWatch = [Diagnostics.Stopwatch]::StartNew()
$acvRoot = $PSScriptRoot
$acvRepo = Split-Path (Split-Path $acvRoot -Parent) -Parent
$acvDestination = 'D:/THESIS-BACKUPS/active-counterfactual-verification-20260923/preparation-v1'
$acvVolume = Get-Volume -DriveLetter D
if ($acvVolume.FileSystemLabel -ne 'THESIS_SSD' -or $acvVolume.UniqueId -ne '\\?\Volume{0a2f1ba9-0000-0000-0000-100000000000}\') { throw 'Wrong designated SSD' }
if ($acvVolume.SizeRemaining -lt 40000000000) { throw 'Insufficient SSD free bytes' }
if (Test-Path -LiteralPath $acvDestination) { throw 'Exclusive backup already exists; do not overwrite/retry' }
if (Test-Path -LiteralPath (Join-Path $acvRoot 'DELIVERY.json')) { throw 'Receipt already exists' }
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
if ($acvTotal -gt 25000000 -or $acvFiles.Count -gt 200) { throw 'Not the expected small new package' }
$acvSource = [IO.Path]::GetFullPath($acvRoot)
$acvTarget = [IO.Path]::GetFullPath($acvDestination)
if (-not $acvTarget.StartsWith('D:\THESIS-BACKUPS\active-counterfactual-verification-20260923\')) { throw 'Unexpected destination' }
foreach ($acvFile in $acvFiles) {
    if ($acvFile.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Reparse payload forbidden' }
}
New-Item -ItemType Directory -Path $acvDestination | Out-Null
$acvEntries = @()
foreach ($acvFile in $acvFiles) {
    $acvRelative = $acvFile.FullName.Substring($acvSource.Length).TrimStart('\','/')
    $acvOut = Join-Path $acvDestination $acvRelative
    $acvParent = Split-Path $acvOut -Parent
    if (-not (Test-Path -LiteralPath $acvParent)) { New-Item -ItemType Directory -Path $acvParent | Out-Null }
    if (Test-Path -LiteralPath $acvOut) { throw 'Existing member; stop' }
    $acvHash = (Get-FileHash -LiteralPath $acvFile.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    Copy-Item -LiteralPath $acvFile.FullName -Destination $acvOut
    $acvReadback = (Get-FileHash -LiteralPath $acvOut -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($acvReadback -ne $acvHash -or (Get-Item -LiteralPath $acvOut).Length -ne $acvFile.Length) { throw ('Verification failed '+$acvRelative) }
    $acvEntries += [pscustomobject]@{path=$acvRelative;bytes=$acvFile.Length;sha256=$acvHash;readback_match=$true}
}
$acvReceipt = [ordered]@{status='VERIFIED';package_commit=$acvHead;remote_head_verified=$true;
    base_commit='02a6157ecb11ff2a9cf6ced6ce0523b181805db0';branch=$acvBranch;
    source=$acvSource;destination=$acvTarget;ssd_volume=$acvVolume.UniqueId;free_bytes_before=$acvVolume.SizeRemaining;
    payload_files=$acvEntries.Count;payload_bytes=$acvTotal;members=$acvEntries;
    generated_utc=[DateTime]::UtcNow.ToString('o');preservation_seconds_through_payload_verification=$acvWatch.Elapsed.TotalSeconds;
    research_execution_authorized=$false;historical_archives_transferred=0;
    note='Only new ACV0 preparation package including supplied candidate ZIP. Every payload member read back; receipt copied and hash-read-back separately. No old archives or prior-study outputs retransmitted.'}
$acvReceiptPath = Join-Path $acvRoot 'DELIVERY.json'
[IO.File]::WriteAllText($acvReceiptPath,($acvReceipt | ConvertTo-Json -Depth 8)+"`n",[Text.UTF8Encoding]::new($false))
$acvReceiptOut = Join-Path $acvDestination 'DELIVERY.json'
Copy-Item -LiteralPath $acvReceiptPath -Destination $acvReceiptOut
$acvReceiptHash = (Get-FileHash -LiteralPath $acvReceiptPath -Algorithm SHA256).Hash
if ((Get-FileHash -LiteralPath $acvReceiptOut -Algorithm SHA256).Hash -ne $acvReceiptHash) { throw 'Receipt mismatch' }
[pscustomobject]@{status='VERIFIED';payload_files=$acvEntries.Count;payload_bytes=$acvTotal;
    receipt_bytes=(Get-Item -LiteralPath $acvReceiptPath).Length;receipt_sha256=$acvReceiptHash;
    preservation_wall_seconds=$acvWatch.Elapsed.TotalSeconds;destination=$acvDestination} | ConvertTo-Json
