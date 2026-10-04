# Expand depth only inside the same two declared, relevant metadata/model roots.
$ErrorActionPreference = 'Stop'
$wmDeepSidecarQuery = @'
find /lustreFS/data/superworld/ckontzias/thesis/data/stablewm /lustreFS/data/superworld/ckontzias/thesis/manifests -maxdepth 5 -type f \( -iname '*provenance*' -o -iname '*origin*' -o -iname '*seed*' -o -iname '*generat*' -o -iname '*collect*' -o -iname '*download*' -o -iname '*dinowm*' -o -iname '*dino_wm*' -o -iname '*readme*' -o -iname '*replay*' \) -printf '%p\t%s bytes\n'
'@
$wmDeepSidecarRows = @(wsl.exe -d Thesis-Ubuntu -u chris -- ssh -o BatchMode=yes -o ConnectTimeout=20 prometheus $wmDeepSidecarQuery)
if ($LASTEXITCODE -ne 0) { throw 'Configured metadata transport failed; missing files cannot be inferred' }
if ($wmDeepSidecarRows.Count -gt 200) { throw 'Bounded metadata output exceeds 200 entries; no truncation or broader scan permitted' }
[ordered]@{domain='metadata-only';observed_utc=[DateTime]::UtcNow.ToString('o');scope='same two declared roots, maximum depth five, matched acquisition/generation/release names only';rows=$wmDeepSidecarRows;payload_or_header_reads=0;checkpoint_loading=0;research_execution=$false;absence_scope='No match in these roots is not global absence or custodian confirmation of non-retention'} | ConvertTo-Json -Depth 5
