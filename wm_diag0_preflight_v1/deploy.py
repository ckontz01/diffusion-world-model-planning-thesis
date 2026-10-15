"""Exactly one exclusive upload and held CPU submission; never automatic retry."""
import hashlib
import json
import sys
from wm_diag0_preflight_v1.common import *
from wm_diag0_preflight_v1.build import blobs
from wm_diag0_preflight_v1.transport import ssh
from wm_diag0_preflight_v1.preserve import volume,git

def published():
    r=json.loads((DOC/'SSD-VERIFIED-001.json').read_text()); c=identity(DOC/'CONTRACT.json')
    if r['status']!='WHOLE_AND_EVERY_MEMBER_VERIFIED' or r['contract']!=c: raise ValueError('preservation gate')
    if git('ls-remote','origin','refs/heads/world-model-diagnostic-preparation-20261004').decode().split()[0]!=r['source_commit']: raise ValueError('remote source hash')
    if hashlib.sha256(git('show',r['source_commit']+':'+DOCREL+'/CONTRACT.json')).hexdigest()!=c['sha256']: raise ValueError('published contract')
    volume()
    if identity(r['archive'])!=r['whole']: raise ValueError('SSD archive changed')
    return c['sha256']

def stage():
    expected=published(); items=blobs(); c=json.loads((DOC/'CONTRACT.json').read_text())
    if {n:{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for n,b in items.items()}!=c['staged_members']: raise ValueError('source changed after freeze')
    items['CONTRACT.json']=(DOC/'CONTRACT.json').read_bytes()
    rows=[{'name':n,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for n,b in sorted(items.items())]
    header=json.dumps(rows).encode()+b'\n'
    payload=header+b''.join(items[r['name']] for r in rows)
    write_new(DOC/'STAGE-001.started.json',{'contract_sha256':expected,'bytes':len(payload),'run':RUN})
    code='RUN='+repr(RUN)+'\nEXPECTED='+repr(expected)+'\n'+'''
import hashlib,json,os,pathlib,sys,time
root=pathlib.Path(RUN); root.mkdir(parents=True,exist_ok=False)
for n in ('source','controls','logs','output','tmp'): (root/n).mkdir()
with (root/'controls/STAGING-STARTED.json').open('x') as f: json.dump({'time':time.time(),'expected_contract':EXPECTED},f)
rows=json.loads(sys.stdin.buffer.readline(200000))
if len(rows)>100 or sum(r['bytes'] for r in rows)>270000000: raise RuntimeError('upload bound')
names=[r['name'] for r in rows]
if len(names)!=len(set(names)): raise ValueError('duplicate upload members')
for r in rows:
 name=r['name']; p=pathlib.PurePosixPath(name)
 if p.is_absolute() or '..' in p.parts or chr(92) in name or ':' in name: raise ValueError('upload path')
 target=root/'source'/name; target.parent.mkdir(parents=True,exist_ok=True)
 h=hashlib.sha256(); remaining=r['bytes']
 with target.open('xb') as f:
  while remaining:
   raw=sys.stdin.buffer.read(min(1048576,remaining))
   if not raw: raise EOFError('preserve incomplete upload')
   f.write(raw); h.update(raw); remaining-=len(raw)
  f.flush(); os.fsync(f.fileno())
 if h.hexdigest()!=r['sha256']: raise ValueError('uploaded identity')
 target.chmod(0o444)
if sys.stdin.buffer.read(1): raise ValueError('unexpected extra upload bytes')
if hashlib.sha256((root/'source/CONTRACT.json').read_bytes()).hexdigest()!=EXPECTED: raise ValueError('contract identity')
result={'status':'EXCLUSIVE_STAGE_AUTHENTICATED','contract_sha256':EXPECTED,'members':len(rows),'bytes':sum(r['bytes'] for r in rows)}
with (root/'controls/STAGING-VERIFIED.json').open('x') as f: json.dump(result,f,sort_keys=True)
for p in sorted((root/'source').rglob('*'),reverse=True):
 if p.is_dir(): p.chmod(0o555)
(root/'source').chmod(0o555)
print(json.dumps(result))
'''
    result=ssh(code,payload=payload)
    write_new(DOC/'STAGE-001.json',result); print(json.dumps(result))

def submit():
    expected=published(); reservation(1200)
    write_new(DOC/'SUBMIT-001.started.json',{'contract_sha256':expected,'attempts':1,'allocation_seconds':1200,'no_requeue':True})
    code='RUN='+repr(RUN)+'\nEXPECTED='+repr(expected)+'\n'+'''
import hashlib,json,os,pathlib,subprocess,time
root=pathlib.Path(RUN); control=root/'controls'
def write(p,r):
 with p.open('x') as f: json.dump(r,f,sort_keys=True)
if (control/'DISPATCH.json').exists() or (control/'SUBMIT-STARTED.json').exists(): raise RuntimeError('never submit twice/ambiguous')
if json.loads((control/'STAGING-VERIFIED.json').read_text())['contract_sha256']!=EXPECTED: raise ValueError('stage identity')
if hashlib.sha256((root/'source/CONTRACT.json').read_bytes()).hexdigest()!=EXPECTED: raise ValueError('contract identity')
queue=subprocess.check_output(['squeue','-u',str(os.getuid()),'-h','-o','%i|%j|%T'],universal_newlines=True)
if any('wm-a2-' in line for line in queue.splitlines()): raise RuntimeError('existing study allocation; reconcile first')
write(control/'SUBMIT-STARTED.json',{'time':time.time(),'contract_sha256':EXPECTED,'queue':queue,'max_attempts':1})
script='#!/bin/bash\\nset -eu\\numask 077\\nexport PYTHONDONTWRITEBYTECODE=1\\nexport PYTHONPATH='+str(root/'source')+'\\nexec python3 -B -m wm_diag0_preflight_v1.supervisor '+RUN+' '+EXPECTED+'\\n'
p=subprocess.run(['sbatch','--parsable','--hold','--no-requeue','--job-name=wm-a2-preflight-v1','--partition=defq','--nodes=1','--ntasks=1','--cpus-per-task=4','--mem=8192M','--time=00:20:00','--chdir='+str(root/'source'),'--output='+str(root/'logs/bootstrap.log'),'--error='+str(root/'logs/bootstrap.log')],input=script,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=20)
write(control/'SBATCH-RESPONSE.json',{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
if p.returncode: raise RuntimeError('sbatch failed; preserve evidence, no retry')
job=p.stdout.strip().split(';')[0]
if not job.isdigit(): raise RuntimeError('ambiguous job ID; no retry/release')
r={'job_id':job,'contract_sha256':EXPECTED,'allocation_seconds_reserved':1200,'cpu_full_future_other':12600,'gpu_full_future':468000,'held_until_dispatch_receipt':True}
write(control/'DISPATCH.json',r)
p=subprocess.run(['scontrol','release',job],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=15)
write(control/'RELEASE-RESPONSE.json',{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
r['release_returncode']=p.returncode
print(json.dumps(r))
'''
    result=ssh(code); write_new(DOC/'DISPATCH-001.json',result); print(json.dumps(result))

if __name__=='__main__':
    if sys.argv[1]=='stage': stage()
    elif sys.argv[1]=='submit': submit()
    else: raise ValueError('stage or submit only')
