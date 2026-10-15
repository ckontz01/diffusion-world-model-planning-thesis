"""One serial two-head dispatch and exact scheduler/technical observations."""
import base64,json,sys
from .common import *
from .prepare import additions
from wm_diag0_native_v3.transport import ssh

STAGE=r'''
import base64,hashlib,json,os,pathlib,subprocess,sys
r=pathlib.Path(RUN);gate=pathlib.Path(GATE);data=json.load(sys.stdin);raw=base64.b64decode(data['contract']);c=json.loads(raw)
def ident(p):
 h=hashlib.sha256();size=0
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b);size+=len(b)
 return {'bytes':size,'sha256':h.hexdigest()}
def write(n,x):
 with (r/'controls'/n).open('x') as f:json.dump(x,f,sort_keys=True)
if hashlib.sha256(raw).hexdigest()!=EXPECTED or not c['rc1_heads']['exact_two_fits_authorized'] or c['gpu_stages_authorized']:raise ValueError('two-head-only contract')
q=subprocess.check_output(['squeue','-h','-j','317163,317164,317165,317166,317172,317173,317174','-o','%i|%T'],universal_newlines=True,timeout=10)
if q.strip():raise ValueError('old or gate allocation live/ambiguous')
a=subprocess.check_output(['sacct','-X','-n','-P','-j','317174','--format=JobID,State,ExitCode,ElapsedRaw,AllocCPUS,NodeList'],universal_newlines=True,timeout=15)
rows=[x.split('|') for x in a.splitlines() if x.strip()]
if rows!=[['317174','COMPLETED','0:0','19','4','gpu09']]:raise ValueError('exact completed gate accounting')
if (gate/'controls/STOP.json').exists():raise ValueError('gate stopped')
t=gate/'tasks/rc1-gate'
if ident(gate/'source/RC1-CONTRACT.json')!=c['rc1_heads']['gate_contract'] or ident(t/'output/RC1-GATE.json')!=c['rc1_heads']['gate_report'] or ident(t/'output/MEMBERS.json')!=c['rc1_heads']['gate_seal']:raise ValueError('gate evidence changed')
for n,x in json.loads((t/'output/MEMBERS.json').read_text()).items():
 if ident(t/'output'/n)!=x:raise ValueError('gate member changed')
if not json.loads((t/'controls/RESULT.json').read_text())['all_RC1_checks_passed']:raise ValueError('real gate not accepted')
old=pathlib.Path(c['recovery']['old_run'])
for k,x in c['recovery']['accepted_suppliers'].items():
 if ident(old/'tasks'/k/'controls/ACCEPTED.json')!=x['control'] or ident(old/'tasks'/k/'output/MEMBERS.json')!=x['output_seal']:raise ValueError('old accepted supplier identity')
 for n,z in json.loads((old/'tasks'/k/'output/MEMBERS.json').read_text()).items():
  if ident(old/'tasks'/k/'output'/n)!=z:raise ValueError('old accepted artifact changed')
for n,x in c['recovery']['partial'].items():
 if ident(old/'tasks/technical-1/output'/n)!=x:raise ValueError('failed bank evidence changed')
if ident(old/'controls/RUNTIME-MANIFEST.json')!=c['runtime_manifest']:raise ValueError('runtime authority changed')
r.mkdir(exist_ok=False)
for n in ('source','controls','tasks','logs'):(r/n).mkdir()
for n,x in c['staged_members'].items():
 p=r/'source'/n;p.parent.mkdir(parents=True,exist_ok=True)
 if n in data['additions']:
  b=base64.b64decode(data['additions'][n])
  if {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}!=x:raise ValueError('new source bytes')
  with p.open('xb') as f:f.write(b)
  p.chmod(0o444)
 else:
  supplier=gate/'source'/n
  if supplier.is_symlink() or ident(supplier)!=x:raise ValueError('executed closure supplier')
  os.link(str(supplier),str(p))
with (r/'source/HEADS-CONTRACT.json').open('xb') as f:f.write(raw)
(r/'source/HEADS-CONTRACT.json').chmod(0o444)
os.link(str(old/'controls/RUNTIME-MANIFEST.json'),str(r/'controls/RUNTIME-MANIFEST.json'))
for p in sorted((r/'source').rglob('*'),reverse=True):
 if p.is_dir():p.chmod(0o555)
(r/'source').chmod(0o555)
write('PUBLICATION-AND-SSD.json',data['publication']);write('PRO-GATE-DISPOSITION.json',data['review']);write('GATE-TERMINAL-RECONCILIATION.json',{'scheduler':a,'GPU_all_attempts':287,'CPU_all_attempts':1436,'full_future_GPU':461087,'full_future_CPU':6836})
script=chr(10).join(['#!/bin/bash','set -eu','umask 077','export PYTHONDONTWRITEBYTECODE=1','export PYTHONPATH='+str(r/'source'),
 'exec python3 -B -m wm_diag0_rc1_heads_v1.supervisor '+RUN+' '+EXPECTED,''])
args=['sbatch','--parsable','--hold','--no-requeue','--job-name=wm-a2-rc1-heads-v1','--array=1,3%1','--partition=a6000','--qos=normal-a6000','--nodelist=gpu09',
 '--nodes=1','--ntasks=1','--cpus-per-task=4','--mem=8192M','--gres=gpu:1','--time=30','--chdir='+str(r/'source'),
 '--output='+str(r/'logs/heads-%A_%a.log'),'--error='+str(r/'logs/heads-%A_%a.log')]
write('SUBMIT-STARTED.json',{'args':args,'contract_sha256':EXPECTED,'two_settings':[1,3],'GPU_before':287,'full_future_GPU':461087,'retries':0})
p=subprocess.run(args,input=script,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=20)
write('SBATCH-RESPONSE.json',{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
if p.returncode:raise RuntimeError('submission rejected; no blind retry')
jid=p.stdout.strip().split(';')[0]
if not jid.isdigit():raise RuntimeError('ambiguous dispatch; reconcile no retry')
d={'array_job_id':jid,'settings':[1,3],'contract_sha256':EXPECTED,'allocation_seconds_each':1800,'automatic_retries':0,'campaign_resumed':False}
write('DISPATCH.json',d)
p=subprocess.run(['scontrol','release',jid],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=10)
write('RELEASE-RESPONSE.json',{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
if p.returncode:raise RuntimeError('known held dispatch; reconcile no retry')
print(json.dumps(d))
'''

OBSERVE=r'''
import hashlib,json,pathlib,subprocess
r=pathlib.Path(RUN);d=json.loads((r/'controls/DISPATCH.json').read_text());jid=d['array_job_id']
if not jid.isdigit():raise ValueError('exact dispatch')
q=subprocess.check_output(['squeue','-h','-j',jid,'-o','%i|%T|%M|%N|%R'],universal_newlines=True,timeout=10)
a=subprocess.check_output(['sacct','-X','-n','-P','-j',jid,'--format=JobID,JobIDRaw,State,ExitCode,ElapsedRaw,AllocCPUS,NodeList'],universal_newlines=True,timeout=15)
tasks={}
for i in (1,3):
 t=r/'tasks'/('readout-'+str(i));z={}
 for n in ('STARTED','RESULT','WORKER-SUCCESS','ACCEPTED'):
  p=t/'controls'/(n+'.json')
  if p.exists():z[n]=json.loads(p.read_text())
 if 'STARTED' in z:
  s=z['STARTED'];p=pathlib.Path('/proc')/str(s['PID'])/'stat'
  z['process']={'PID_exists':p.exists(),'start_ticks_match':p.exists() and p.read_text().rsplit(')',1)[1].split()[19]==str(s['start_ticks'])}
 if 'ACCEPTED' in z:
  p=t/'output/MEMBERS.json';s=z['ACCEPTED']['output_seal']
  if {'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}!=s:raise ValueError('accepted output seal')
 if 'RESULT' in z and z['RESULT']['status']=='FAILED':
  p=t/'logs/worker.log';z['stderr']=p.read_text(errors='replace')[-16000:] if p.exists() else ''
 tasks[str(i)]=z
stop=json.loads((r/'controls/STOP.json').read_text()) if (r/'controls/STOP.json').exists() else None
print(json.dumps({'dispatch':d,'queue':q,'scheduler':a,'tasks':tasks,'STOP':stop,'quality_or_predictions_read':False}))
'''

def main():
    op,label=sys.argv[1:3]
    if not label.isalnum():raise ValueError('exclusive label')
    if op=='stage_submit':
        from .preserve import published
        pub=published();raw=(DOC/'HEADS-CONTRACT.json').read_bytes();expected=identity(DOC/'HEADS-CONTRACT.json')['sha256']
        review=json.loads((DOC/'PRO-GATE-DISPOSITION-001.json').read_text())
        if identity(DOC/'PRO-GATE-DISPOSITION-001.json')!=json.loads(raw)['rc1_heads']['scientific_disposition']:raise ValueError('review identity')
        write_new(DOC/('SUBMISSION-'+label+'.started.json'),{'contract_sha256':expected,'two_fits_only':True,'no_retry':True})
        z=ssh('RUN='+repr(RUN)+'\nGATE='+repr(GATE_RUN)+'\nEXPECTED='+repr(expected)+'\n'+STAGE,
            json.dumps({'contract':base64.b64encode(raw).decode(),'additions':{n:base64.b64encode(b).decode() for n,b in additions().items()},'publication':pub,'review':review}).encode())
    elif op=='observe':z=ssh('RUN='+repr(RUN)+'\n'+OBSERVE)
    else:raise ValueError('one-shot declared operation')
    write_new(DOC/(op.upper()+'-'+label+'.json'),z);print(json.dumps(z,indent=2))

if __name__=='__main__':main()
