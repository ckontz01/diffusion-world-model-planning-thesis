"""Corrected finite serial dispatch and bounded initial sacct visibility."""
import argparse,json,subprocess,time
from pathlib import Path
from dtv_efficiency_r1.control import DOC,ROOT,load_bindings,WORKER_SECONDS,GRID_RESERVATION_SECONDS,AGGREGATE_SECONDS
from dtv_efficiency_r1.profile import gate

LIVE={'PENDING','RUNNING','CONFIGURING','COMPLETING','SUSPENDED','RESIZING','SIGNALING'}
TERMINAL={'BOOT_FAIL','CANCELLED','COMPLETED','DEADLINE','FAILED','NODE_FAIL','OUT_OF_MEMORY','PREEMPTED','TIMEOUT'}

class ControlFault(RuntimeError):
    def __init__(self,message,charged):super().__init__(message);self.charged=charged

def plan(c,package_root,approval,run):
    env='/lustreFS/data/superworld/ckontzias/thesis/envs/hi-lewm-artifact-py311-cu121-swm006'
    image='/lustreFS/data/superworld/ckontzias/thesis/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif'
    if len(c['jobs'])!=9 or any(j['wall_limit_seconds']!=WORKER_SECONDS for j in c['jobs']) or sum(j['wall_limit_seconds'] for j in c['jobs'])!=GRID_RESERVATION_SECONDS:raise RuntimeError('corrected grid/reservation mismatch')
    return [dict(id=j['id'],reservation_seconds=j['wall_limit_seconds'],command=['sbatch','--parsable','--job-name=dtveff0-'+j['id'],'--account=superworld','--partition=a6000','--qos=normal-a6000','--nodelist=gpu09','--gres=gpu:1','--cpus-per-task=4','--mem=8G','--time=00:13:00','--no-requeue','--output='+str(run/(j['id']+'.out')),'--error='+str(run/(j['id']+'.err')),'--wrap='+'apptainer exec --nv --cleanenv --bind /lustreFS/data/superworld/ckontzias/thesis:/lustreFS/data/superworld/ckontzias/thesis '+image+' env OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH='+str(package_root)+' CUBLAS_WORKSPACE_CONFIG=:4096:8 SLURM_JOB_ID=$SLURM_JOB_ID SLURM_JOB_NAME=$SLURM_JOB_NAME SLURMD_NODENAME=$SLURMD_NODENAME '+env+'/bin/python -m dtv_efficiency_r1.profile --bindings '+str(package_root/'docs/dtv-efficiency-correction-r1-20260930/BINDINGS.json')+' --approval '+str(approval)+' --job '+j['id']+' --output '+str(run/j['id'])]) for j in c['jobs']]

def invoke(command,timeout):
    return subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=timeout)

def dispatch_one(job,append,charged=0,call=invoke,clock=time.monotonic,sleep=time.sleep,check=lambda:None):
    """Exactly one submission. Missing/error responses never become charges."""
    append(dict(event='submission_intent',task=job['id'],attempt=1))
    try:response=call(job['command'],30)
    except subprocess.TimeoutExpired as e:
        append(dict(event='submission_response',task=job['id'],returncode=None,stdout=str(e.stdout or ''),stderr=str(e.stderr or ''),command_timeout=True))
        raise ControlFault('ambiguous submission command timeout; reconcile, never retry',charged)
    append(dict(event='submission_response',task=job['id'],returncode=response.returncode,stdout=response.stdout,stderr=response.stderr))
    allocation=response.stdout.strip().split(';')[0]
    if response.returncode or not allocation.isdigit():raise ControlFault('ambiguous submission preserved; no retry',charged)
    submitted_at=clock();seen=False
    append(dict(event='submitted',task=job['id'],allocation_id=allocation,initial_visibility_allowance_seconds=60))
    while True:
        check()
        command=['sacct','-n','-P','-X','-j',allocation,'--format=JobIDRaw,JobName,State,ExitCode,ElapsedRaw,AllocTRES,NodeList']
        timeout=10 if seen else max(.001,min(10,60-(clock()-submitted_at)))
        try:response=call(command,timeout)
        except subprocess.TimeoutExpired as e:
            append(dict(event='scheduler',allocation_id=allocation,returncode=None,stdout=str(e.stdout or ''),stderr=str(e.stderr or ''),command_timeout=True))
            raise ControlFault('unresolved allocation: accounting command timeout',charged)
        append(dict(event='scheduler',allocation_id=allocation,returncode=response.returncode,stdout=response.stdout,stderr=response.stderr,seconds_since_submission=clock()-submitted_at))
        if response.returncode:raise ControlFault('unresolved allocation: accounting command error',charged)
        rows=[line.split('|') for line in response.stdout.splitlines() if line.strip()]
        if not rows:
            if seen or clock()-submitted_at>=60:raise ControlFault('unresolved allocation: missing accounting row',charged)
            sleep(min(5,60-(clock()-submitted_at)));continue
        if not seen and clock()-submitted_at>60:raise ControlFault('unresolved allocation: initial visibility deadline exceeded',charged)
        if len(rows)!=1:raise ControlFault('unresolved allocation: duplicate/unexpected rows',charged)
        row=rows[0]
        if row[-1]=='':row.pop()
        if len(row)!=7 or row[0]!=allocation or row[1]!='dtveff0-'+job['id']:raise ControlFault('unresolved allocation: conflicting allocation/task identity',charged)
        seen=True;state=row[2].split()[0] if row[2].strip() else ''
        if state in LIVE:sleep(5);continue
        if state not in TERMINAL:raise ControlFault('unresolved allocation: unknown/nonterminal state',charged)
        try:elapsed=int(row[4])
        except ValueError:raise ControlFault('unresolved terminal accounting: invalid elapsed charge',charged)
        if elapsed<0:raise ControlFault('unresolved terminal accounting: negative charge',charged)
        charged+=elapsed
        terminal=dict(event='terminal',task=job['id'],allocation_id=allocation,elapsed_seconds=elapsed,cumulative_gpu_seconds=charged,state=state,exit=row[3],node=row[6],allocated_resources=row[5])
        try:append(terminal)
        except Exception as e:raise ControlFault('actual terminal charge retained despite control-record fault: '+repr(terminal)+'; '+repr(e),charged) from e
        if elapsed>WORKER_SECONDS or charged>AGGREGATE_SECONDS or state!='COMPLETED' or row[3]!='0:0' or row[6] not in ('gpu09','gpu09.cluster') or 'gres/gpu=1' not in row[5]:raise ControlFault('actual terminal fault charged once; no retry',charged)
        return charged,terminal

def footprint(run,c):
    manifest=DOC/'PACKAGE-MANIFEST.json';package=json.loads(manifest.read_text())
    source_bytes=sum(r['bytes'] for r in package['files'])+manifest.stat().st_size
    if source_bytes>4000000:raise RuntimeError('complete source and manifest ceiling')
    if sum(p.stat().st_size for p in run.rglob('*') if p.is_file())+source_bytes>c['live_bytes_cap']:raise RuntimeError('live footprint ceiling')
    for job in c['jobs']:
        if sum(p.stat().st_size for p in (run/(job['id']+'.out'),run/(job['id']+'.err')) if p.exists())>2000000:raise RuntimeError('worker log cap')
        root=run/job['id']
        if root.exists() and sum(p.stat().st_size for p in root.rglob('*') if p.is_file())>job['output_limit_bytes']:raise RuntimeError('complete worker output cap')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--submit',action='store_true');parser.add_argument('--run',type=Path,required=True);parser.add_argument('--approval',type=Path,default=DOC/'EXECUTION-APPROVAL.json');args=parser.parse_args()
    c=load_bindings();jobs=plan(c,ROOT,args.approval,args.run)
    if not args.submit:print(json.dumps(dict(execute=False,full_future_gpu_reservation_seconds=GRID_RESERVATION_SECONDS,aggregate_gpu_allocation_seconds_ceiling=AGGREGATE_SECONDS,jobs=jobs),indent=2));return
    gate(DOC/'BINDINGS.json',json.loads(args.approval.read_text()))
    if not str(args.run).startswith('/lustreFS/data/superworld/ckontzias/thesis/experiments/dtv-efficiency-20260930/run-') or args.run.exists():raise RuntimeError('exclusive namespace required; successful/live/ambiguous work never repeated')
    args.run.mkdir(parents=True);charged=0;ledger=args.run/'DISPATCH.jsonl'
    def append(event):
        with ledger.open('a') as f:f.write(json.dumps(event)+'\n');f.flush()
        # Preserve the triggering raw response/charge rather than discard it.
        if ledger.stat().st_size>1000000:raise RuntimeError('control ledger cap; triggering evidence retained')
    try:
        for index,job in enumerate(jobs):
            remaining=sum(j['reservation_seconds'] for j in jobs[index:])
            if charged+remaining>AGGREGATE_SECONDS:raise ControlFault('full remaining reservation exhausted',charged)
            append(dict(event='full_remaining_reservation',charged_seconds=charged,remaining_seconds=remaining))
            charged,_=dispatch_one(job,append,charged=charged,check=lambda:footprint(args.run,c))
            if not (args.run/job['id']/'CONTROL-SEAL.json').is_file():raise ControlFault('terminal success without independently sealed control evidence',charged)
            footprint(args.run,c)
        append(dict(event='all_complete',cumulative_gpu_seconds=charged,successful_jobs=9,research_outcomes=False))
    except Exception as e:
        charged=getattr(e,'charged',charged)
        with (args.run/'STOP.json').open('x') as f:json.dump(dict(error=repr(e),known_terminal_gpu_seconds=charged,unresolved_allocations_must_be_reconciled=True,automatic_retry=False),f,indent=2)
        raise
if __name__=='__main__':main()
