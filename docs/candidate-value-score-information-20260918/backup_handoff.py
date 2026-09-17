"""Copy the final documentation supplement to the designated SSD; verify each byte."""
import hashlib,json,shutil,time
from pathlib import Path
d=Path(__file__).resolve().parent
ssd=Path('/mnt/d/THESIS-BACKUPS/candidate-value-score-information-20260918')
target=ssd/'execution-68145e6458da0b90/handoff';target.mkdir(exist_ok=False)
files=[(x.name,x) for x in d.iterdir() if x.is_file()]+[('THESIS-README.md',d.parents[1]/'README.md')]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
members=[]
for name,src in sorted(files):
    dst=target/name;shutil.copyfile(src,dst);assert sha(src)==sha(dst)
    members.append(dict(name=name,bytes=dst.stat().st_size,sha256=sha(dst)))
remote_bytes=425740+20007830+20825041
ssd_bytes=sum(p.stat().st_size for p in ssd.rglob('*') if p.is_file())
doc_bytes=sum(p.stat().st_size for _,p in files)
receipt=dict(verified=True,utc=time.time(),members=members,remote_source_run_staging_bytes=remote_bytes,
    external_preparation_archive_manifest_receipt_handoff_bytes=ssd_bytes,local_documentation_bytes=doc_bytes,
    measured_materialized_bytes_before_this_receipt=remote_bytes+ssd_bytes+doc_bytes,
    ceiling_bytes=1000000000,notes='Conservative scope includes preparation lineage staging and duplicate copies; excludes pre-existing research data, WSL recovery VHDX, Git database and filesystem block overhead. Receipt itself adds only a few KB.')
assert receipt['measured_materialized_bytes_before_this_receipt']<100000000
data=(json.dumps(receipt,indent=2,sort_keys=True)+'\n').encode()
for p in (target/'HANDOFF-RECEIPT.json',d/'HANDOFF-RECEIPT.json'):
    with p.open('xb') as f:f.write(data)
print(json.dumps({k:v for k,v in receipt.items() if k!='members'},indent=2))
