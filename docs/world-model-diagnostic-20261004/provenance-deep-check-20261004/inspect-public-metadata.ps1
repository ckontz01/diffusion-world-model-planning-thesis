# New bounded metadata observation only; never download weights or dataset archives.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Net.Http
$wmDeepClient = New-Object System.Net.Http.HttpClient
$wmDeepClient.Timeout = [TimeSpan]::FromSeconds(25)
$wmDeepClient.DefaultRequestHeaders.UserAgent.ParseAdd('WM-DIAG0-provenance-metadata-review')
function Get-WmSmallText([string]$url) {
    $response = $wmDeepClient.GetAsync($url, [System.Net.Http.HttpCompletionOption]::ResponseHeadersRead).GetAwaiter().GetResult()
    try {
        if (-not $response.IsSuccessStatusCode) { throw "Metadata HTTP $([int]$response.StatusCode): $url" }
        if ($response.Content.Headers.ContentLength -gt 100000) { throw 'Metadata response exceeds 100000 byte cap' }
        $stream = $response.Content.ReadAsStreamAsync().GetAwaiter().GetResult()
        $buffer = New-Object byte[] 4096
        $memory = New-Object System.IO.MemoryStream
        try {
            while (($count = $stream.Read($buffer, 0, $buffer.Length)) -gt 0) {
                if (($memory.Length + $count) -gt 100000) { throw 'Metadata response exceeds 100000 byte cap' }
                $memory.Write($buffer, 0, $count)
            }
            return [Text.Encoding]::UTF8.GetString($memory.ToArray())
        } finally { $stream.Dispose(); $memory.Dispose() }
    } finally { $response.Dispose() }
}
$records = New-Object System.Collections.ArrayList
$requests = @(
    @{ kind='publisher-releases'; url='https://api.github.com/repos/lucas-maes/le-wm/releases?per_page=5' },
    @{ kind='reacher-collector-history'; url='https://api.github.com/repos/galilai-group/stable-worldmodel/commits?path=scripts/data/collect_reacher.py&per_page=5' },
    @{ kind='pusht-collector-history'; url='https://api.github.com/repos/galilai-group/stable-worldmodel/commits?path=scripts/data/collect_weak_pusht.py&per_page=5' },
    @{ kind='mirror-revision'; url='https://huggingface.co/api/datasets/PeterLiZijia/nfwm' },
    @{ kind='mirror-pusht-tree'; url='https://huggingface.co/api/datasets/PeterLiZijia/nfwm/tree/main/datasets/pusht' },
    @{ kind='mirror-reacher-tree'; url='https://huggingface.co/api/datasets/PeterLiZijia/nfwm/tree/main/datasets/reacher' }
)
$mirrorRevision = $null
foreach ($item in $requests) {
    try {
        $raw = Get-WmSmallText $item.url
        $parsed = ConvertFrom-Json $raw
        if ($item.kind -eq 'mirror-revision') {
            $mirrorRevision = $parsed.sha
            $value = [ordered]@{ id=$parsed.id; sha=$parsed.sha; lastModified=$parsed.lastModified }
        } elseif ($item.kind -like '*collector-history') {
            $value = @($parsed | ForEach-Object { [ordered]@{sha=$_.sha; date=$_.commit.committer.date; message=$_.commit.message; url=$_.html_url} })
            if ($value.Count -gt 0) {
                $oldest = $value[-1].sha
                $file = if ($item.kind -eq 'reacher-collector-history') {'collect_reacher.py'} else {'collect_weak_pusht.py'}
                $sourceUrl = "https://raw.githubusercontent.com/galilai-group/stable-worldmodel/$oldest/scripts/data/$file"
                $source = Get-WmSmallText $sourceUrl
                [void]$records.Add([ordered]@{kind='oldest-returned-source'; url=$sourceUrl; source=$source; limit='Oldest of at most five path commits; source is a lead, not proof of released dataset generation'})
            }
        } elseif ($item.kind -eq 'publisher-releases') {
            $value = @($parsed | ForEach-Object { [ordered]@{tag=$_.tag_name;url=$_.html_url;assets=@($_.assets | ForEach-Object {[ordered]@{name=$_.name;bytes=$_.size;digest=$_.digest;url=$_.browser_download_url}})} })
        } else { $value = @($parsed | ForEach-Object { [ordered]@{path=$_.path;type=$_.type;size=$_.size;oid=$_.oid} }) }
        [void]$records.Add([ordered]@{kind=$item.kind;url=$item.url;value=$value})
    } catch { [void]$records.Add([ordered]@{kind=$item.kind;url=$item.url;error=$_.Exception.Message;absence_not_inferred=$true}) }
}
if ($mirrorRevision) {
    foreach ($task in @('pusht','reacher')) {
        $checksumUrl = "https://huggingface.co/datasets/PeterLiZijia/nfwm/resolve/$mirrorRevision/datasets/$task/SHA256SUMS"
        try { [void]$records.Add([ordered]@{kind="mirror-$task-checksums";url=$checksumUrl;text=(Get-WmSmallText $checksumUrl);interpretation='A third-party checksum can corroborate byte identity, not authenticate historical episode roots'}) }
        catch { [void]$records.Add([ordered]@{kind="mirror-$task-checksums";url=$checksumUrl;error=$_.Exception.Message;absence_not_inferred=$true}) }
    }
}
$wmDeepClient.Dispose()
[ordered]@{domain='public-source-metadata-only';observed_utc=[DateTime]::UtcNow.ToString('o');records=$records;research_payload_or_header_reads=0;checkpoint_downloads=0;research_execution=$false} | ConvertTo-Json -Depth 12
