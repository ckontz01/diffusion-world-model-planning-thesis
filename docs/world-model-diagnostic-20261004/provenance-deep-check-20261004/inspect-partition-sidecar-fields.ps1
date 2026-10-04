# Exact small partition metadata sidecars only. Do not read selected-row TSVs,
# historical outcomes, HDF5 headers, data payloads, or model files.
$ErrorActionPreference = 'Stop'
$wmPartitionQuery = @'
python3 -B - <<'PY'
import hashlib,json,pathlib
root=pathlib.Path('/lustreFS/data/superworld/ckontzias/thesis/manifests/partitions')
out=[]
for task in ('pusht','reacher'):
    for name in ('episodes-seed-20260728-summary.json','p1-train-val-seed-20260728-summary.json'):
        p=root/(task+'-v1')/name
        if not p.is_file() or p.stat().st_size>10000: raise RuntimeError('Exact small metadata file unavailable or exceeds cap')
        raw=p.read_bytes(); d=json.loads(raw)
        allowed=('seed','partition_seed','selection_seed','generation_seed','reset_seed','root_seed','source','dataset','dataset_sha256','source_sha256','note','notes','schema','status','source_file')
        out.append(dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),fields=sorted(d.keys()),metadata={k:d[k] for k in allowed if k in d}))
print(json.dumps(dict(domain='partition-source-metadata-only',records=out,payload_or_header_reads=0,research_execution=False)))
PY
'@
$wmPartitionRows = @(wsl.exe -d Thesis-Ubuntu -u chris -- ssh -o BatchMode=yes -o ConnectTimeout=20 prometheus $wmPartitionQuery)
if ($LASTEXITCODE -ne 0) { throw 'Exact partition metadata observation failed; no absence inferred' }
$wmPartitionRows
