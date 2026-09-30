"""Finite serial timing dispatch. Default prints plan; disabled approval blocks submit."""
import argparse,json,subprocess,time
from pathlib import Path
from dtv_efficiency.profile import DOC,gate,sha

def footprint(run,c):
    total=sum(p.stat().st_size for p in run.rglob('*') if p.is_file())
    package=json.loads((DOC/'PACKAGE-MANIFEST.json').read_text())
    if total+sum(r['bytes'] for r in package['files'])>c['live_bytes_cap']:raise RuntimeError('live footprint ceiling; preserve without resubmission')
    for job in c['jobs']:
        logs=sum(p.stat().st_size for p in (run/(job['id']+'.out'),run/(job['id']+'.err')) if p.exists())
        if logs>2000000:raise RuntimeError('worker log reservation exceeded')
        root=run/job['id']
        if root.exists() and sum(p.stat().st_size for p in root.rglob('*') if p.is_file())>job['output_limit_bytes']:raise RuntimeError('worker artifact reservation exceeded')
    return total

def plan(c,package_root,approval,run):
    env='/lustreFS/data/superworld/ckontzias/thesis/envs/hi-lewm-artifact-py311-cu121-swm006'
    image='/lustreFS/data/superworld/ckontzias/thesis/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif'
    if len(c['jobs'])!=9 or sum(j['wall_limit_seconds'] for j in c['jobs'])>7200:raise RuntimeError('grid/reservation mismatch')
    return [dict(id=j['id'],reservation_seconds=j['wall_limit_seconds'],command=['sbatch','--parsable','--job-name=dtveff0-'+j['id'],'--account=superworld','--partition=a6000','--qos=normal-a6000','--nodelist=gpu09','--gres=gpu:1','--cpus-per-task=4','--mem=8G','--time=00:13:20','--no-requeue','--output='+str(run/(j['id']+'.out')),'--error='+str(run/(j['id']+'.err')),'--wrap='+'apptainer exec --nv --cleanenv --bind /lustreFS/data/superworld/ckontzias/thesis:/lustreFS/data/superworld/ckontzias/thesis '+image+' env OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH='+str(package_root)+' CUBLAS_WORKSPACE_CONFIG=:4096:8 SLURM_JOB_ID=$SLURM_JOB_ID SLURM_JOB_NAME=$SLURM_JOB_NAME SLURMD_NODENAME=$SLURMD_NODENAME '+env+'/bin/python -m dtv_efficiency.profile --bindings '+str(package_root/'docs/dtv-efficiency-20260930/BINDINGS.json')+' --approval '+str(approval)+' --job '+j['id']+' --output '+str(run/j['id'])]) for j in c['jobs']]

def main():
    a=argparse.ArgumentParser();a.add_argument('--submit',action='store_true');a.add_argument('--run',type=Path,required=True);a.add_argument('--approval',type=Path,default=DOC/'EXECUTION-APPROVAL.json');args=a.parse_args()
    c=json.loads((DOC/'BINDINGS.json').read_text());jobs=plan(c,DOC.parents[1],args.approval,args.run)
    if not args.submit:print(json.dumps(dict(execute=False,full_future_gpu_reservation_seconds=7200,jobs=jobs),indent=2));return
    gate(DOC/'BINDINGS.json',json.loads(args.approval.read_text()))
    if not str(args.run).startswith('/lustreFS/data/superworld/ckontzias/thesis/experiments/dtv-efficiency-20260930/run-') or args.run.exists():raise RuntimeError('exclusive study namespace required')
    args.run.mkdir(parents=True);charged=0;ledger=args.run/'DISPATCH.jsonl'
    def append(value):
        if ledger.exists() and ledger.stat().st_size>1000000:raise RuntimeError('control ledger reservation exhausted; retain exact records')
        with ledger.open('a') as f:f.write(json.dumps(value)+'\n');f.flush()
    for index,job in enumerate(jobs):
        if charged+sum(j['reservation_seconds'] for j in jobs[index:])>7200:raise RuntimeError('full remaining reservation exhausted')
        append(dict(event='submission_intent',task=job['id'],remaining_reserved_seconds=sum(j['reservation_seconds'] for j in jobs[index:]),attempt=1))
        r=subprocess.run(job['command'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        append(dict(event='submission_response',task=job['id'],returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))
        allocation=r.stdout.strip().split(';')[0]
        if r.returncode or not allocation.isdigit():raise RuntimeError('ambiguous submission preserved; no automatic retry')
        append(dict(event='submitted',task=job['id'],allocation_id=allocation))
        while True:
            footprint(args.run,c)
            r=subprocess.run(['sacct','-n','-P','-X','-j',allocation,'--format=JobIDRaw,JobName,State,ExitCode,ElapsedRaw,AllocTRES,NodeList'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            append(dict(event='scheduler',allocation_id=allocation,stdout=r.stdout,stderr=r.stderr,returncode=r.returncode))
            rows=[x.split('|') for x in r.stdout.strip().splitlines() if x]
            if r.returncode or len(rows)!=1 or rows[0][0]!=allocation:raise RuntimeError('unresolved allocation; preserve, reconcile before any recovery')
            row=rows[0]
            if row[1]!='dtveff0-'+job['id']:raise RuntimeError('allocation task identity mismatch')
            state=row[2].split()[0]
            if state not in ('PENDING','RUNNING','CONFIGURING','COMPLETING'):
                elapsed=int(row[4]);charged+=elapsed;append(dict(event='terminal',task=job['id'],allocation_id=allocation,elapsed_seconds=elapsed,cumulative_gpu_seconds=charged,state=state,exit=row[3],node=row[6],allocated_resources=row[5]))
                if elapsed>800 or state!='COMPLETED' or row[3]!='0:0' or row[6] not in ('gpu09','gpu09.cluster') or 'gres/gpu=1' not in row[5] or not (args.run/job['id']/'SEAL.json').is_file():raise RuntimeError('terminal fault charged and preserved; no retry')
                footprint(args.run,c)
                break
            time.sleep(5)
    append(dict(event='all_complete',cumulative_gpu_seconds=charged,successful_jobs=9,research_outcomes=False))
if __name__=='__main__':main()
