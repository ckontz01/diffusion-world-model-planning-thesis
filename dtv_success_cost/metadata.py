"""Read canonical source-role metadata and runtime text; never research payloads."""
import base64
import hashlib
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / 'docs/dtv-success-cost-20261001'
REMOTE = r'''
import base64,hashlib,json,pathlib,time
R=pathlib.Path('/lustreFS/data/superworld/ckontzias/thesis'); files=[]; total=0
paths=[]
for task in ('pusht','reacher','cube'):
 paths += list((R/'manifests/partitions'/ (task+'-v1')).glob('*.tsv'))
 paths += list((R/'manifests/partitions'/ (task+'-v1')).glob('*summary.json'))
 for study in ('acid-alternative-v1','acid-alternative-v3-d2','gdp-cem-e11-d3','gdp-cem-e13-d4'):
  paths += list((R/'manifests'/study/task).rglob('*.tsv'))
  if study=='acid-alternative-v1':paths += list((R/'manifests'/study/task).glob('summary.json'))
S=R/'envs/hi-lewm-artifact-py311-cu121-swm006/lib/python3.11/site-packages/stable_worldmodel'
paths += [S/n for n in ('world.py','wrapper.py','data/dataset.py','envs/pusht/env.py','envs/dmcontrol/reacher.py','envs/ogbench/cube_env.py')]
paths += [R/'src/hi-lewm/third_party/lewm/config/eval'/ (t+'.yaml') for t in ('pusht','reacher','cube')]
for p in sorted(set(paths)):
 if not p.is_file():raise RuntimeError('missing required metadata/code '+str(p))
 b=p.read_bytes();total+=len(b)
 if len(b)>10000000 or total>25000000:raise RuntimeError('metadata recovery cap')
 files.append(dict(path=str(p.relative_to(R)),bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),data=base64.b64encode(b).decode()))
print(json.dumps(dict(files=files,total_bytes=total,observed_unix=time.time(),payload_reads=0,inference=False,physics=False)))
'''

def main():
    output = DOC/'metadata'
    if output.exists(): raise RuntimeError('exclusive metadata receipt already exists')
    start=time.monotonic()
    r=subprocess.run(['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=15','prometheus','python3.9 -'],input=REMOTE.encode(),capture_output=True,timeout=90)
    if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace'))
    value=json.loads(r.stdout); output.mkdir(parents=True)
    for item in value['files']:
        b=base64.b64decode(item.pop('data'))
        if hashlib.sha256(b).hexdigest()!=item['sha256']:raise RuntimeError('transport hash mismatch')
        p=output/item['path'];p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f:f.write(b)
    value['local_wall_seconds']=time.monotonic()-start
    with (DOC/'METADATA-RECEIPT.json').open('x') as f:json.dump(value,f,indent=2)
    print(json.dumps({k:v for k,v in value.items() if k!='files'}));print('files',len(value['files']))
if __name__=='__main__':main()
