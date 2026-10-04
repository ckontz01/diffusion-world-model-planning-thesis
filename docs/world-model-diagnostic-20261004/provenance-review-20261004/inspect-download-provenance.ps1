# Read two identified small data-acquisition source files only; never execute them.
# Public dataset URLs are extracted without query strings; no credentials printed.
$ErrorActionPreference = 'Stop'
$wmDownloadQuery = @'
sha256sum /lustreFS/data/superworld/ckontzias/thesis/manifests/download_benchmark_data.slurm /lustreFS/data/superworld/ckontzias/thesis/manifests/stage_downloads_login.sh
grep -oE 'https://huggingface.co/datasets/[A-Za-z0-9_./-]+' /lustreFS/data/superworld/ckontzias/thesis/manifests/download_benchmark_data.slurm /lustreFS/data/superworld/ckontzias/thesis/manifests/stage_downloads_login.sh
grep -nE '^#.*(PushT|Reacher|seed|origin|collect|generat)|^[[:space:]]*(pusht_expert_train|reacher)[.]' /lustreFS/data/superworld/ckontzias/thesis/manifests/download_benchmark_data.slurm /lustreFS/data/superworld/ckontzias/thesis/manifests/stage_downloads_login.sh || true
'@
$wmDownloadRows = @(wsl.exe -d Thesis-Ubuntu -u chris -- ssh -o BatchMode=yes -o ConnectTimeout=20 prometheus $wmDownloadQuery)
if ($LASTEXITCODE -ne 0) { throw 'Configured source metadata transport failed; do not infer missing records' }
if ($wmDownloadRows.Count -gt 100) { throw 'Source metadata output cap exceeded' }
[ordered]@{domain='source-metadata-only';payload_or_header_reads=0;source_files_executed=0;research_execution=$false;rows=$wmDownloadRows;note='Downloaded data source is not itself episode-origin authentication'} | ConvertTo-Json -Depth 4
