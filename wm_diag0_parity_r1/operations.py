"""One exact encoding-only allocation, plus bounded technical readback."""
import base64,json,sys
from .common import DOC,RUN,OLD_RUN,identity,write_new
from .prepare import additions
from .preserve import published
from wm_diag0_native_v3.transport import ssh

STAGE='''
import base64,hashlib,json,os,pathlib,subprocess,sys,time
r=pathlib.Path(RUN);old=pathlib.Path(OLD);data=json.load(sys.stdin);raw=base64.b64decode(data['contract']);c=json.loads(raw)
def identity(p):return {'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def write(n,x):
 with (r/'controls'/n).open('x') as f:json.dump(x,f,sort_keys=True)
if hashlib.sha256(raw).hexdigest()!=EXPECTED or c['recovery']['predictor_calls']!=0 or c['gpu_stages_authorized']:raise ValueError('encoding-only contract')
q=subprocess.check_output(['squeue','-h','-j','317163,317164,317165,317166','-o','%i'],universal_newlines=True,timeout=10)
if q.strip():raise ValueError('old live allocation')
for key,x in c['recovery']['accepted_suppliers'].items():
 if identity(old/'tasks'/key/'controls/ACCEPTED.json')!=x['control']:raise ValueError('accepted supplier changed')
for n,x in c['recovery']['partial'].items():
 if identity(old/'tasks/technical-1/output'/n)!=x:raise ValueError('retained partial changed')
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
  supplier=old/'source'/n
  if supplier.is_symlink() or identity(supplier)!=x:raise ValueError('frozen source supplier')
  os.link(str(supplier),str(p))
with (r/'source/PROBE-CONTRACT.json').open('xb') as f:f.write(raw)
(r/'source/PROBE-CONTRACT.json').chmod(0o444)
for p in sorted((r/'source').rglob('*'),reverse=True):
 if p.is_dir():p.chmod(0o555)
(r/'source').chmod(0o555)
write('PUBLICATION-AND-SSD.json',data['publication'])
script=chr(10).join(['#!/bin/bash','set -eu','umask 077','export PYTHONDONTWRITEBYTECODE=1','export PYTHONPATH='+str(r/'source'),
 'exec python3 -B -m wm_diag0_parity_r1.supervisor '+RUN+' '+EXPECTED,''])
args=['sbatch','--parsable','--hold','--no-requeue','--job-name=wm-a2-encoding-diagnosis-r1','--partition=a6000','--qos=normal-a6000','--nodelist=gpu09',
 '--nodes=1','--ntasks=1','--cpus-per-task=4','--mem=8192M','--gres=gpu:1','--time=3','--chdir='+str(r/'source'),'--output='+str(r/'logs/probe-%j.log'),'--error='+str(r/'logs/probe-%j.log')]
write('SUBMIT-STARTED.json',{'args':args,'contract_sha256':EXPECTED,'GPU_charged_before':236,'allocation_seconds':180})
p=subprocess.run(args,input=script,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=20)
write('SBATCH-RESPONSE.json',{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
if p.returncode:raise RuntimeError('submission rejected; retain evidence, never blind retry')
jid=p.stdout.strip().split(';')[0]
if not jid.isdigit():raise RuntimeError('ambiguous submission; no retry')
dispatch={'job_id':jid,'contract_sha256':EXPECTED,'phase':'encoding_only','allocation_seconds':180,'automatic_retries':0,'campaign_resumed':False}
write('DISPATCH.json',dispatch)
p=subprocess.run(['scontrol','release',jid],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=10)
write('RELEASE-RESPONSE.json',{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
if p.returncode:raise RuntimeError('known held allocation; reconcile, no retry')
print(json.dumps(dispatch))
'''

OBSERVE='''
import json,pathlib,subprocess
r=pathlib.Path(RUN);d=json.loads((r/'controls/DISPATCH.json').read_text());jid=d['job_id']
if not jid.isdigit():raise ValueError('exact ID')
q=subprocess.check_output(['squeue','-h','-j',jid,'-o','%i|%T|%M|%N|%R'],universal_newlines=True,timeout=10)
a=subprocess.check_output(['sacct','-X','-n','-P','-j',jid,'--format=JobID,State,ExitCode,ElapsedRaw,AllocCPUS,NodeList'],universal_newlines=True,timeout=15)
p=r/'tasks/encoding-only/controls/RESULT.json';z=json.loads(p.read_text()) if p.exists() else None
f=r/'tasks/encoding-only/logs/worker.log';error=f.read_text(errors='replace')[-10000:] if z is not None and z['status']=='FAILED' and f.exists() else None
print(json.dumps({'dispatch':d,'queue':q,'scheduler':a,'result':z,'stderr':error,'scientific_results_read':False}))
'''

def main():
    operation,label=sys.argv[1:3]
    if not label.isalnum():raise ValueError('exclusive label')
    if operation=='stage_submit':
        pub=published();raw=(DOC/'PROBE-CONTRACT.json').read_bytes();expected=identity(DOC/'PROBE-CONTRACT.json')['sha256']
        write_new(DOC/('SUBMISSION-'+label+'.started.json'),{'contract':expected,'one_encoding_only_job':True})
        payload=json.dumps({'contract':base64.b64encode(raw).decode(),'additions':{n:base64.b64encode(b).decode() for n,b in additions().items()},'publication':pub}).encode()
        z=ssh('RUN='+repr(RUN)+'\nOLD='+repr(OLD_RUN)+'\nEXPECTED='+repr(expected)+'\n'+STAGE,payload=payload)
    elif operation=='observe':z=ssh('RUN='+repr(RUN)+'\n'+OBSERVE)
    else:raise ValueError('one-shot stage/submit or read-only observation')
    write_new(DOC/(operation.upper()+'-'+label+'.json'),z);print(json.dumps(z,indent=2))

if __name__=='__main__':main()
