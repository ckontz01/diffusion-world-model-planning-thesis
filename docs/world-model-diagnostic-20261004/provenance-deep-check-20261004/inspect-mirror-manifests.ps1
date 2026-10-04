# Inspect only the two identified small third-party metadata manifests, not data.
$ErrorActionPreference = 'Stop'
$wmManifestRows = @()
foreach ($task in @('pusht','reacher')) {
    $url = "https://huggingface.co/datasets/PeterLiZijia/nfwm/resolve/fd4fa751d23acc9f69eef769d28b232b3adf50db/datasets/$task/eval_manifest.json"
    $response = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 25
    if ($response.RawContentLength -gt 10000) { throw 'Identified small manifest response exceeded 10000 byte cap' }
    $wmManifestRows += [ordered]@{task=$task;url=$url;manifest=(ConvertFrom-Json $response.Content);limit='Third-party metadata only; no automatic attribution to original historical roots'}
}
[ordered]@{domain='public-metadata-only';observed_utc=[DateTime]::UtcNow.ToString('o');records=$wmManifestRows;payload_or_header_reads=0;artifact_downloads=0;research_execution=$false} | ConvertTo-Json -Depth 15
