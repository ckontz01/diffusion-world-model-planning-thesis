"""Exact reconciliation, one held/reconciled gate dispatch, bounded observation."""
import base64,json,sys
from .common import *
from .prepare import additions
from wm_diag0_native_v3.transport import ssh
from wm_diag0_numerical_v3.operations import RECONCILE as PREVIOUS_RECONCILE

RECONCILE=PREVIOUS_RECONCILE.replace("+['317172']", "+['317172','317173']").replace('charge!=249','charge!=268')

STAGE=r'''
import base64,hashlib,json,os,pathlib,subprocess,sys
r=pathlib.Path(RUN);old=pathlib.Path(OLD);v3=pathlib.Path(V3);data=json.load(sys.stdin);raw=base64.b64decode(data['contract']);c=json.loads(raw)
def ident(p):
 h=hashlib.sha256();size=0
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b);size+=len(b)
 return {'bytes':size,'sha256':h.hexdigest()}
def write(n,x):
 with (r/'controls'/n).open('x') as f:json.dump(x,f,sort_keys=True)
if hashlib.sha256(raw).hexdigest()!=EXPECTED or not c['rc1']['gate_authorized'] or c['gpu_stages_authorized'] or c['rc1']['GPU_charged_before']!=268:
 raise ValueError('exact RC1 gate-only authorization')
q=subprocess.check_output(['squeue','-h','-j','317163,317164,317165,317166,317172,317173','-o','%i'],universal_newlines=True,timeout=10)
if q.strip():raise ValueError('old live allocation')
for k,x in c['recovery']['accepted_suppliers'].items():
 if ident(old/'tasks'/k/'controls/ACCEPTED.json')!=x['control']:raise ValueError('old accepted control')
 p=old/'tasks'/k/'output/MEMBERS.json'
 if ident(p)!=x['output_seal']:raise ValueError('accepted seal')
 for n,z in json.loads(p.read_text()).items():
  if ident(p.parent/n)!=z:raise ValueError('accepted member changed')
for n,x in c['recovery']['partial'].items():
 if ident(old/'tasks/technical-1/output'/n)!=x:raise ValueError('failed bank partial changed')
vp=v3/'tasks/numerical-validation/output'
if ident(vp/'MEMBERS.json')!=c['rc1']['V3_output_seal'] or ident(vp/'VALIDATION.json')!=c['rc1']['V3_report']:raise ValueError('V3 supplier seals')
for n,x in json.loads((vp/'MEMBERS.json').read_text()).items():
 if ident(vp/n)!=x:raise ValueError('V3 forecast member identity')
if ident(old/'controls/RUNTIME-MANIFEST.json')!=c['runtime_manifest']:raise ValueError('runtime manifest')
r.mkdir(exist_ok=False)
for n in ('source','controls','tasks','logs'):(r/n).mkdir()
for n,x in c['staged_members'].items():
 p=r/'source'/n;p.parent.mkdir(parents=True,exist_ok=True)
 if n in data['additions']:
  b=base64.b64decode(data['additions'][n])
  if {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}!=x:raise ValueError('new source hash')
  with p.open('xb') as f:f.write(b)
  p.chmod(0o444)
 else:
  supplier=v3/'source'/n
  if supplier.is_symlink() or ident(supplier)!=x:raise ValueError('frozen source supplier')
  os.link(str(supplier),str(p))
with (r/'source/RC1-CONTRACT.json').open('xb') as f:f.write(raw)
(r/'source/RC1-CONTRACT.json').chmod(0o444)
os.link(str(old/'controls/RUNTIME-MANIFEST.json'),str(r/'controls/RUNTIME-MANIFEST.json'))
for p in sorted((r/'source').rglob('*'),reverse=True):
 if p.is_dir():p.chmod(0o555)
(r/'source').chmod(0o555)
write('PUBLICATION-AND-SSD.json',data['publication'])
script=chr(10).join(['#!/bin/bash','set -eu','umask 077','export PYTHONDONTWRITEBYTECODE=1','export PYTHONPATH='+str(r/'source'),
 'exec python3 -B -m wm_diag0_rc1_v1.supervisor '+RUN+' '+EXPECTED,''])
args=['sbatch','--parsable','--hold','--no-requeue','--job-name=wm-a2-rc1-gate-v1','--partition=a6000','--qos=normal-a6000','--nodelist=gpu09',
 '--nodes=1','--ntasks=1','--cpus-per-task=4','--mem=8192M','--gres=gpu:1','--time=3','--chdir='+str(r/'source'),
 '--output='+str(r/'logs/gate-%j.log'),'--error='+str(r/'logs/gate-%j.log')]
write('SUBMIT-STARTED.json',{'args':args,'contract_sha256':EXPECTED,'GPU_charged_before':268,'allocation_seconds':180})
p=subprocess.run(args,input=script,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=20)
write('SBATCH-RESPONSE.json',{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
if p.returncode:raise RuntimeError('submission rejected; retain no blind retry')
jid=p.stdout.strip().split(';')[0]
if not jid.isdigit():raise RuntimeError('ambiguous dispatch; no retry')
d={'job_id':jid,'contract_sha256':EXPECTED,'phase':'RC1_gate','allocation_seconds':180,'automatic_retries':0,'campaign_resumed':False}
write('DISPATCH.json',d)
p=subprocess.run(['scontrol','release',jid],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=10)
write('RELEASE-RESPONSE.json',{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
if p.returncode:raise RuntimeError('known held allocation; reconcile no retry')
print(json.dumps(d))
'''

OBSERVE=r'''
import hashlib,json,pathlib,subprocess
r=pathlib.Path(RUN);d=json.loads((r/'controls/DISPATCH.json').read_text());jid=d['job_id']
if not jid.isdigit():raise ValueError('exact dispatch ID')
q=subprocess.check_output(['squeue','-h','-j',jid,'-o','%i|%T|%M|%N|%R'],universal_newlines=True,timeout=10)
a=subprocess.check_output(['sacct','-X','-n','-P','-j',jid,'--format=JobID,State,ExitCode,ElapsedRaw,AllocCPUS,NodeList'],universal_newlines=True,timeout=15)
t=r/'tasks/rc1-gate';p=t/'controls/RESULT.json';result=json.loads(p.read_text()) if p.exists() else None
report=None
if result is not None and result['status']!='FAILED':
 p=t/'output/RC1-GATE.json'
 if {'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}!=result['report_identity']:raise ValueError('authenticated report')
 report=json.loads(p.read_text())
stderr={}
if result is not None and result['status']=='FAILED':
 for p in (t/'logs/worker.log',r/'logs'/('gate-'+jid+'.log')):
  if p.exists():stderr[str(p.relative_to(r))]=p.read_text(errors='replace')[-20000:]
started=t/'controls/STARTED.json';process=None
if started.exists():
 z=json.loads(started.read_text());p=pathlib.Path('/proc')/str(z['PID'])/'stat'
 process={'recorded':z,'PID_exists':p.exists(),'start_ticks_match':p.exists() and p.read_text().rsplit(')',1)[1].split()[19]==str(z['start_ticks'])}
stop=json.loads((r/'controls/STOP.json').read_text()) if (r/'controls/STOP.json').exists() else None
print(json.dumps({'dispatch':d,'queue':q,'scheduler':a,'process':process,'result':result,'report':report,'STOP':stop,'stderr':stderr,'efficacy_read':False}))
'''

def main():
    op,label=sys.argv[1:3]
    if not label.isalnum():raise ValueError('exclusive label')
    if op=='reconcile':z=ssh('RUN='+repr(OLD_RUN)+'\nEXPECTED='+repr('f08e53e73035171340fe2438e3061685a3be6d1f18a8b132540717bd447a60dc')+'\n'+RECONCILE)
    elif op=='stage_submit':
        from .preserve import published
        pub=published();raw=(DOC/'RC1-CONTRACT.json').read_bytes();expected=identity(DOC/'RC1-CONTRACT.json')['sha256']
        write_new(DOC/('SUBMISSION-'+label+'.started.json'),{'contract':expected,'one_gate_only':True})
        z=ssh('RUN='+repr(RUN)+'\nOLD='+repr(OLD_RUN)+'\nV3='+repr(V3_RUN)+'\nEXPECTED='+repr(expected)+'\n'+STAGE,
              json.dumps({'contract':base64.b64encode(raw).decode(),'additions':{n:base64.b64encode(b).decode() for n,b in additions().items()},'publication':pub}).encode())
    elif op=='observe':z=ssh('RUN='+repr(RUN)+'\n'+OBSERVE)
    else:raise ValueError('bounded declared operation')
    write_new(DOC/(op.upper()+'-'+label+'.json'),z);print(json.dumps(z,indent=2))

if __name__=='__main__':main()
