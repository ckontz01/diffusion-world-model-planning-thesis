"""Second narrow metadata pass: authenticate bytes, not tensor contents."""
import base64, hashlib, json, subprocess, time
from pathlib import Path
from recover import ROOT, OUT

def main():
    specs=[]
    for p in OUT.glob('results/acid-alternative/scorers/*/*/true/*/summary.json'):
        s=json.loads(p.read_text()); specs.append({'path':s['checkpoint'],'sha256':s['checkpoint_sha256'],'kind':'checkpoint'})
    for p in OUT.glob('results/acid-alternative/diagnostics/*/d1-b0-candidate-pools/*/manifest.json'):
        s=json.loads(p.read_text())
        for path,sha,kind in [(s['artifact'],s['artifact_sha256'],'input'),(s['world_model_checkpoint'],s['world_model_checkpoint_sha256'],'world_model')]:
            specs.append(dict(path=path,sha256=sha,kind=kind))
    remote="""
import base64, hashlib, json, pathlib, time
R=pathlib.Path('/lustreFS/data/superworld/ckontzias/thesis')
specs=SPECIFICATIONS
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''): h.update(b)
 return h.hexdigest()
records=[]
for s in specs:
 p=pathlib.Path(s['path']); row=dict(s,exists=p.is_file())
 if p.is_file():
  row.update(bytes=p.stat().st_size,actual_sha256=digest(p))
  if row['actual_sha256']!=s['sha256']: raise RuntimeError('identity mismatch '+str(p))
 records.append(row)
patterns=['snapshots/acid-alt-v3-d2-2c8f890c31e9f5bf/acid_alt_d2_models.py','results/acid-alternative/e6-d2-quantile/closed-loop/*/acid_cont/seed-6101-8301-job-297656-*/summary.json','results/acid-alternative/e6-d2-quantile/closed-loop/*/rdx_gate_all_q40/seed-6101-8301-job-297656-*/summary.json','results/acid-alternative/e6-d2-quantile/analysis/job-297657/summary.json','results/acid-alternative/diagnostics/pusht/d1-candidate-scores/job-297056/manifest.json','results/acid-alternative/diagnostics/reacher/d1-candidate-scores/job-297162/manifest.json','results/acid-alternative/diagnostics/cube/d1-candidate-scores/job-297080/manifest.json']
files=[]
for pattern in patterns:
 for p in sorted(R.glob(pattern)):
  if p.stat().st_size>2000000: raise RuntimeError('metadata cap')
  data=p.read_bytes(); files.append(dict(path=str(p.relative_to(R)),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),data=base64.b64encode(data).decode()))
env=R/'envs/hi-lewm-artifact-py311-cu121-swm006/lib/python3.11/site-packages/stable_worldmodel'
runtime=[]
for p in sorted(env.rglob('*.py')):
 runtime.append(dict(path=str(p),bytes=p.stat().st_size,sha256=digest(p)))
for name in ['solver/cem.py','solver/solver.py','policy/planning.py','policy/cost_model.py']:
 p=env/name
 if p.is_file():
  data=p.read_bytes();files.append(dict(path='runtime/stable_worldmodel/'+name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),data=base64.b64encode(data).decode()))
print(json.dumps(dict(observed_unix=time.time(),records=records,files=files,runtime=runtime)))
""".replace('SPECIFICATIONS',repr(specs))
    started=time.monotonic()
    r=subprocess.run(['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','ssh','-T','-o','BatchMode=yes','prometheus','python3.9 -'],input=remote.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=180)
    if r.returncode: raise RuntimeError(r.stderr.decode())
    receipt=json.loads(r.stdout)
    for item in receipt['files']:
        data=base64.b64decode(item.pop('data')); assert hashlib.sha256(data).hexdigest()==item['sha256']
        p=OUT/item['path'];p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f:f.write(data)
    receipt['local_wall_seconds']=time.monotonic()-started
    receipt['checkpoint_deserialization']=False
    with (OUT/'AUTHENTICATED-BYTES.json').open('x') as f:json.dump(receipt,f,indent=2)
    print('authenticated_byte_records',len(receipt['records']),'recovered_files',len(receipt['files']),'runtime_sources',len(receipt['runtime']))
if __name__=='__main__':main()
