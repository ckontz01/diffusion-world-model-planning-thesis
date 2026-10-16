"""Exact58 held dispatch only after all immutable publication/resource gates."""
import base64,json,time
from .common import *
from .transport import call
from .inspect_v2 import program

STAGE=r'''
data=json.load(sys.stdin);root=pathlib.Path(RUN);raw=base64.b64decode(data['contract']);new=json.loads(raw)
if root.exists():raise FileExistsError('new recovery root already exists; no duplicate staging/submission')
if hashlib.sha256(raw).hexdigest()!=EXPECTED or new['run']!=RUN or new['rc1_recovery']['indices']!=list(range(66,124)):raise ValueError('reviewed exact recovery')
if new['rc1_recovery']['old_failure_controls']!=failure or new['rc1_recovery']['accepted_control_commitment']!=z['accepted_control_commitment']:raise ValueError('old failure and accepted controls unchanged at dispatch')
if z['GPU_full_future']!=254702 or new['rc1_recovery']['planned_total_attempts']!=139:raise ValueError('finite approved attempts/time')
root.mkdir(exist_ok=False)
for n in ('source','controls','tasks','logs'):(root/n).mkdir()
def write(name,obj):
 with (root/'controls'/name).open('x') as f:json.dump(obj,f,sort_keys=True)
for n,x in new['staged_members'].items():
 p=root/'source'/n;p.parent.mkdir(parents=True,exist_ok=True)
 if n.startswith('wm_diag0_rc1_recovery_r1/'):
  b=base64.b64decode(data['additions'][n])
  if {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}!=x:raise ValueError('new published recovery source bytes')
  with p.open('xb') as f:f.write(b)
  p.chmod(0o444)
 else:
  source=old/'source'/n
  if ident(source)!=x:raise ValueError('exact old frozen source retained')
  os.link(str(source),str(p))
with (root/'source/GRID-CONTRACT.json').open('xb') as f:f.write(raw)
(root/'source/GRID-CONTRACT.json').chmod(0o444)
os.link(str(manifest),str(root/'controls/RUNTIME-MANIFEST.json'))
for p in sorted((root/'source').rglob('*'),reverse=True):
 if p.is_dir():p.chmod(0o555)
(root/'source').chmod(0o555)
write('ORIGINAL-RECONCILIATION.json',z);write('PUBLICATION-AND-SSD.json',data['publication']);write('LATEST-HUMAN-AUTHORITY.json',new['rc1_recovery']['authority'])
script='\n'.join(['#!/bin/bash','set -eu','umask 077','export PYTHONDONTWRITEBYTECODE=1','export PYTHONPATH='+str(root/'source'),'exec python3 -B -m wm_diag0_rc1_recovery_r1.supervisor '+RUN+' '+EXPECTED,''])
args=['sbatch','--parsable','--hold','--no-requeue','--job-name=wm-a2-rc1-recovery-r1','--array=66-123%1','--partition=a6000','--qos=normal-a6000','--nodelist=gpu09','--nodes=1','--ntasks=1','--cpus-per-task=4','--mem=8192M','--gres=gpu:1','--time=60','--chdir='+str(root/'source'),'--output='+str(root/'logs/grid-%A_%a.log'),'--error='+str(root/'logs/grid-%A_%a.log')]
write('SUBMIT-STARTED.json',{'args':args,'contract_sha256':EXPECTED,'script_sha256':hashlib.sha256(script.encode()).hexdigest(),'GPU_terminal_before':45902,'attempts_before':81,'new_attempts':58,'planned_total_attempts':139,'automatic_retry':False})
p=subprocess.run(args,input=script,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=20)
write('SBATCH-RESPONSE.json',{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
if p.returncode:raise RuntimeError('submission failed; preserve/reconcile no retry')
jid=p.stdout.strip().split(';')[0]
if not jid.isdigit():raise RuntimeError('ambiguous submission response; no retry')
d={'array_job_id':jid,'indices':58,'original_indices':list(range(66,124)),'contract_sha256':EXPECTED,'allocation_seconds_each':3600,'automatic_retries':0,'GPU_full_future':254702,'planned_total_attempts':139,'accepted_original_indices_never_rerun':list(range(66))}
write('DISPATCH.json',d)
p=subprocess.run(['scontrol','release',jid],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=10)
write('RELEASE-RESPONSE.json',{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
if p.returncode:raise RuntimeError('known held allocation; reconcile not resubmit')
print(json.dumps({'status':'EXACT58_RECOVERY_DISPATCHED','dispatch':d,'source_commit':data['publication']['source_commit'],'original_failed_and_successful_work_preserved':True}))
'''

def main():
    from .publication import git,BRANCH
    pub=json.loads((DOC/'SSD-VERIFIED-001.json').read_text())
    if pub['status']!='RECOVERY_SOURCE_WHOLE_EVERY_MEMBER_VERIFIED' or git('ls-remote','origin','refs/heads/'+BRANCH).decode().split()[0]!=pub['source_commit']:raise ValueError('whole/everymember publication/fullremote gate')
    if identity(pub['archive'])!=pub['whole'] or identity(DOC/'GRID-CONTRACT.json')!=pub['contract']:raise ValueError('exact preserved package/contract')
    for n,x in pub['working_source_members'].items():
        if identity(ROOT/n)!=x:raise ValueError('published source changed')
    raw=(DOC/'GRID-CONTRACT.json').read_bytes();c=json.loads(raw);closed_indices(c)
    if not Path('D:/WSL/Thesis-Ubuntu/ext4.vhdx').is_file():raise RuntimeError('existing configured WSL path unavailable')
    code=program();tail="print(json.dumps(z,sort_keys=True,separators=(',',':')))"
    if code.count(tail)!=1:raise ValueError('one exact pre-dispatch reconciliation program')
    code=code.replace(tail,STAGE)
    code='RUN='+repr(RUN)+'\nEXPECTED='+repr(pub['contract']['sha256'])+'\n'+code
    data={'contract':base64.b64encode(raw).decode(),'publication':pub,'additions':{n:base64.b64encode((ROOT/n).read_bytes()).decode() for n in c['staged_members'] if n.startswith('wm_diag0_rc1_recovery_r1/')}}
    z=call('STAGE001',code,data,seconds=220);print(json.dumps(z))

if __name__=='__main__':main()
