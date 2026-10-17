"""One exclusive held/released site CPU job after pre-run publication/SSD gate."""
import ast,base64,json
from .common import DOC,REMOTE,identity
from .freeze import payload
from .transport import call

CODE=r'''
import base64,hashlib,json,os,shlex,subprocess,sys
from pathlib import Path
d=json.load(sys.stdin);root=Path(d['root']);source=root/'source';pub=d['publication']
if str(root)!='/lustreFS/data/superworld/ckontzias/thesis/experiments/wm-diag1-saved-20261017' or root.exists():raise FileExistsError('exact new saved-data root absent; reconcile, never duplicate job')
if pub['source_commit']!=pub['full_remote_hash']:raise ValueError('actual pre-run fullremote source publication')
raw=base64.b64decode(d['files']['FREEZE.json'])
if {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}!=pub['freeze']:raise ValueError('externally bound pre-run freeze')
freeze=json.loads(raw)
if (freeze['saved_data_jobs'],freeze['allocation_wall_seconds'],freeze['CPUs'],freeze['RAM_bytes'],freeze['GPU_requested'])!=(1,1800,4,8589934592,0):raise PermissionError('one unchanged saved-only CPU job')
root.mkdir();source.mkdir();(root/'controls').mkdir();(root/'analysis/tmp').mkdir(parents=True)
total=0
for name,encoded in d['files'].items():
 if name.startswith('/') or '..' in name.split('/') or '\\' in name:raise ValueError('ordinary exact source member')
 b=base64.b64decode(encoded);want=pub['freeze'] if name=='FREEZE.json' else freeze['members'][name]
 if {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}!=want:raise ValueError('published exact source bytes')
 total+=len(b)
 if total>8000000:raise ValueError('small new source/spec/input copy')
 p=source/name;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as out:out.write(b)
 p.chmod(0o444)
for p in sorted(source.rglob('*'),reverse=True):
 if p.is_dir():p.chmod(0o555)
source.chmod(0o555)
def write(name,v):
 b=(json.dumps(v,sort_keys=True,separators=(',',':'))+'\n').encode()
 if len(b)>300000:raise ValueError('bounded stage control')
 with (root/'controls'/name).open('xb') as out:out.write(b);out.flush();os.fsync(out.fileno())
script='#!/bin/bash\nset -euo pipefail\numask 077\nexport PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 CUDA_VISIBLE_DEVICES="" NVIDIA_VISIBLE_DEVICES=void\nexport OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 NUMEXPR_NUM_THREADS=4\ncd '+shlex.quote(str(source))+'\nexec python3 -B -m wm_diag1_saved_v1.driver '+shlex.quote(str(root))+' '+shlex.quote(json.dumps(pub['freeze'],separators=(',',':')))+'\n'
args=['sbatch','--parsable','--hold','--no-requeue','--account=superworld','--job-name=wm-diag1-saved','--partition=defq','--qos=normal','--nodes=1','--ntasks=1','--cpus-per-task=4','--mem=8192M','--time=30','--chdir='+str(source),'--output='+str(root/'slurm.log'),'--error='+str(root/'slurm.log')]
write('REQUEST.json',{'script_sha256':hashlib.sha256(script.encode()).hexdigest(),'freeze':pub['freeze'],'CPUs':4,'RAM_bytes':8589934592,'wall_seconds':1800,'GPU_requested':0,'automatic_retry':False})
p=subprocess.run(args,input=script,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=15)
write('SUBMISSION.json',{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
if p.returncode:raise RuntimeError('submission diagnostic retained; no retry')
job=p.stdout.strip().split(';')[0]
if not job.isdigit():raise ValueError('ambiguous job ID; never resubmit')
actual=subprocess.check_output(['scontrol','show','job','-o',job],universal_newlines=True,timeout=8);fields=dict(x.split('=',1) for x in actual.split() if '=' in x)
if fields.get('JobState')!='PENDING' or fields.get('NumCPUs')!='4' or fields.get('NumTasks')!='1' or fields.get('TimeLimit')!='00:30:00' or fields.get('Partition')!='defq' or fields.get('MinMemoryNode') not in ('8G','8192M') or 'gpu' in fields.get('ReqTRES','').lower():raise PermissionError('held exact CPU-only allocation mismatch; preserve held job')
dispatch={'job_id':job,'freeze':pub['freeze'],'source_commit':pub['source_commit'],'full_remote_hash':pub['full_remote_hash'],'pre_run_source_SSD':pub['whole'],'held_scheduler_record':actual,'new_logical_source_bytes':total,'automatic_retry':False}
write('DISPATCH.json',dispatch)
release=subprocess.run(['scontrol','release',job],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=8)
write('RELEASE.json',{'job_id':job,'returncode':release.returncode,'stdout':release.stdout,'stderr':release.stderr})
if release.returncode:raise RuntimeError('held release ambiguous; never resubmit')
print(json.dumps({'status':'ONE_SAVED_DATA_ONLY_CPU_JOB_DISPATCHED_ONCE','job_id':job,'freeze':pub['freeze'],'source_commit':pub['source_commit'],'new_logical_source_bytes':total,'GPUs':0}))
'''

def main():
    from wm_diag0_preflight_v1.preserve import volume
    pub=json.loads((DOC/'SOURCE-PUBLISHED.json').read_text());volume()
    if identity(pub['archive'])!=pub['whole'] or pub['status']!='FROZEN_ANALYSIS_PUBLISHED_FULL_REMOTE_SOURCE_SSD_WHOLE_EVERY_MEMBER_VERIFIED_BEFORE_FIRST_DERIVED_PASS':raise PermissionError('real pre-run source SSD gate')
    files=payload();ast.parse(CODE,feature_version=(3,6))
    value=call('STAGE001',CODE,{'root':REMOTE,'publication':{k:pub[k] for k in ('source_commit','full_remote_hash','freeze','whole')},'files':{k:base64.b64encode(v).decode() for k,v in files.items()}},seconds=65)
    print(json.dumps(value))

if __name__=='__main__':main()
