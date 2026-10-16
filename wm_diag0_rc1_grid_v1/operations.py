"""Exact124-parent dispatch only after terminal independent all-four-gate proof."""
import base64,json,sys
from .common import *
from .prepare import additions
from .observer import OBSERVE
from .scheduler import SOURCE,HISTORY
from wm_diag0_native_v3.transport import ssh

STAGE=SOURCE+HISTORY+r'''
import base64,hashlib,json,os,pathlib,subprocess,sys
r=pathlib.Path(RUN);data=json.load(sys.stdin);raw=base64.b64decode(data['contract']);c=json.loads(raw)
def ident(p):
 h=hashlib.sha256();size=0
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b);size+=len(b)
 return {'bytes':size,'sha256':h.hexdigest()}
def write(n,x):
 with (r/'controls'/n).open('x') as f:json.dump(x,f,sort_keys=True)
if hashlib.sha256(raw).hexdigest()!=EXPECTED or not c['rc1_grid']['grid_authorized'] or c['gpu_stages_authorized']:raise ValueError('exact grid-only contract')
q,a,queue_diagnostic=exact_snapshot('317163,317164,317165,317166,317172,317173,317174,317175,317177',set(HISTORY_EXPECTED)|HISTORY_UNALLOCATED)
if q.strip():raise ValueError('old/gate/head/technical allocation still live or ambiguous')
rows,gpu=all_before_grid(a)
if gpu!=c['rc1_grid']['GPU_charged_before'] or gpu+124*3600>468000 or c['rc1_grid']['all_attempts_full_future']!=138:raise ValueError('failure-inclusive/full-future accounting')
troot=pathlib.Path(c['rc1_grid']['technical_run'])
if (troot/'controls/STOP.json').exists() or ident(troot/'source/TECHNICAL-CONTRACT.json')!=c['rc1_grid']['technical_contract']:raise ValueError('actual accepted technical closure')
if set(c['rc1_grid']['technical_suppliers'])!={'0','1','2','3'}:raise ValueError('ALL four setting gates required')
for k,x in c['rc1_grid']['technical_suppliers'].items():
 t=pathlib.Path(x['run'])/'tasks'/('technical-'+k)
 if ident(t/'controls/ACCEPTED.json')!=x['acceptance_identity'] or ident(t/'output/MEMBERS.json')!=x['output_seal']:raise ValueError('accepted native setting supplier identity')
 aa=json.loads((t/'controls/ACCEPTED.json').read_text());rr=json.loads((t/'controls/RESULT.json').read_text())
 if not aa['accepted'] or rr['status']!='ACCEPTED' or aa['output_seal']!=x['output_seal']:raise ValueError('independent setting acceptance')
 for n,z in json.loads((t/'output/MEMBERS.json').read_text()).items():
  if ident(t/'output'/n)!=z:raise ValueError('accepted native artifact changed')
for i,x in c['rc1_technical']['head_suppliers'].items():
 t=pathlib.Path(c['rc1_technical']['heads_run'])/'tasks'/('readout-'+i)
 if ident(t/'controls/ACCEPTED.json')!=x['acceptance_identity'] or ident(t/'output/MEMBERS.json')!=x['output_seal']:raise ValueError('amended active head supplier')
 for n,z in json.loads((t/'output/MEMBERS.json').read_text()).items():
  if ident(t/'output'/n)!=z:raise ValueError('amended head member changed')
old=pathlib.Path(c['recovery']['old_run'])
if ident(old/'controls/RUNTIME-MANIFEST.json')!=c['runtime_manifest']:raise ValueError('runtime authority')
logical=sum(p.stat().st_size for p in r.parent.rglob('*') if p.is_file())
live=logical+2100000000+3139002368+144694193+620000000+3720000000+124000000+60000000+20000000+300000000
if live>13500000000 or live+500000000>14000000000 or live+28000000000+2874852312>44000000000:raise ValueError('fresh whole-study full-future storage')
r.mkdir(exist_ok=False)
for n in ('source','controls','tasks','logs'):(r/n).mkdir()
for n,x in c['staged_members'].items():
 p=r/'source'/n;p.parent.mkdir(parents=True,exist_ok=True)
 if n in data['additions']:
  b=base64.b64decode(data['additions'][n])
  if {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}!=x:raise ValueError('new frozen source')
  with p.open('xb') as f:f.write(b)
  p.chmod(0o444)
 else:
  source=troot/'source'/n
  if source.is_symlink() or ident(source)!=x:raise ValueError('actual source supplier identity')
  os.link(str(source),str(p))
with (r/'source/GRID-CONTRACT.json').open('xb') as f:f.write(raw)
(r/'source/GRID-CONTRACT.json').chmod(0o444)
os.link(str(old/'controls/RUNTIME-MANIFEST.json'),str(r/'controls/RUNTIME-MANIFEST.json'))
for p in sorted((r/'source').rglob('*'),reverse=True):
 if p.is_dir():p.chmod(0o555)
(r/'source').chmod(0o555)
sys.path.insert(0,str(r/'source'))
from wm_diag0_rc1_grid_v1.resources import before_grid
physical=before_grid(c)
write('ALL-ATTEMPT-PHYSICAL-FUTURE-RESERVATION.json',physical)
write('PUBLICATION-AND-SSD.json',data['publication']);write('ALL-FOUR-GATES-AND-CHARGES.json',{'scheduler':a,'queue_diagnostic':queue_diagnostic,'suppliers':c['rc1_grid']['technical_suppliers'],'GPU_before':gpu,'GPU_full_future':gpu+124*3600,'CPU_before':1436,'CPU_full_future':6836})
write('FRESH-STORAGE.json',{'logical_current_study':logical,'live_full_future':live,'archive_full_future':live+500000000,'inclusive_full_future':live+28000000000+2874852312})
script=chr(10).join(['#!/bin/bash','set -eu','umask 077','export PYTHONDONTWRITEBYTECODE=1','export PYTHONPATH='+str(r/'source'),'exec python3 -B -m wm_diag0_rc1_grid_v1.supervisor '+RUN+' '+EXPECTED,''])
args=['sbatch','--parsable','--hold','--no-requeue','--job-name=wm-a2-rc1-grid-v1','--array=0-123%1','--partition=a6000','--qos=normal-a6000','--nodelist=gpu09','--nodes=1','--ntasks=1','--cpus-per-task=4','--mem=8192M','--gres=gpu:1','--time=60','--chdir='+str(r/'source'),'--output='+str(r/'logs/grid-%A_%a.log'),'--error='+str(r/'logs/grid-%A_%a.log')]
write('SUBMIT-STARTED.json',{'args':args,'contract_sha256':EXPECTED,'GPU_charged_before':gpu,'grid_attempts':124,'automatic_retry':False})
p=subprocess.run(args,input=script,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=20)
write('SBATCH-RESPONSE.json',{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
if p.returncode:raise RuntimeError('submission rejected; no blind retry')
jid=p.stdout.strip().split(';')[0]
if not jid.isdigit():raise RuntimeError('ambiguous dispatch; reconcile no retry')
d={'array_job_id':jid,'indices':124,'contract_sha256':EXPECTED,'allocation_seconds_each':3600,'automatic_retries':0,'grid_dispatched_after_all_four_gates':True}
write('DISPATCH.json',d)
p=subprocess.run(['scontrol','release',jid],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=10)
write('RELEASE-RESPONSE.json',{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
if p.returncode:raise RuntimeError('known held dispatch; reconcile no retry')
print(json.dumps(d))
'''

def main():
    op,label=sys.argv[1:3]
    if not label.isalnum():raise ValueError('exclusive label')
    if op=='stage_submit':
        from .preserve import published
        pub=published();raw=(DOC/'GRID-CONTRACT.json').read_bytes();expected=identity(DOC/'GRID-CONTRACT.json')['sha256']
        write_new(DOC/('SUBMISSION-'+label+'.started.json'),{'contract_sha256':expected,'exact_grid_attempts':124,'no_retry':True})
        z=ssh('RUN='+repr(RUN)+'\nEXPECTED='+repr(expected)+'\n'+STAGE,json.dumps({'contract':base64.b64encode(raw).decode(),'additions':{n:base64.b64encode(b).decode() for n,b in additions().items()},'publication':pub}).encode())
    elif op=='observe':z=ssh('RUN='+repr(RUN)+'\n'+OBSERVE)
    else:raise ValueError('declared operation only')
    write_new(DOC/(op.upper()+'-'+label+'.json'),z);print(json.dumps(z,indent=2))

if __name__=='__main__':main()
