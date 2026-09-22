$ErrorActionPreference = 'Stop'
$acvInput = 'C:/Users/Chris/Downloads/Active_counterfactual_verification_candidate_20260923.zip'
$acvExpected = '9d843e842aae5318e55d65520a21b782cbb0f1c34c50875375fad6aa46cd95b2'
if ((Get-FileHash -LiteralPath $acvInput -Algorithm SHA256).Hash.ToLowerInvariant() -ne $acvExpected) { throw 'ZIP hash mismatch' }
$acvTarget = Join-Path $PSScriptRoot 'prototype'
if (Test-Path -LiteralPath $acvTarget) { throw 'Import already exists' }
Add-Type -AssemblyName System.IO.Compression.FileSystem
$acvZip = [IO.Compression.ZipFile]::OpenRead($acvInput)
try {
    $acvReader = [IO.StreamReader]::new($acvZip.GetEntry('active_counterfactual_verification/MANIFEST.json').Open())
    try { $acvManifest = $acvReader.ReadToEnd() | ConvertFrom-Json } finally { $acvReader.Dispose() }
    if ($acvZip.Entries.Count -ne 17 -or $acvManifest.files.PSObject.Properties.Count -eq 0) { throw 'Unexpected inventory' }
    foreach ($acvItem in $acvManifest.files.PSObject.Properties) {
        if ($acvItem.Name -match '(^/|\.\.|\\|:)') { throw 'Unsafe archive member' }
        $acvEntry = $acvZip.GetEntry('active_counterfactual_verification/'+$acvItem.Name)
        if (-not $acvEntry -or $acvEntry.Length -ne $acvItem.Value.bytes) { throw 'Member bytes mismatch' }
        $acvStream = $acvEntry.Open()
        $acvHasher = [Security.Cryptography.SHA256]::Create()
        try { $acvHash = [Convert]::ToHexString($acvHasher.ComputeHash($acvStream)).ToLowerInvariant() } finally { $acvStream.Dispose(); $acvHasher.Dispose() }
        if ($acvHash -ne $acvItem.Value.sha256) { throw ('Member hash mismatch '+$acvItem.Name) }
    }
    New-Item -ItemType Directory -Path $acvTarget | Out-Null
    foreach ($acvEntry in $acvZip.Entries) {
        $acvName = $acvEntry.FullName.Substring('active_counterfactual_verification/'.Length)
        if ($acvName -match '(^/|\.\.|\\|:)') { throw 'Unsafe path' }
        $acvOut = Join-Path $acvTarget $acvName
        $acvParent = Split-Path $acvOut -Parent
        if (-not (Test-Path -LiteralPath $acvParent)) { New-Item -ItemType Directory -Path $acvParent | Out-Null }
        [IO.Compression.ZipFileExtensions]::ExtractToFile($acvEntry,$acvOut,$false)
    }
} finally { $acvZip.Dispose() }
Copy-Item -LiteralPath $acvInput -Destination (Join-Path $PSScriptRoot 'ORIGINAL-PROTOTYPE.zip')
Copy-Item -LiteralPath 'C:/Users/Chris/.codex/attachments/cbe44b0c-2f20-42d1-9c23-b02b46a6853f/Pasted text.txt' -Destination (Join-Path $PSScriptRoot 'ACV0-INSTRUCTION.txt')
Write-Output 'Verified original ZIP and all 16 manifest members; imported unchanged.'
