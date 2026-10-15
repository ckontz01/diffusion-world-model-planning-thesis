"""Source-only stage and one held 120-element serial array; no automatic retry."""
import hashlib,json,sys
from .common import *
from .build import blobs
from .transport import ssh
from wm_diag0_preflight_v1.preserve import git,volume

def published():
    r=json.loads((DOC/'SSD-VERIFIED-001.json').read_text())
    if r['status']!='WHOLE_AND_EVERY_MEMBER_VERIFIED' or identity(DOC/'CONTRACT.json')!=r['contract']:raise ValueError('source preservation gate')
    remote=git('ls-remote','origin','refs/heads/world-model-diagnostic-preparation-20261004').decode().split()[0]
    if remote!=r['source_commit']:raise ValueError('full remote source hash')
    if hashlib.sha256(git('show',remote+':'+DOCREL+'/CONTRACT.json')).hexdigest()!=r['contract']['sha256']:raise ValueError('published contract bytes')
    volume()
    for k in ('source_package','renderer_package'):
        if identity(r[k]['archive'])!=r[k]['whole']:raise ValueError('SSD package changed')
    return r['contract']['sha256']

def stage():
    expected=published();c=json.loads((DOC/'CONTRACT.json').read_text());data=blobs()
    if {n:{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for n,b in data.items()}!=c['staged_members']:raise ValueError('frozen source changed')
    data['CONTRACT.json']=(DOC/'CONTRACT.json').read_bytes()
    rows=[{'name':n,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for n,b in sorted(data.items())]
    payload=json.dumps(rows).encode()+b'\n'+b''.join(data[r['name']] for r in rows)
    write_new(DOC/'STAGE-001.started.json',{'expected':expected,'bytes':len(payload)})
    code='RUN='+repr(RUN)+'\nEXPECTED='+repr(expected)+'\n'+'''
import hashlib,json,os,pathlib,sys,time
r=pathlib.Path(RUN);source=r/'source';control=r/'controls'
if any(source.iterdir()) or (control/'STAGE-STARTED.json').exists():raise RuntimeError('reconcile prior/ambiguous stage')
with (control/'STAGE-STARTED.json').open('x') as f:json.dump({'contract_sha256':EXPECTED,'time':time.time()},f)
rows=json.loads(sys.stdin.buffer.readline(200000))
if len(rows)>1000 or sum(x['bytes'] for x in rows)>5000000 or len({x['name'] for x in rows})!=len(rows):raise ValueError('finite source stage')
for x in rows:
 n=x['name'];p=pathlib.PurePosixPath(n)
 if p.is_absolute() or '..' in p.parts or chr(92) in n or ':' in n:raise ValueError('source member path')
 b=sys.stdin.buffer.read(x['bytes'])
 if len(b)!=x['bytes'] or hashlib.sha256(b).hexdigest()!=x['sha256']:raise ValueError('exact source bytes')
 target=source/n;target.parent.mkdir(parents=True,exist_ok=True)
 with target.open('xb') as f:f.write(b)
 target.chmod(0o444)
if sys.stdin.buffer.read(1):raise ValueError('trailing stage bytes')
if hashlib.sha256((source/'CONTRACT.json').read_bytes()).hexdigest()!=EXPECTED:raise ValueError('contract')
for p in sorted(source.rglob('*'),reverse=True):
 if p.is_dir():p.chmod(0o555)
source.chmod(0o555)
row={'status':'SOURCE_STAGE_AUTHENTICATED','members':len(rows),'bytes':sum(x['bytes'] for x in rows),'contract_sha256':EXPECTED}
with (control/'STAGE-VERIFIED.json').open('x') as f:json.dump(row,f,sort_keys=True)
print(json.dumps(row))
'''
    r=ssh(code,payload=payload);write_new(DOC/'STAGE-001.json',r);print(json.dumps(r))

def submit():
    expected=published()
    if 17+120*60+3600+1800>13800:raise ValueError('all charges and full CPU future')
    write_new(DOC/'SUBMIT-SOURCE-001.started.json',{'contract_sha256':expected,'tasks':120,'task_seconds':60,'replacements':0})
    code='RUN='+repr(RUN)+'\nEXPECTED='+repr(expected)+'\n'+'''
import hashlib,json,os,pathlib,subprocess,time
r=pathlib.Path(RUN);control=r/'controls'
def write(n,x):
 with (control/n).open('x') as f:json.dump(x,f,sort_keys=True)
if any((control/n).exists() for n in ('DISPATCH-source.json','SUBMIT-source-STARTED.json','STOP.json')):raise RuntimeError('reconcile existing/ambiguous study state')
if json.loads((control/'STAGE-VERIFIED.json').read_text())['contract_sha256']!=EXPECTED:raise ValueError('verified stage')
if json.loads((control/'RENDERER-R6-TEST.json').read_text())['returncode']!=0:raise ValueError('software rendering gate')
if json.loads((control/'NATIVE-IMPORT-CHECK.json').read_text())['returncode']!=0:raise ValueError('new native import gate')
queue=subprocess.check_output(['squeue','-u',str(os.getuid()),'-h','-o','%i|%j|%T'],universal_newlines=True)
active=[line for line in queue.splitlines() if 'wm-a2-' in line]
if active:raise RuntimeError('existing study allocation; reconcile first')
write('SUBMIT-source-STARTED.json',{'time':time.time(),'contract_sha256':EXPECTED,'array_elements':120,'replacements':0})
script=chr(10).join(['#!/bin/bash','set -eu','umask 077','export PYTHONDONTWRITEBYTECODE=1','export PYTHONPATH='+str(r/'source'),'exec python3 -B -m wm_diag0_native_v3.supervisor '+RUN+' '+EXPECTED+' source',''])
p=subprocess.run(['sbatch','--parsable','--hold','--no-requeue','--job-name=wm-a2-source-v3','--partition=defq','--nodes=1','--ntasks=1','--cpus-per-task=4','--mem=8192M','--time=00:01:00','--array=0-119%1','--chdir='+str(r/'source'),'--output='+str(r/'logs/source-%A_%a.log'),'--error='+str(r/'logs/source-%A_%a.log')],input=script,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=20)
write('SBATCH-source-RESPONSE.json',{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
if p.returncode:raise RuntimeError('sbatch failed; no retry')
job=p.stdout.strip().split(';')[0]
if not job.isdigit():raise RuntimeError('ambiguous submission; no release/retry')
d={'job_id':job,'contract_sha256':EXPECTED,'array_elements':120,'allocation_seconds_each':60,'full_future_source_seconds':7200,'CPU_charged_before':17,'CPU_other_full_future_seconds':5400,'GPU_full_future_seconds':468000,'maximum_concurrency':1,'replacements':0}
write('DISPATCH-source.json',d)
p=subprocess.run(['scontrol','release',job],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=10)
write('RELEASE-source-RESPONSE.json',{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
d['release_returncode']=p.returncode
print(json.dumps(d))
'''
    r=ssh(code);write_new(DOC/'DISPATCH-SOURCE-001.json',r);print(json.dumps(r))

if __name__=='__main__':
    if sys.argv[1]=='stage':stage()
    elif sys.argv[1]=='submit':submit()
    else:raise ValueError('stage or submit')
