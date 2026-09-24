"""One-shot serial dispatcher. A restart is NEVER a resubmission strategy."""
import common as c
import argparse
import os
from pathlib import Path
import subprocess
import time
import traceback
import acceptance
import scheduler
import storage

def reservation(jobs,terminals):
    # Terminal failures still consume their actual charge; all uncompleted tasks reserve full limits.
    gpu=cpu=0
    for j in jobs:
        seconds=terminals.get(j['key'],{}).get('row',{}).get('seconds',j['seconds'])
        if j['gpu']: gpu+=seconds
        else: cpu+=seconds
    c.require(gpu<=c.caps()['gpu_allocation_seconds'] and cpu<=c.caps()['cpu_stage_allocation_seconds'],'Full future compute reservation')
    return dict(gpu_seconds=gpu,cpu_stage_seconds=cpu)

def command(spec,approval,run):
    cmd=['/usr/bin/sbatch','--parsable','--no-requeue','--account=superworld','--cpus-per-task=4',
         '--mem='+str(spec['ram_gib'])+'G','--time='+str(spec['seconds']//60),
         '--job-name=acvm1-'+spec['key'],'--output='+str(run/'logs'/(spec['key']+'.slurm.out')),
         '--error='+str(run/'logs'/(spec['key']+'.slurm.err'))]
    if spec['gpu']: cmd+=['--partition=a6000','--qos=normal-a6000','--gres=gpu:1','--nodelist=gpu09']
    else: cmd+=['--partition=defq','--qos=normal']
    return cmd+['/bin/bash',str(c.ROOT/'run_worker.sh'),str(c.ROOT),str(approval),str(run),spec['key'],str(spec['gpu'])]

class RealScheduler:
    def __init__(self,control,approval,run): self.control=control; self.approval=approval; self.run=run
    def submit(self,spec):
        cmd=command(spec,self.approval,self.run)
        try:
            p=subprocess.run(cmd,capture_output=True,text=True,timeout=60)
            r=dict(command=cmd,stdout=p.stdout,stderr=p.stderr,returncode=p.returncode)
        except subprocess.TimeoutExpired as e:
            r=dict(command=cmd,stdout=str(e.stdout or ''),stderr=str(e.stderr or ''),returncode=124)
        c.write(self.control/(spec['key']+'.SUBMIT.json'),r)
        v=r['stdout'].strip()
        c.require(r['returncode']==0 and v.isdigit(),'AMBIGUOUS submission; full claim retained, no retry')
        return v
    def terminal(self,job,spec):
        grace=0; poll=0
        while True:
            poll+=1
            raw=scheduler.observe(self.control,[job],spec['key']+'-'+str(poll))
            state=scheduler.status(raw,job,spec)
            if state=='INCOMPLETE':
                grace+=1; c.require(grace<=8,'Incomplete accounting grace exhausted')
            else: grace=0
            if state in scheduler.TERMINAL: return scheduler.parse(raw.strip())
            c.require(c.bytes_in(self.control)<=150_000_000,'Scheduler/control log envelope')
            time.sleep(15)

def campaign(auth,control,sched,*,jobs=None,accept=None,reuse=None,freeze=None,gate=None,storage_check=None):
    """Same state machine for real and mocked scheduler. Injection is not a CLI capability."""
    jobs=c.grid() if jobs is None else jobs
    c.require(not (control/'CONTROLLER-STARTED.json').exists() and not (control/'CAMPAIGN.jsonl').exists(),'Already started: no restart/repeat')
    c.require(not any((auth.run/j['key']).exists() for j in jobs),'Pre-existing output/task forbidden')
    c.write(control/'CONTROLLER-STARTED.json',dict(unix=time.time(),package=auth.approval['package_sha256']))
    terminals={}; completed=set(); eval_count=0
    def event(kind,**v): c.append(control/'CAMPAIGN.jsonl',dict(event=kind,unix=time.time(),**v))
    try:
        if reuse: reuse()
        for spec in jobs:
            c.require(not (control/'STOP.json').exists(),'Unknown STOP')
            if spec['stage']=='evaluation' and eval_count==0 and freeze: freeze()
            reserve=reservation(jobs,terminals)
            if storage_check: storage_check(completed)
            event('claim',key=spec['key'],spec=spec,reservation=reserve)
            # Claim durable before scheduler side effect. Any ambiguity is irrevocably fail-stop.
            job=sched.submit(spec)
            event('submitted',key=spec['key'],job=job)
            c.write(auth.run/'submissions'/(spec['key']+'.json'),dict(job=job,spec=spec,package=auth.approval['package_sha256']))
            row=sched.terminal(job,spec)
            # Charge BEFORE state, hardware or evidence validation; preserve terminal faults.
            event('terminal',key=spec['key'],row=row); terminals[spec['key']]={'row':row}
            receipt=accept(spec,row)
            event('accepted',key=spec['key'],**{k:v for k,v in receipt.items() if k!='key'})
            completed.add(spec['key'])
            if spec['stage']=='evaluation':
                eval_count+=1
                if eval_count==16 and gate: gate()
        c.write(control/'COMPUTE-COMPLETE.json',dict(unix=time.time(),tasks=len(completed),episodes=eval_count,
                charges=reservation([],{}),gpu_seconds=sum(v['row']['seconds'] for k,v in terminals.items() if next(j for j in jobs if j['key']==k)['gpu']),
                cpu_seconds=sum(v['row']['seconds'] for k,v in terminals.items() if not next(j for j in jobs if j['key']==k)['gpu'])))
    except BaseException as e:
        c.write(control/'STOP.json',dict(unix=time.time(),error=repr(e),traceback=traceback.format_exc(),automatic_retry=False)); raise

def main():
    p=argparse.ArgumentParser();p.add_argument('--approval',required=True);p.add_argument('--run',required=True);p.add_argument('--control',required=True);a=p.parse_args()
    auth=c.Authorization(a.approval,a.run);control=Path(a.control)
    expected=c.RESEARCH+'/staging/'+c.NAMESPACE+'-'+auth.approval['package_sha256'][:16]
    c.require(str(control)==expected,'Exact control namespace')
    for path,h in c.read(c.ROOT/'CONTROLLER-RUNTIME.json')['files'].items(): c.require(c.sha(path)==h,'Controller runtime identity')
    from models import reuse,freeze
    campaign(auth,control,RealScheduler(control,Path(a.approval),auth.run),
             accept=lambda j,r:acceptance.worker(auth.run,j,r,auth.approval['package_sha256'],auth.approval_sha),
             reuse=lambda:reuse(auth),freeze=lambda:freeze(auth.run,auth.approval['package_sha256']),
             gate=lambda:acceptance.gate(auth.run,c.grid()),
             storage_check=lambda done:storage.check(c.REPO,control,auth.run,c.grid(),done))
if __name__=='__main__':main()
