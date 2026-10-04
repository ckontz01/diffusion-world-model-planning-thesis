# New scoped provenance review: file names/sizes only; no HDF5 headers/payloads,
# scientific outputs, weights, simulator or jobs. No environment changes.
$ErrorActionPreference = 'Stop'
$wmSidecarQuery = @'
find /lustreFS/data/superworld/ckontzias/thesis/data/stablewm /lustreFS/data/superworld/ckontzias/thesis/manifests -maxdepth 2 -type f \( -iname '*provenance*' -o -iname '*origin*' -o -iname '*seed*' -o -iname '*generation*' -o -iname '*download*' -o -iname '*dinowm*' -o -iname '*readme*' -o -iname '*replay*' \) -printf '%p\t%s bytes\n'
'@
$wmSidecarRows = @(wsl.exe -d Thesis-Ubuntu -u chris -- ssh -o BatchMode=yes -o ConnectTimeout=20 prometheus $wmSidecarQuery)
if ($LASTEXITCODE -ne 0) { throw 'Configured provenance metadata transport failed; this is not evidence of missing cluster artifacts' }
if ($wmSidecarRows.Count -gt 200) { throw 'Scoped metadata output exceeds 200 entries; do not broaden or silently truncate' }
[ordered]@{domain='metadata-only';scope='two declared roots, maxdepth 2, matched sidecar/release names only';payload_or_header_reads=0;model_downloads=0;research_execution=$false;rows=$wmSidecarRows;absence_scope='No match here is not evidence of global absence or non-retention'} | ConvertTo-Json -Depth 4
