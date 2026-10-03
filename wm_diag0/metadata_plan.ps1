# Metadata-only stdout. Never opens HDF5 pixels, actions, states or checkpoints.
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$roles = Get-Content -Raw -LiteralPath "$repo/docs/world-model-diagnostic-20261004/ROLE-PROPOSAL.json" | ConvertFrom-Json
$result = @{}
foreach ($task in 'pusht','reacher') {
    $remote = "/lustreFS/data/superworld/ckontzias/thesis/manifests/partitions/$task-v1/episodes-seed-20260728.tsv"
    $raw = @(wsl.exe -d Thesis-Ubuntu -u chris -- ssh -o BatchMode=yes -o ConnectTimeout=20 prometheus "cat $remote")
    if ($LASTEXITCODE -ne 0) { throw "Metadata transport failed for $task" }
    # These authenticated TSV masters use CRLF. PowerShell removes line
    # terminators from native stdout; reconstruct the ORIGINAL bytes.
    $bytes = [Text.Encoding]::UTF8.GetBytes(($raw -join "`r`n")+"`r`n")
    $hash = [BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash($bytes)).Replace('-','').ToLower()
    if ($hash -ne $roles.$task.master_sha256) { throw 'Canonical metadata hash changed' }
    $all = $raw | ConvertFrom-Csv -Delimiter "`t"
    $offset = 0
    $indexed = @{}
    foreach($row in $all) {
        $id = [int]$row.episode_id; $length = [int]$row.episode_length
        $indexed[$id] = @{ parent=$id; length=$length; offset=$offset; partition=$row.partition }
        $offset += $length
    }
    $entries = @()
    foreach($role in 'diagnostic','fit','validation') {
        foreach($id in $roles.$task.$role) {
            $row = $indexed[[int]$id]
            if ($row.partition -ne 'P2') { throw 'Protected-role proposal' }
            if ($row.length -lt 31 -or $row.length -gt 425) { throw 'Source length requires review; no substitution' }
            $start = [int][Math]::Floor(($row.length-25)/2)
            $frames = @()
            if ($role -ne 'diagnostic') {
                $count = if ($role -eq 'fit') { 16 } else { 8 }
                # At least two preceding frames are reserved for compatibility;
                # checkpoints requiring longer history remain blocked.
                for($i=0;$i -lt $count;$i++) { $frames += 2+[int][Math]::Floor($i*($row.length-3)/($count-1)) }
                if (($frames | Select-Object -Unique).Count -ne $count) { throw 'Too few unique frames' }
            }
            $entries += [ordered]@{task=$task;role=$role;parent=[int]$id;partition='P2';length=$row.length;
                episode_offset=$row.offset;source_step=$start;goal_step=$start+24;source_row=$row.offset+$start;
                goal_row=$row.offset+$start+24;readout_steps=$frames;replay_actions=$start}
        }
    }
    $result[$task] = @{master_sha256=$hash;metadata_path=$remote;entries=$entries}
}
[ordered]@{domain='metadata-only';status='PROPOSED_NOT_ALLOCATED';payload_reads=0;tasks=$result} | ConvertTo-Json -Depth 8 -Compress
