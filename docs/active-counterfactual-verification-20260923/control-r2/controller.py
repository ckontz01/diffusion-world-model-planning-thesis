"""Exclusive R2 controller: reuse490, submit only338 never-created tasks."""
import r2_core as r
import argparse
import os
from pathlib import Path
import subprocess
import time

def permitted(spec,jobs):
    r.require(spec['key']!='collect-fit-490' and spec in jobs[1:],'490/new generic restart blocked')

class Slurm:
    def __init__(self,ctx):self.ctx=ctx;self.claimed=set()
    def submit(self,j):
        ctx=self.ctx;permitted(j,ctx.jobs)
        r.require(j['key'] not in self.claimed and not (ctx.run/j['key']).exists(),'No repeated or existing scientific task')
        self.claimed.add(j['key']);r.stop_guard(ctx)
        args=['sbatch','--parsable','--no-requeue','--account=superworld','--cpus-per-task=4',
              '--mem='+('24G' if j['gpu'] else '8G'),'--time='+str(j['seconds']//60),
              '--partition='+('a6000' if j['gpu'] else 'defq'),'--qos='+('normal-a6000' if j['gpu'] else 'normal'),
              '--job-name=acv0r2-'+j['key'],'--output='+str(ctx.run/(j['key']+'-%j.out')),
              '--error='+str(ctx.run/(j['key']+'-%j.err'))]
        if j['gpu']:args+=['--gres=gpu:1','--nodelist=gpu09']
        args += [str(ctx.science_root/'run_worker.sh'),str(ctx.science_root),str(ctx.worker_approval),str(ctx.run),j['key'],str(j['gpu'])]
        p=subprocess.run(args,capture_output=True,text=True,timeout=60)
        r.require(p.returncode==0 and p.stdout.strip().split(';')[0].isdigit(),'Ambiguous submission: '+p.stderr[:4096])
        return p.stdout.strip().split(';')[0]
    def wait(self,job,spec):
        while True:
            p=subprocess.run(['sacct','-X','-n','-P','-j',job,'--format='+r.FIELDS],capture_output=True,text=True,timeout=60)
            r.require(p.returncode==0,'Scheduler unavailable: '+p.stderr[:4096])
            rows=[line for line in p.stdout.splitlines() if line.split('|')[0]==job]
            r.require(len(rows)<=1,'Ambiguous exact allocation')
            if rows:
                row=r.parse_row(rows[0])
                if row['state'] not in ('PENDING','RUNNING','CONFIGURING','COMPLETING'):return row
            time.sleep(15)

def execute(jobs,existing,scheduler,record,check,gate,budget_check):
    r.require(len(jobs)==339 and existing['spec']==jobs[0] and existing['job']=='304193'
              and existing['seconds']==80 and existing['state']=='COMPLETED','Exact reused supplier')
    r.require(len({j['key'] for j in jobs})==339 and jobs[0]['key']=='collect-fit-490' and jobs[1]['key']=='collect-fit-545','Exact task order')
    completed=[existing];gpu=103;cpu=0;known={'304189','304193'};keys={'collect-fit-490'}
    for i in range(1,len(jobs)):
        j=jobs[i];permitted(j,jobs);r.require(j['key'] not in keys,'Repeated task key');keys.add(j['key'])
        budget_check()
        remaining=sum(k['seconds'] for k in jobs[i:] if k['gpu'])
        r.require(gpu+remaining<=220800,'Full remaining campaign GPU reservation')
        r.require(cpu+sum(k['seconds'] for k in jobs[i:] if not k['gpu'])<=21600,'Full remaining CPU reservation')
        if i==2:gate('technical',completed)
        if i==82:gate('models',completed)
        if j['stage']=='analysis':gate('analysis',completed)
        record({'event':'claim','spec':j,'attempt':1,'reserved_seconds':j['seconds'],
                'campaign_gpu_seconds':gpu,'remaining_gpu_reservation':remaining,'r2_replacements_authorized':0})
        try:job=scheduler.submit(j)
        except BaseException as e:
            record({'event':'submission_unresolved','spec':j,'reservation_retained':j['seconds'],'error':repr(e)[:4096]});raise
        r.require(job not in known,'Repeated allocation ID');known.add(job)
        record({'event':'submitted','spec':j,'job':job,'attempt':1,'automatic_retry_count':0})
        try:terminal=scheduler.wait(job,j)
        except BaseException as e:
            record({'event':'observation_unresolved','spec':j,'job':job,'reservation_retained':j['seconds'],'error':repr(e)[:4096]});raise
        seconds=int(terminal['seconds']);r.require(seconds>=0,'Negative charge')
        if j['gpu']:gpu+=seconds*int(terminal['gpus'])
        else:cpu+=seconds
        row=dict(terminal,event='terminal',spec=j,job=job,attempt=1,campaign_gpu_seconds=gpu,campaign_cpu_stage_seconds=cpu)
        record(row)  # Charge failures before acceptance; never retry.
        r.allocation_contract(j,row)
        acceptance=check(j,row);record(dict(acceptance,event='accepted_new',new_submission=True))
        completed.append(row)
    return {'jobs':completed,'campaign_gpu_seconds':gpu,'campaign_cpu_stage_seconds':cpu,'new_r2_allocations':338,
            'campaign_allocations':340,'successful_unique_tasks':339,'historical_failed_allocations':1,
            'previously_authorized_replacements':1,'new_replacements_authorized':0,'automatic_retry_count':0}

def gates(ctx,name,rows):
    if name=='technical':
        r.require([v['spec'] for v in rows]==ctx.jobs[:2] and [v['job'] for v in rows][0]=='304193','Both included490/545 required')
        accepted=[r.verify_worker(ctx,j,row) for j,row in zip(ctx.jobs[:2],rows)]
        ctx.c.write(ctx.run/'TECHNICAL-TRANCHE-PASSED.json',{'seals':{a['key']:a['seal_sha256'] for a in accepted},'scientific_selection':False})
        r.write(ctx.control/'TECHNICAL-TRANCHE-R2.json',{'unix':time.time(),'suppliers':accepted,'failed304189_counted':False,
                'original_run_marker_sha256':r.sha(ctx.run/'TECHNICAL-TRANCHE-PASSED.json')})
    elif name=='models':
        r.require([v['spec'] for v in rows]==ctx.jobs[:82],'All collection/fitting tasks before freeze')
        from model_seal import model_freeze
        model_freeze(ctx.run,r.SCIENCE_MANIFEST)
        r.write(ctx.control/'MODEL-FREEZE-R2.json',{'unix':time.time(),'original_model_freeze_sha256':r.sha(ctx.run/'MODEL-FREEZE.json')})
    else:
        r.require(len(rows)==338 and [v['spec'] for v in rows]==ctx.jobs[:-1] and len({v['job'] for v in rows})==338,'Full combined pre-analysis logical grid')
        ctx.c.write(ctx.run/'PRE-ANALYSIS-ACCOUNTING.json',{'jobs':rows})

def main():
    p=argparse.ArgumentParser();p.add_argument('--approval',required=True);args=p.parse_args()
    ctx=r.Context(args.approval)
    from controller_runtime import verify
    verify();reconciled=r.reconcile(ctx);ctx.auth.runtime();r.storage(ctx)
    r.write(ctx.control/'CONTROLLER-STARTED.json',{'pid':os.getpid(),'start_ticks':Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19],
            'unix':time.time(),'control_manifest':ctx.binding['control_manifest'],'approval_sha256':ctx.approval_sha})
    def record(row):
        row['unix']=time.time();r.append(ctx.control/'CAMPAIGN-R2.jsonl',row)
        if row['event'] in ('accepted_existing','accepted_new'):r.append(ctx.control/'SCIENTIFIC-TASKS-R2.jsonl',row)
    try:
        r.write(ctx.control/'RECONCILIATION.json',reconciled)
        existing,accepted=r.accept_existing(ctx);r.write(ctx.control/'ACCEPTED-EXISTING.json',accepted);record(accepted)
        r.write(ctx.control/'STOP-RESOLUTION.json',{'resolved_stop_path':str(ctx.run/'STOP.json'),'resolved_stop_sha256':r.STOP_SHA,
                'instruction_sha256':ctx.binding['instruction_sha256'],'r2_approval_sha256':ctx.approval_sha,'accepted_existing_sha256':r.sha(ctx.control/'ACCEPTED-EXISTING.json'),
                'scope':'Only documented R1 hostname-association fault; original STOP retained, no new stop waived','unix':time.time()})
        def budget():r.stop_guard(ctx);r.storage(ctx)
        result=execute(ctx.jobs,existing,Slurm(ctx),record,lambda j,row:r.verify_worker(ctx,j,row),lambda n,rows:gates(ctx,n,rows),budget)
        import finalize
        result['storage']=r.storage(ctx)
        r.write(ctx.control/'FINAL-SCHEDULER.json',finalize.scheduler_snapshot(ctx,result))
        combined=finalize.accept(ctx,result)
        r.write(ctx.control/'COMBINED-CAMPAIGN.json',combined)
        r.write(ctx.control/'COMPUTE-COMPLETE.json',result)
        r.write(ctx.run/'COMPUTE-COMPLETE.json',{'r2_control':str(ctx.control),'completion_sha256':r.sha(ctx.control/'COMPUTE-COMPLETE.json'),
                'combined_campaign_sha256':r.sha(ctx.control/'COMBINED-CAMPAIGN.json'),'successful_unique_tasks':339,'campaign_allocations':340})
    except BaseException as e:
        r.write(ctx.control/'STOP-R2.json',{'error':repr(e)[:4096],'unix':time.time(),'automatic_retry':False,'action':'Preserve; reconcile; no further continuation authorized'})
        raise

if __name__=='__main__':main()
