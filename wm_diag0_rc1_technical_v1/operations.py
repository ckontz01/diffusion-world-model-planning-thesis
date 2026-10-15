"""One three-setting dispatch, authenticated suppliers and node-aware observation."""
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
if hashlib.sha256(raw).hexdigest()!=EXPECTED or not c['rc1_technical']['three_settings_authorized'] or c['gpu_stages_authorized']:raise ValueError('three-setting-only contract')
q=subprocess.check_output(['squeue','-h','-j','317163,317164,317165,317166,317172,317173,317174,317175','-o','%i|%T'],universal_newlines=True,timeout=10)
if q.strip():raise ValueError('old or gate allocation live/ambiguous')
a=subprocess.check_output(['sacct','-X','-n','-P','-j','317174','--format=JobID,State,ExitCode,ElapsedRaw,AllocCPUS,NodeList'],universal_newlines=True,timeout=15)
rows=[x.split('|') for x in a.splitlines() if x.strip()]
if rows!=[['317174','COMPLETED','0:0','19','4','gpu09']]:raise ValueError('exact completed gate accounting')
ha=subprocess.check_output(['sacct','-X','-n','-P','-j','317175','--format=JobID,JobIDRaw,State,ExitCode,ElapsedRaw,AllocCPUS,NodeList'],universal_newlines=True,timeout=15)
hr=[x.split('|') for x in ha.splitlines() if x.strip()]
if len(hr)!=2 or {x[0] for x in hr}!={'317175_1','317175_3'} or any(x[2:]!=['COMPLETED','0:0','22','4','gpu09'] for x in hr):raise ValueError('both exact terminal head charges')
heads=pathlib.Path(c['rc1_technical']['heads_run'])
if ident(heads/'source/HEADS-CONTRACT.json')!=c['rc1_technical']['heads_contract'] or (heads/'controls/STOP.json').exists():raise ValueError('accepted head closure')
for i,x in c['rc1_technical']['head_suppliers'].items():
 ht=heads/'tasks'/('readout-'+i)
 if ident(ht/'controls/ACCEPTED.json')!=x['acceptance_identity'] or ident(ht/'output/MEMBERS.json')!=x['output_seal']:raise ValueError('new accepted head identity')
 if not json.loads((ht/'controls/ACCEPTED.json').read_text())['accepted']:raise ValueError('new head not accepted')
 for n,z in json.loads((ht/'output/MEMBERS.json').read_text()).items():
  if ident(ht/'output'/n)!=z:raise ValueError('new head artifact changed')
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
base=pathlib.Path(RUN).parent
logical=sum(p.stat().st_size for p in base.rglob('*') if p.is_file())
live=logical+2100000000+3139002368+144694193+630000000+3840000000+127000000+60000000+20000000+300000000
archive=live+500000000;inclusive=live+28000000000+2874852312
if live>13500000000 or archive>14000000000 or inclusive>44000000000:raise ValueError('fresh all-lineage full-future storage bound')
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
  supplier=heads/'source'/n
  if supplier.is_symlink() or ident(supplier)!=x:raise ValueError('executed closure supplier')
  os.link(str(supplier),str(p))
with (r/'source/TECHNICAL-CONTRACT.json').open('xb') as f:f.write(raw)
(r/'source/TECHNICAL-CONTRACT.json').chmod(0o444)
os.link(str(old/'controls/RUNTIME-MANIFEST.json'),str(r/'controls/RUNTIME-MANIFEST.json'))
for p in sorted((r/'source').rglob('*'),reverse=True):
 if p.is_dir():p.chmod(0o555)
(r/'source').chmod(0o555)
write('PUBLICATION-AND-SSD.json',data['publication']);write('PRO-GATE-DISPOSITION.json',data['review']);write('FRESH-STORAGE.json',{'logical_study_bytes':logical,'full_future_live':live,'full_future_archive':archive,'full_future_inclusive':inclusive,'no_compression_savings':True});write('GATE-TERMINAL-RECONCILIATION.json',{'scheduler':a,'GPU_all_attempts':331,'CPU_all_attempts':1436,'full_future_GPU':457531,'full_future_CPU':6836})
script=chr(10).join(['#!/bin/bash','set -eu','umask 077','export PYTHONDONTWRITEBYTECODE=1','export PYTHONPATH='+str(r/'source'),
 'exec python3 -B -m wm_diag0_rc1_technical_v1.supervisor '+RUN+' '+EXPECTED,''])
args=['sbatch','--parsable','--hold','--no-requeue','--job-name=wm-a2-rc1-technical-v1','--array=1-3%1','--partition=a6000','--qos=normal-a6000','--nodelist=gpu09',
 '--nodes=1','--ntasks=1','--cpus-per-task=4','--mem=8192M','--gres=gpu:1','--time=60','--chdir='+str(r/'source'),
 '--output='+str(r/'logs/technical-%A_%a.log'),'--error='+str(r/'logs/technical-%A_%a.log')]
write('SUBMIT-STARTED.json',{'args':args,'contract_sha256':EXPECTED,'three_settings':[1,2,3],'GPU_before':331,'full_future_GPU':457531,'retries':0})
p=subprocess.run(args,input=script,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=20)
write('SBATCH-RESPONSE.json',{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
if p.returncode:raise RuntimeError('submission rejected; no blind retry')
jid=p.stdout.strip().split(';')[0]
if not jid.isdigit():raise RuntimeError('ambiguous dispatch; reconcile no retry')
d={'array_job_id':jid,'settings':[1,2,3],'contract_sha256':EXPECTED,'allocation_seconds_each':3600,'automatic_retries':0,'campaign_resumed':False}
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
for i in (1,2,3):
 t=r/'tasks'/('technical-'+str(i));z={}
 for n in ('STARTED','RESULT','WORKER-SUCCESS','ACCEPTED'):
  p=t/'controls'/(n+'.json')
  if p.exists():z[n]=json.loads(p.read_text())
 if 'STARTED' in z:
  s=z['STARTED'];z['process']={'node':s['node'],'PID':s['PID'],'start_ticks':s['start_ticks'],'scope':'compute-node record; not login /proc'}
  if 'RESULT' not in z:
   code="import json,pathlib;p=pathlib.Path('/proc')/"+repr(str(s['PID']))+"/'stat';print(json.dumps({'PID_exists':p.exists(),'start_ticks_match':p.exists() and p.read_text().rsplit(')',1)[1].split()[19]=="+repr(str(s['start_ticks']))+"}))"
   import shlex
   try:
    p=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=5',s['node'],'python3 -B -c '+shlex.quote(code)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=8)
    z['process']['verification_returncode']=p.returncode
    if p.returncode==0:z['process'].update(json.loads(p.stdout))
    else:z['process']['verification_unavailable_not_cluster_failure']=True
   except subprocess.TimeoutExpired:z['process']['verification_unavailable_not_cluster_failure']=True
  else:z['process']['allocation_terminal_no_live_process_expected']=True
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
        pub=published();raw=(DOC/'TECHNICAL-CONTRACT.json').read_bytes();expected=identity(DOC/'TECHNICAL-CONTRACT.json')['sha256']
        reviewpath=ROOT/'docs/world-model-diagnostic-rc1-heads-v1-20261016/PRO-GATE-DISPOSITION-001.json'
        review=json.loads(reviewpath.read_text())
        if identity(reviewpath)!=json.loads(raw)['rc1_technical']['scientific_gate_disposition']:raise ValueError('review identity')
        write_new(DOC/('SUBMISSION-'+label+'.started.json'),{'contract_sha256':expected,'three_settings_only':True,'no_retry':True})
        z=ssh('RUN='+repr(RUN)+'\nGATE='+repr(GATE_RUN)+'\nEXPECTED='+repr(expected)+'\n'+STAGE,
            json.dumps({'contract':base64.b64encode(raw).decode(),'additions':{n:base64.b64encode(b).decode() for n,b in additions().items()},'publication':pub,'review':review}).encode())
    elif op=='observe':z=ssh('RUN='+repr(RUN)+'\n'+OBSERVE)
    else:raise ValueError('one-shot declared operation')
    write_new(DOC/(op.upper()+'-'+label+'.json'),z);print(json.dumps(z,indent=2))

if __name__=='__main__':main()


