"""Exclusive R4 controller: reuse37 completed tasks; only302 new submissions."""
import r4_core as r
import argparse
import os
from pathlib import Path
import subprocess
import time

def permitted(spec,jobs):
    r.require(spec['key'] not in {j['key'] for j in jobs[:37]} and spec in jobs[37:],'Existing37/generic restart blocked')

ACTIVE={'PENDING','RUNNING','CONFIGURING','COMPLETING'}
TERMINAL={'COMPLETED','FAILED','CANCELLED','TIMEOUT','OUT_OF_MEMORY','NODE_FAIL','BOOT_FAIL','DEADLINE','PREEMPTED','REVOKED'}

def observation(text,job,spec):
    """Identity/state first; never turn missing accounting into zero charges."""
    lines=[line for line in text.splitlines() if line.strip()]
    r.require(len(lines)<=1,'Duplicate/unexpected allocation rows')
    if not lines:return None,'missing-row'
    fields=lines[0].split('|')
    r.require(fields[0]==job,'Wrong scheduler allocation ID')
    if len(fields)>13 or (len(fields)==13 and fields[-1]!=''):raise ValueError('Unexpected scheduler schema')
    if len(fields)<3:return None,'incomplete-identity/state'
    # Observed304237 accounting placeholder, not an authenticated task row.
    # Require the exact allocated ID and exact saved incomplete PENDING shape;
    # it consumes the same finite incomplete-status allowance as missing rows.
    if len(fields) in (12,13) and r.columns(fields)==[job,'allocation','PENDING','0:0','0','0','','gpu09','','Unknown','superworld',''] and spec['gpu']==1:
        return None,'incomplete-pending-allocation-placeholder'
    if fields[1]:r.require(fields[1]=='acv0r4-'+spec['key'],'Wrong scheduler task identity')
    if not fields[1] or not fields[2]:return None,'incomplete-identity/state'
    state=fields[2].split()[0]
    r.require(state in ACTIVE|TERMINAL,'Unknown/requeued scheduler state: '+state)
    if state in ACTIVE:return None,'active:'+state
    if len(fields) not in (12,13):return None,'incomplete-terminal-columns'
    col=r.columns(fields)
    if not all(col):return None,'incomplete-terminal-fields'
    return r.parse_row(col),'terminal:'+state

class Slurm:
    def __init__(self,ctx):self.ctx=ctx;self.claimed=set()
    def submit(self,j):
        ctx=self.ctx;permitted(j,ctx.jobs)
        r.require(j['key'] not in self.claimed and not (ctx.run/j['key']).exists(),'No repeated or existing scientific task')
        self.claimed.add(j['key']);r.stop_guard(ctx)
        args=['sbatch','--parsable','--no-requeue','--account=superworld','--cpus-per-task=4',
              '--mem='+('24G' if j['gpu'] else '8G'),'--time='+str(j['seconds']//60),
              '--partition='+('a6000' if j['gpu'] else 'defq'),'--qos='+('normal-a6000' if j['gpu'] else 'normal'),
              '--job-name=acv0r4-'+j['key'],'--output='+str(ctx.run/(j['key']+'-%j.out')),
              '--error='+str(ctx.run/(j['key']+'-%j.err'))]
        if j['gpu']:args+=['--gres=gpu:1','--nodelist=gpu09']
        args += [str(ctx.science_root/'run_worker.sh'),str(ctx.science_root),str(ctx.worker_approval),str(ctx.run),j['key'],str(j['gpu'])]
        p=subprocess.run(args,capture_output=True,text=True,timeout=60)
        r.require(p.returncode==0 and p.stdout.strip().split(';')[0].isdigit(),'Ambiguous submission: '+p.stderr[:4096])
        return p.stdout.strip().split(';')[0]
    def wait(self,job,spec):
        uncertain=0;last=None;log=self.ctx.control/'SCHEDULER-OBSERVATIONS.jsonl'
        while True:
            r.stop_guard(self.ctx)
            p=subprocess.run(['sacct','-X','-n','-P','-j',job,'--format='+r.FIELDS],capture_output=True,text=True,timeout=60)
            def preserve(reason):
                entry={'unix':time.time(),'job':job,'key':spec['key'],'returncode':p.returncode,
                       'stdout':p.stdout[:32768],'stderr':p.stderr[:16384],'reason':reason,'status_only':True}
                data=r.canonical(entry)+b'\n'
                r.require((log.stat().st_size if log.exists() else 0)+len(data)<=10000000,'Scheduler technical log cap')
                r.append(log,entry)
            try:
                r.require(p.returncode==0,'Scheduler unavailable: '+p.stderr[:4096])
                r.require(len(p.stdout)<=32768 and len(p.stderr)<=16384,'Oversized scheduler response')
                row,reason=observation(p.stdout,job,spec)
            except BaseException as e:preserve('fault:'+repr(e));raise
            incomplete=not reason.startswith(('active:','terminal:'))
            if incomplete or reason!=last:preserve(reason)
            last=reason
            if row is not None:return row
            uncertain=uncertain+1 if incomplete else 0
            r.require(uncertain<=8,'Accounting incomplete beyond8 consecutive observations; preserve allocation, no retry')
            time.sleep(15)

def execute(jobs,existing,scheduler,record,check,gate,budget_check):
    r.require(len(jobs)==339 and len(existing)==37 and [v['spec'] for v in existing]==jobs[:37]
              and existing[0]['job']=='304193' and existing[-1]['job']=='304237'
              and all(v['state']=='COMPLETED' and v['exit_code']=='0:0' for v in existing),'Exact37 reused suppliers')
    r.require(len({j['key'] for j in jobs})==339 and jobs[37]['key']=='collect-fit-256','Exact task order')
    completed=list(existing);gpu=23+sum(v['seconds']*v['gpus'] for v in existing);cpu=0
    r.require(gpu==4862 and len({v['job'] for v in existing})==37,'Prior charges/identities once')
    known={'304189'}|{v['job'] for v in existing};keys={v['spec']['key'] for v in existing}
    for i in range(37,len(jobs)):
        j=jobs[i];permitted(j,jobs);r.require(j['key'] not in keys,'Repeated task key');keys.add(j['key'])
        budget_check()
        remaining=sum(k['seconds'] for k in jobs[i:] if k['gpu'])
        r.require(gpu+remaining<=220800,'Full remaining campaign GPU reservation')
        r.require(cpu+sum(k['seconds'] for k in jobs[i:] if not k['gpu'])<=21600,'Full remaining CPU reservation')
        if i==82:gate('models',completed)
        if j['stage']=='analysis':gate('analysis',completed)
        record({'event':'claim','spec':j,'attempt':1,'reserved_seconds':j['seconds'],
                'campaign_gpu_seconds':gpu,'remaining_gpu_reservation':remaining,'r4_replacements_authorized':0})
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
    return {'jobs':completed,'campaign_gpu_seconds':gpu,'campaign_cpu_stage_seconds':cpu,'new_r4_allocations':302,
            'campaign_allocations':340,'successful_unique_tasks':339,'historical_failed_allocations':1,
            'previously_authorized_replacements':1,'new_replacements_authorized':0,'automatic_retry_count':0}

def gates(ctx,name,rows):
    if name=='models':
        r.require([v['spec'] for v in rows]==ctx.jobs[:82],'All collection/fitting tasks before freeze')
        from model_seal import model_freeze
        model_freeze(ctx.run,r.SCIENCE_MANIFEST)
        r.write(ctx.control/'MODEL-FREEZE-R4.json',{'unix':time.time(),'original_model_freeze_sha256':r.sha(ctx.run/'MODEL-FREEZE.json')})
    else:
        r.require(name=='analysis','No tranche rewrite or unknown gate')
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
        row['unix']=time.time();r.append(ctx.control/'CAMPAIGN-R4.jsonl',row)
        if row['event'] in ('accepted_existing','accepted_new'):r.append(ctx.control/'SCIENTIFIC-TASKS-R4.jsonl',row)
    try:
        r.write(ctx.control/'RECONCILIATION.json',reconciled)
        existing,accepted=r.accept_existing(ctx);r.write(ctx.control/'ACCEPTED-EXISTING.json',accepted)
        for entry in accepted:record(entry)
        r.write(ctx.control/'STOP-RESOLUTION.json',{'resolved_stop_path':str(ctx.run/'STOP.json'),'resolved_stop_sha256':r.STOP_SHA,
                'resolved_r2_stop_sha256':ctx.binding['resolved_r2_stop_sha256'],
                'resolved_r3_stop_sha256':ctx.binding['resolved_r3_stop_sha256'],
                'instruction_sha256':ctx.binding['instruction_sha256'],'r4_approval_sha256':ctx.approval_sha,'accepted_existing_sha256':r.sha(ctx.control/'ACCEPTED-EXISTING.json'),
                'scope':'Only authenticated historical R1/R2/R3 control faults; all STOPs retained, no new fault waived','unix':time.time()})
        def budget():r.stop_guard(ctx);r.storage(ctx)
        result=execute(ctx.jobs,existing,Slurm(ctx),record,lambda j,row:r.verify_worker(ctx,j,row),lambda n,rows:gates(ctx,n,rows),budget)
        import finalize4 as finalize
        result['storage']=r.storage(ctx)
        r.write(ctx.control/'FINAL-SCHEDULER.json',finalize.scheduler_snapshot(ctx,result))
        combined=finalize.accept(ctx,result)
        r.write(ctx.control/'COMBINED-CAMPAIGN.json',combined)
        r.write(ctx.control/'COMPUTE-COMPLETE.json',result)
        r.write(ctx.run/'COMPUTE-COMPLETE.json',{'r4_control':str(ctx.control),'completion_sha256':r.sha(ctx.control/'COMPUTE-COMPLETE.json'),
                'combined_campaign_sha256':r.sha(ctx.control/'COMBINED-CAMPAIGN.json'),'successful_unique_tasks':339,'campaign_allocations':340})
    except BaseException as e:
        r.write(ctx.control/'STOP-R4.json',{'error':repr(e)[:4096],'unix':time.time(),'automatic_retry':False,'action':'Preserve; agent-led diagnosis under direct monitoring authority; never blindly restart'})
        raise

if __name__=='__main__':main()
