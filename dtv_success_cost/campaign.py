"""Finite, serial, no-retry dispatcher. Dry plan is the default."""
import argparse
import json
import shlex
import subprocess
import time
from dtv_success_cost.common import *
from dtv_efficiency_r1.campaign import LIVE,TERMINAL,ControlFault,invoke

def commands(c,approval,run):
    run=PurePosixPath(Path(run).as_posix())
    env=REMOTE/'envs/hi-lewm-artifact-py311-cu121-swm006';image=REMOTE/'containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif'
    result=[]
    for j in [dict(id='preflight',wall_seconds=7200,work_seconds=7140,output_bytes=1000000,log_bytes=100000)]+c['jobs']+[dict(id='analysis',wall_seconds=7200,work_seconds=7140,output_bytes=c['analysis_bytes'],log_bytes=100000)]:
        gpu=j['id'] not in ('analysis','preflight')
        python=['env','OMP_NUM_THREADS=4','MKL_NUM_THREADS=4','OPENBLAS_NUM_THREADS=4','PYTHONNOUSERSITE=1','PYTHONDONTWRITEBYTECODE=1','PYTHONPATH='+str(ROOT),'CUBLAS_WORKSPACE_CONFIG=:4096:8',str(env/'bin/python'),'-m','dtv_success_cost.worker','--approval',str(approval),'--job',j['id'],'--output',str(run/j['id'])]
        if not gpu:python+=['--run',str(run)]
        wrap=['apptainer','exec']+(['--nv'] if gpu else [])+['--cleanenv','--bind',str(REMOTE)+':'+str(REMOTE),str(image)]
        # These are only site-provided allocation values, never keys/credentials.
        forwarding=' SLURM_JOB_ID=$SLURM_JOB_ID SLURM_JOB_NAME=$SLURM_JOB_NAME SLURMD_NODENAME=$SLURMD_NODENAME '
        body=shlex.join(wrap)+' '+shlex.join(python[:1])+forwarding+shlex.join(python[1:])
        base=['sbatch','--parsable','--job-name=dtveff1-'+j['id'],'--account=superworld','--cpus-per-task=4','--mem=8G','--time='+('00:05:00' if gpu else '02:00:00'),'--no-requeue','--output='+str(run/(j['id']+'.out')),'--error='+str(run/(j['id']+'.err'))]
        base+=['--partition=a6000','--qos=normal-a6000','--nodelist=gpu09','--gres=gpu:1'] if gpu else ['--partition=defq','--qos=normal']
        result.append(dict(**j,gpu=gpu,command=base+['--wrap='+body]))
    return result

def dispatch(job,append,charges,call=invoke,clock=time.monotonic,sleep=time.sleep,check=lambda:None):
    append(dict(event='submission_intent',task=job['id']))
    try:r=call(job['command'],30)
    except subprocess.TimeoutExpired as e:
        append(dict(event='submission_response',task=job['id'],error=repr(e),ambiguous=True));raise ControlFault('ambiguous submission; preserve and reconcile, never repeat',dict(charges))
    append(dict(event='submission_response',task=job['id'],stdout=r.stdout,stderr=r.stderr,returncode=r.returncode))
    allocation=r.stdout.strip().split(';')[0]
    if r.returncode or not allocation.isdigit():raise ControlFault('ambiguous submission, no retry',dict(charges))
    began=clock();seen=False;placeholder=0
    append(dict(event='submitted',task=job['id'],allocation_id=allocation))
    while True:
        check()
        try:r=call(['sacct','-n','-P','-X','-j',allocation,'--format=JobIDRaw,JobName,State,ExitCode,ElapsedRaw,AllocTRES,NodeList'],10)
        except subprocess.TimeoutExpired as e:
            append(dict(event='scheduler',allocation_id=allocation,error=repr(e)));raise ControlFault('unresolved scheduler timeout',dict(charges))
        append(dict(event='scheduler',allocation_id=allocation,stdout=r.stdout,stderr=r.stderr,returncode=r.returncode))
        if r.returncode:raise ControlFault('unresolved scheduler command failure',dict(charges))
        rows=[s.split('|') for s in r.stdout.splitlines() if s.strip()]
        if not rows:
            if seen or clock()-began>=60:raise ControlFault('bounded initial accounting visibility exhausted',dict(charges))
            sleep(min(5,60-(clock()-began)));continue
        if len(rows)!=1:raise ControlFault('unexpected accounting rows',dict(charges))
        row=rows[0]
        if row[-1]=='':row.pop()
        if len(row)!=7 or row[0]!=allocation:raise ControlFault('wrong allocation identity',dict(charges))
        state=row[2].split()[0]
        # Carry the accepted R4 correction: only this exact pending placeholder,
        # with the submitted ID, gets finite grace; terminal identities stay strict.
        if job['gpu'] and row[1]=='allocation' and state=='PENDING' and row[3:5]==['0:0','0'] and row[6] in ('gpu09',''):
            placeholder+=1
            if placeholder>8 or clock()-began>=60:raise ControlFault('pending identity grace exhausted',dict(charges))
            sleep(5);continue
        if state in TERMINAL:
            if not row[4].isdigit():raise ControlFault('invalid terminal charge',dict(charges))
            elapsed=int(row[4]);kind='gpu' if job['gpu'] else 'cpu';charges[kind]+=elapsed
            terminal=dict(event='terminal',task=job['id'],allocation_id=allocation,state=state,exit=row[3],elapsed_seconds=elapsed,charges=dict(charges),node=row[6],resources=row[5]);append(terminal)
            # Charge genuine terminal work before rejecting conflicting metadata.
            if row[1]!='dtveff1-'+job['id'] or state!='COMPLETED' or row[3]!='0:0' or elapsed>job['wall_seconds']:raise ControlFault('terminal fault charged and preserved',dict(charges))
            if job['gpu'] and (row[6] not in ('gpu09','gpu09.cluster') or 'gres/gpu=1' not in row[5]):raise ControlFault('wrong hardware/allocation charged',dict(charges))
            resources=dict(x.split('=',1) for x in row[5].split(',') if '=' in x)
            if job['gpu'] and resources.get('gres/gpu')!='1':raise ControlFault('wrong GPU allocation cardinality charged',dict(charges))
            if not job['gpu'] and 'gres/gpu' in row[5]:raise ControlFault('analysis unexpectedly used GPU',dict(charges))
            return terminal
        if row[1]!='dtveff1-'+job['id'] or state not in LIVE:raise ControlFault('nonterminal identity/state fault',dict(charges))
        if not seen and clock()-began>60:raise ControlFault('initial visibility deadline exceeded',dict(charges))
        seen=True;sleep(5)

def footprint(c,run,remaining):
    run=Path(run);live=sum(p.stat().st_size for p in run.rglob('*') if p.is_file())
    reservation=sum(j['output_bytes']+j['log_bytes'] for j in remaining)+c['source_bytes']+c['control_bytes']+c['reused_model_bytes']
    if live+reservation>c['live_bytes']:raise RuntimeError('full remaining output reservation exhausted')
    if live+c['source_bytes']+c['archive_bytes']*2>c['inclusive_bytes']:raise RuntimeError('history/archive/SSD inclusive cap')
    for j in c['jobs']:
        if sum(p.stat().st_size for p in (run/(j['id']+'.out'),run/(j['id']+'.err')) if p.exists())>j['log_bytes']:raise RuntimeError('retained log cap')

def main():
    p=argparse.ArgumentParser();p.add_argument('--submit',action='store_true');p.add_argument('--approval',type=Path,default=DOC/'EXECUTION-APPROVAL.json');a=p.parse_args();c=load(DOC/'BINDINGS.json');run=run_namespace(c);jobs=commands(c,a.approval,run)
    if not a.submit:
        print(json.dumps(dict(execute=False,run=run.as_posix(),scheduled_tasks=len(jobs),gpu_seconds=c['gpu_seconds'],cpu_seconds=c['cpu_seconds'],first_command=jobs[0]['command'])));return
    gate(a.approval)
    if run.exists():raise RuntimeError('exclusive namespace already exists; no automated restart/repeat')
    run.mkdir(parents=True);charges=dict(gpu=0,cpu=0)
    def append(r):
        with (run/'DISPATCH.jsonl').open('a') as f:f.write(json.dumps(r,separators=(',',':'))+'\n');f.flush();__import__('os').fsync(f.fileno())
        if (run/'DISPATCH.jsonl').stat().st_size>c['control_bytes']:raise RuntimeError('control cap; triggering evidence retained')
    try:
        for i,j in enumerate(jobs):
            footprint(c,run,jobs[i:])
            if charges['gpu']+sum(v['wall_seconds'] for v in jobs[i:] if v['gpu'])>c['gpu_seconds'] or charges['cpu']+sum(v['wall_seconds'] for v in jobs[i:] if not v['gpu'])>c['cpu_seconds']:raise RuntimeError('full future compute reservation exhausted')
            terminal=dispatch(j,append,charges,check=lambda:footprint(c,run,jobs[i+1:]))
            from dtv_success_cost.accept import accept_worker
            if j['gpu']:accept_worker(c,j,run,terminal['allocation_id'])
            else:
                read_seal(run/j['id'],j['id'])
                if sum(p.stat().st_size for p in (run/j['id']).rglob('*') if p.is_file())>j['output_bytes']:raise RuntimeError('complete CPU-stage output cap')
            append(dict(event='accepted',task=j['id'],seal_sha256=sha(run/j['id']/'SEAL.json')))
            if i==9:
                append(dict(event='technical_tranche_passed',included_workers=9,included_episodes=72,scientific_selection=False))
        from dtv_success_cost.accept import accounting
        write(run/'COMPUTE-COMPLETE.json',dict(**accounting(run,c,True),bindings_sha256=sha(DOC/'BINDINGS.json')))
    except Exception as e:
        write(run/'STOP.json',dict(error=repr(e),charges=charges,automatic_retry=False));raise
if __name__=='__main__':main()
