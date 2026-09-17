"""Terminal accounting and byte-preserving backup; never interpret scientific outputs."""
import hashlib,json,subprocess,tarfile,time
from pathlib import Path
R=Path('/lustreFS/data/superworld/ckontzias/thesis')
V='candidate-value-score-information-20260918'
source=R/'snapshots'/(V+'-68145e6458da0b90')
run=R/'experiments'/V
stage=R/'staging/cvl-score-information-preparation-20260918'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def put(p,value):
    with p.open('x') as f:json.dump(value,f,indent=2,sort_keys=True);f.write('\n')
cmd=['sacct','-j','301953','--parsable2','--format=JobID,JobName,Partition,State,ExitCode,ElapsedRaw,AllocCPUS,ReqMem,AllocTRES,MaxRSS,TotalCPU,Submit,Start,End']
raw=subprocess.check_output(cmd).decode();lines=raw.strip().splitlines();keys=lines[0].split('|')
rows=[dict(zip(keys,x.split('|'))) for x in lines[1:]]
parent=next(r for r in rows if r['JobID']=='301953')
assert parent['State']=='COMPLETED' and parent['ExitCode']=='0:0'
assert parent['AllocCPUS']=='4' and int(parent['ElapsedRaw'])<=7200 and 'gres/gpu' not in parent['AllocTRES']
worker=run/'run-68145e6458da0b90';seen=set()
for line in (worker/'sha256.txt').read_text().splitlines():
    h,n=line.split('  ',1);p=worker/n
    assert not p.is_symlink() and worker in p.resolve().parents and sha(p)==h
    seen.add(n)
assert seen=={p.relative_to(worker).as_posix() for p in worker.rglob('*') if p.is_file() and p.name!='sha256.txt'}
assert len(list(worker.glob('fold-*/*-820*.npz')))==24
assert len(list(worker.glob('fold-*/normalization.npz')))==4
assert len(list(worker.glob('fold-*/FREEZE.json')))==4
assert len(list(worker.glob('fold-*/predictions.json')))==4
put(run/'control/ACCOUNTING.json',dict(job=301953,utc=time.time(),command=cmd,rows=rows,worker_seal_sha256=sha(worker/'sha256.txt'),verified_worker_members=len(seen)))
paths=[]
for prefix,root in [('source',source),('run',run)]:
    for p in sorted(root.rglob('*')):
        if p.is_file():
            assert not p.is_symlink();paths.append((prefix+'/'+p.relative_to(root).as_posix(),p))
for name in ('launch_once.py','launch_once-v2.py','preserve_completed.py'):
    paths.append(('operations/'+name,stage/name))
members=[dict(name=n,bytes=p.stat().st_size,sha256=sha(p)) for n,p in paths]
payload=sum(m['bytes'] for m in members);assert payload<1000000000
assert sum(m['bytes'] for m in members if not m['name'].startswith('run/run-'))<100000000
archive=stage/'SI1-COMPLETE.tar'
with tarfile.open(str(archive),'x') as tar:
    for n,p in paths:tar.add(str(p),arcname=n,recursive=False)
assert payload+archive.stat().st_size<1000000000
put(stage/'BACKUP-MANIFEST.json',dict(archive_sha256=sha(archive),archive_bytes=archive.stat().st_size,
    unique_payload_bytes=payload,remote_bytes_including_archive=payload+archive.stat().st_size,
    members=members,complete=True,scientific_results_read=False))
print(json.dumps(dict(archive=str(archive),sha256=sha(archive),bytes=archive.stat().st_size,payload_bytes=payload)))
