"""Authenticate the exact single-noise executions and E3 timing boundary."""
import base64, hashlib, json, subprocess, time
from pathlib import Path
from recover import ROOT, OUT
from profile import DOC, sha

def main():
    started=time.monotonic()
    s=json.loads((OUT/'results/acid-alternative/analysis/d1/sensitivity/job-297131/summary.json').read_text())
    requested=[r for r in s['runs'] if r['setting']=='pop300-lambda007-sigma025']
    script="""
import base64,hashlib,json,pathlib,time
R=pathlib.Path('/lustreFS/data/superworld/ckontzias/thesis')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
paths=REQUESTED
for r in paths:
 if sha(pathlib.Path(r['summary']))!=r['summary_sha256']:raise RuntimeError('single-noise receipt mismatch')
files=[pathlib.Path(r['summary']) for r in paths]
files+=list(R.glob('results/acid-alternative/e3-d2-exploratory/analysis/*/summary.json'))
files+=list(R.glob('results/acid-alternative/e3-d2-exploratory/closed-loop/*/*/*/summary.json'))
files+=list(R.glob('snapshots/acid-alt-e3-d2-323318f12407690c/SOURCE-MANIFEST.sha256'))
out=[]
for p in files:
 b=p.read_bytes()
 if len(b)>2000000:raise RuntimeError('metadata byte cap')
 out.append(dict(path=str(p.relative_to(R)),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b),data=base64.b64encode(b).decode()))
runtime=[]
code=R/'src/hi-lewm'
for p in sorted(code.rglob('*.py')):
 if '.git' not in p.parts:
  runtime.append(dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p)))
print(json.dumps(dict(files=out,model_runtime_sources=runtime,observed_unix=time.time())))
""".replace('REQUESTED',repr(requested))
    r=subprocess.run(['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','ssh','-T','-o','BatchMode=yes','prometheus','python3.9 -'],input=script.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=180)
    if r.returncode:raise RuntimeError(r.stderr.decode())
    receipt=json.loads(r.stdout)
    for row in receipt['files']:
        b=base64.b64decode(row.pop('data'));assert hashlib.sha256(b).hexdigest()==row['sha256']
        p=OUT/row['path'];p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f:f.write(b)
    receipt['local_wall_seconds']=time.monotonic()-started
    with (DOC/'FINAL-RECOVERY.json').open('x') as f:json.dump(receipt,f,indent=2)
    rows=[]
    for p in OUT.glob('results/acid-alternative/e3-d2-exploratory/closed-loop/*/*/*/summary.json'):
        v=json.loads(p.read_text())
        rows.append(dict(study='E3 boundary only, not a DTV candidate',task=v['task'],arm=v['arm'],scorer_seed=v['scorer_seed'],planner_seed=v['planner_seed'],elapsed_seconds=v['elapsed_seconds'],scope='50-episode evaluator total including physics; not standalone checker',episode_count=v['episode_count'],cost_calls=v['cem_cost_calls'],sequences=v['cem_cost_calls']*300,transitions=v['cem_cost_calls']*1500,warmup='no separate dedicated latency warmup',runtime=v['runtime'],artifact=str(p.relative_to(OUT)),artifact_sha256=sha(p),source_manifest_sha256=v['source_manifest_sha256']))
    with (DOC/'E3-TIMINGS.json').open('x') as f:json.dump(rows,f,indent=2)
    print('single-noise runs',len(requested),'E3 raw timing records',len(rows),'additional model runtime source hashes',len(receipt['model_runtime_sources']))
if __name__=='__main__':main()
