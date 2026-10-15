"""Exclusive artificial test, read-only reconciliation, one validation dispatch."""
import base64,json,sys
from .common import *
from .prepare import additions
from wm_diag0_native_v3.transport import ssh
from wm_diag0_parity_r1.reconcile import PROGRAM as OLD_RECONCILE

RECONCILE=OLD_RECONCILE.replace("ids=list(d['jobs'].values())", "ids=list(d['jobs'].values())+['317172']").replace('charge!=236','charge!=249').replace('STOPPED_DAG_FULLY_TERMINAL_RECONCILED','TERMINAL_AND_SEALS_RECONCILED')

TEST='''
import base64,hashlib,json,os,pathlib,subprocess,sys
data=json.load(sys.stdin);r=pathlib.Path(TEST_ROOT);r.mkdir(exist_ok=False)
for n,b in data['files'].items():
 p=r/n;p.parent.mkdir(parents=True,exist_ok=True);raw=base64.b64decode(b)
 if hashlib.sha256(raw).hexdigest()!=data['identities'][n]['sha256']:raise ValueError('test source identity')
 with p.open('xb') as f:f.write(raw)
 p.chmod(0o444)
env={k:v for k,v in os.environ.items() if not k.startswith(('APPTAINERENV_','SINGULARITYENV_'))}
for k,v in {'PYTHONPATH':str(r)+':'+OLD_SOURCE+':'+DINO_SOURCE,'PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1','CUDA_VISIBLE_DEVICES':'',
 'OMP_NUM_THREADS':'4','OPENBLAS_NUM_THREADS':'4','MKL_NUM_THREADS':'4','NUMEXPR_NUM_THREADS':'4','HOME':'/tmp','XFORMERS_DISABLED':'1'}.items():env['APPTAINERENV_'+k]=v
os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:4])
cmd=['apptainer','exec','--containall','--cleanenv','--no-home','--bind',str(r)+':'+str(r)+':ro','--bind',OLD_SOURCE+':'+OLD_SOURCE+':ro',
 '--bind',DINO_SOURCE+':'+DINO_SOURCE+':ro','--bind',VENV+':'+VENV+':ro',SIF,VENV+'/bin/python','-B','-m','wm_diag0_numerical_v3.tests','reference']
p=subprocess.run(cmd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=60)
if len(p.stdout)+len(p.stderr)>100000:raise ValueError('artificial log bound')
print(json.dumps({'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'research_checkpoints_or_data_loaded':False,'new_allocation':False,'test_source':data['identities']}))
'''

STAGE='''
import base64,hashlib,json,os,pathlib,subprocess,sys
r=pathlib.Path(RUN);old=pathlib.Path(OLD);data=json.load(sys.stdin);raw=base64.b64decode(data['contract']);c=json.loads(raw)
def ident(p):return {'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def write(n,x):
 with (r/'controls'/n).open('x') as f:json.dump(x,f,sort_keys=True)
if hashlib.sha256(raw).hexdigest()!=EXPECTED or not c['numerical_validation_authorized'] or c['gpu_stages_authorized'] or c['recovery']['actual_usage']['predictor_calls']!=15:raise ValueError('validation only')
q=subprocess.check_output(['squeue','-h','-j','317163,317164,317165,317166,317172','-o','%i'],universal_newlines=True,timeout=10)
if q.strip():raise ValueError('old live allocation')
for k,x in c['recovery']['accepted_suppliers'].items():
 if ident(old/'tasks'/k/'controls/ACCEPTED.json')!=x['control']:raise ValueError('accepted control changed')
 manifest=old/'tasks'/k/'output/MEMBERS.json'
 if ident(manifest)!=x['output_seal']:raise ValueError('supplier seal changed')
 for n,row in json.loads(manifest.read_text()).items():
  if ident(manifest.parent/n)!=row:raise ValueError('accepted member changed')
for n,x in c['recovery']['partial'].items():
 if ident(old/'tasks/technical-1/output'/n)!=x:raise ValueError('failed partial changed')
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
  if supplier.is_symlink() or ident(supplier)!=x:raise ValueError('frozen source supplier')
  os.link(str(supplier),str(p))
with (r/'source/VALIDATION-CONTRACT.json').open('xb') as f:f.write(raw)
(r/'source/VALIDATION-CONTRACT.json').chmod(0o444)
for p in sorted((r/'source').rglob('*'),reverse=True):
 if p.is_dir():p.chmod(0o555)
(r/'source').chmod(0o555)
write('PUBLICATION-AND-SSD.json',data['publication'])
script=chr(10).join(['#!/bin/bash','set -eu','umask 077','export PYTHONDONTWRITEBYTECODE=1','export PYTHONPATH='+str(r/'source'),
 'exec python3 -B -m wm_diag0_numerical_v3.supervisor '+RUN+' '+EXPECTED,''])
args=['sbatch','--parsable','--hold','--no-requeue','--job-name=wm-a2-numerical-validation-v3','--partition=a6000','--qos=normal-a6000','--nodelist=gpu09',
 '--nodes=1','--ntasks=1','--cpus-per-task=4','--mem=8192M','--gres=gpu:1','--time=3','--chdir='+str(r/'source'),'--output='+str(r/'logs/validation-%j.log'),'--error='+str(r/'logs/validation-%j.log')]
write('SUBMIT-STARTED.json',{'args':args,'contract_sha256':EXPECTED,'GPU_charged_before':249,'allocation_seconds':180})
p=subprocess.run(args,input=script,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=20)
write('SBATCH-RESPONSE.json',{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
if p.returncode:raise RuntimeError('submission rejected; retain, no blind retry')
jid=p.stdout.strip().split(';')[0]
if not jid.isdigit():raise RuntimeError('ambiguous submission; no retry')
d={'job_id':jid,'contract_sha256':EXPECTED,'phase':'numerical_validation','allocation_seconds':180,'automatic_retries':0,'campaign_resumed':False}
write('DISPATCH.json',d)
p=subprocess.run(['scontrol','release',jid],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=10)
write('RELEASE-RESPONSE.json',{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
if p.returncode:raise RuntimeError('known held allocation; reconcile, no retry')
print(json.dumps(d))
'''

OBSERVE='''
import hashlib,json,pathlib,subprocess
r=pathlib.Path(RUN);d=json.loads((r/'controls/DISPATCH.json').read_text());jid=d['job_id']
if not jid.isdigit():raise ValueError('exact dispatch ID')
q=subprocess.check_output(['squeue','-h','-j',jid,'-o','%i|%T|%M|%N|%R'],universal_newlines=True,timeout=10)
a=subprocess.check_output(['sacct','-X','-n','-P','-j',jid,'--format=JobID,State,ExitCode,ElapsedRaw,AllocCPUS,NodeList'],universal_newlines=True,timeout=15)
t=r/'tasks/numerical-validation';p=t/'controls/RESULT.json';z=json.loads(p.read_text()) if p.exists() else None
report=None
if z is not None and z['status']!='FAILED':
 p=t/'output/VALIDATION.json'
 if {'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}!=z['report_identity']:raise ValueError('authenticated numerical report')
 report=json.loads(p.read_text())
f=t/'logs/worker.log';err=f.read_text(errors='replace')[-12000:] if z is not None and z['status']=='FAILED' and f.exists() else None
stop=json.loads((r/'controls/STOP.json').read_text()) if (r/'controls/STOP.json').exists() else None
print(json.dumps({'dispatch':d,'queue':q,'scheduler':a,'result':z,'report':report,'stderr':err,'STOP':stop,'efficacy_read':False}))
'''

def main():
    operation,label=sys.argv[1:3]
    if not label.isalnum():raise ValueError('exclusive label')
    DOC.mkdir(exist_ok=True)
    if operation=='reconcile':z=ssh('RUN='+repr(OLD_RUN)+'\nEXPECTED='+repr(OLD_CONTRACT)+'\n'+RECONCILE)
    elif operation=='test':
        c=json.loads((ROOT/'docs/world-model-diagnostic-a2-campaign-v4-20261015/campaign/CONTRACT.json').read_text())
        files={n:b for n,b in additions().items() if n.rsplit('/',1)[1] in ('__init__.py','common.py','metrics.py','reference.py','tests.py')}
        payload={'files':{n:base64.b64encode(b).decode() for n,b in files.items()},'identities':{n:{'bytes':len(b),'sha256':__import__('hashlib').sha256(b).hexdigest()} for n,b in files.items()}}
        values={'TEST_ROOT':RUN+'-artificial-'+label,'OLD_SOURCE':OLD_RUN+'/source','DINO_SOURCE':c['dino_source'],'VENV':c['venv'],'SIF':c['sif']}
        z=ssh('\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'+TEST,json.dumps(payload).encode())
    elif operation=='stage_submit':
        from .preserve import published
        pub=published();raw=(DOC/'VALIDATION-CONTRACT.json').read_bytes();expected=identity(DOC/'VALIDATION-CONTRACT.json')['sha256']
        write_new(DOC/('SUBMISSION-'+label+'.started.json'),{'contract':expected,'one_validation_allocation':True})
        z=ssh('RUN='+repr(RUN)+'\nOLD='+repr(OLD_RUN)+'\nEXPECTED='+repr(expected)+'\n'+STAGE,json.dumps({'contract':base64.b64encode(raw).decode(),
            'additions':{n:base64.b64encode(b).decode() for n,b in additions().items()},'publication':pub}).encode())
    elif operation=='observe':z=ssh('RUN='+repr(RUN)+'\n'+OBSERVE)
    else:raise ValueError('bounded declared operation')
    name='RECONCILIATION-'+label+'.json' if operation=='reconcile' else operation.upper()+'-'+label+'.json'
    write_new(DOC/name,z);print(json.dumps(z,indent=2))

if __name__=='__main__':main()
