"""Serial339, write-ahead allocation ledger, no automatic recovery/retry."""
import common as c
import argparse
import math
import os
from pathlib import Path
import subprocess
import time
import recovery


def storage(source, run, jobs):
    sizes = {j['key']:sum(f.stat().st_size for f in (run/j['key']).rglob('*') if f.is_file()) for j in jobs}
    for j in jobs: c.require(sizes[j['key']]<=j['byte_cap'], 'Worker byte cap: '+j['key'])
    # Full remaining outputs are reserved, not merely already-written bytes.
    gpu_outputs = sum(j['byte_cap'] for j in jobs if j['gpu'])
    control = sum(f.stat().st_size for f in run.glob('*') if f.is_file())
    source_bytes = sum((c.REPO/name).stat().st_size for name in c.read(source/'SOURCE-MANIFEST.json')['files'])
    source_bytes += (source/'SOURCE-MANIFEST.json').stat().st_size+(source/'APPROVAL-TEMPLATE.json').stat().st_size
    binding=recovery.approval_binding(c.sha(source/'SOURCE-MANIFEST.json'))
    external_control=sum(f.stat().st_size for f in Path(binding['control']).rglob('*') if f.is_file())
    old_original_bytes=sum(path.stat().st_size for _,path,_ in recovery.prior_paths())
    old_copied_bytes=sum(f.stat().st_size for f in (run/'provenance-failed-v2').rglob('*') if f.is_file())
    other = control + source_bytes + external_control + old_original_bytes + old_copied_bytes + sum(sizes[j['key']] for j in jobs if not j['gpu'])
    c.require(other<=500_000_000,'Source/model/control/analysis500MB')
    reserved_live = gpu_outputs + 500_000_000
    c.require(reserved_live<=2_000_000_000,'Full future live reservation')
    # 3 copies: live+uncompressed tar+partial; fourth reserve covers headers/logs.
    c.require(4*reserved_live<=8_000_000_000,'Live/archive/partial reservation')
    return {'current_worker_bytes':sum(sizes.values()),'full_live_reservation':reserved_live,
            'inclusive_reservation':4*reserved_live,'source_control_models_analysis':other,
            'old_original_bytes':old_original_bytes,'old_provenance_copy_bytes':old_copied_bytes,'external_control_bytes':external_control}


def execute(jobs, scheduler, record, check, gate, bytes_check):
    completed=[]; gpu=23;cpu=0; ids={'304189'};keys=set();submitted_count=0;replacement_count=0
    c.require(len(jobs)==339 and jobs==c.grid(),'Exact R1 grid only')
    for i,j in enumerate(jobs):
        c.require(j['key'] not in keys,'Duplicate scientific task');keys.add(j['key'])
        bytes_check()
        c.require(gpu+sum(k['seconds'] for k in jobs[i:] if k['gpu'])<=220800, 'Remaining GPU reservation')
        c.require(cpu+sum(k['seconds'] for k in jobs[i:] if not k['gpu'])<=21600, 'Remaining CPU reservation')
        if i==2: gate('technical',completed)
        if i==82: gate('models',completed)
        if j['stage']=='analysis': gate('analysis',completed)
        attempt=2 if j['key']=='collect-fit-490' else 1
        record({'event':'claim','spec':j,'reserved_seconds':j['seconds'],'attempt':attempt,
                'campaign_gpu_seconds':gpu,'remaining_gpu_reservation':sum(k['seconds'] for k in jobs[i:] if k['gpu'])})
        try: job=scheduler.submit(j)
        except BaseException as e:
            record({'event':'submission_unresolved','spec':j,'reservation_retained':j['seconds'],'error':str(e)})
            raise
        c.require(job not in ids,'Duplicate scheduler ID');ids.add(job)
        submitted_count+=1
        if attempt==2:replacement_count+=1
        c.require(submitted_count<=339 and replacement_count<=1,'Finite attempt envelope')
        record({'event':'submitted','spec':j,'job':job,'attempt':attempt,
                'authorized_replacement_count':replacement_count,'automatic_retry_count':0})
        try:terminal=scheduler.wait(job,j)
        except BaseException as e:
            record({'event':'observation_unresolved','spec':j,'job':job,'reservation_retained':j['seconds'],'error':str(e)})
            raise
        seconds=int(terminal['seconds']);c.require(seconds>=0,'Negative charge')
        if j['gpu']:gpu+=seconds*int(terminal.get('gpus',1))
        else:cpu+=seconds
        row={'event':'terminal','spec':j,'job':job,'attempt':attempt,**terminal,'gpu_seconds':gpu,'cpu_seconds':cpu}
        record(row); completed.append(row)  # failures charged BEFORE failure check
        c.require(seconds<=j['seconds'] and terminal['state']=='COMPLETED' and terminal['exit_code']=='0:0', 'Fail-stop: no automatic retry')
        c.require(int(terminal.get('allocated_cpus',4))==4 and int(terminal.get('gpus',j['gpu']))==j['gpu'],'Unexpected actual allocation resources')
        check(j)
        record({'event':'scientific_task_accepted','key':j['key'],'job':job,'attempt':attempt})
    return {'jobs':completed,'gpu_seconds':gpu,'r1_gpu_seconds':gpu-23,'cpu_seconds':cpu,
            'prior_failed_gpu_seconds':23,'prior_failed_attempts':1,'new_attempts':submitted_count,
            'campaign_attempts':submitted_count+1,'successful_unique_tasks':len(completed),
            'authorized_replacement_count':replacement_count,'automatic_retry_count':0}


class Slurm:
    def __init__(self,auth,approval):self.auth=auth;self.approval=approval
    def submit(self,j):
        run=self.auth.run
        args=['sbatch','--parsable','--no-requeue','--account=superworld','--cpus-per-task=4',
              '--mem='+('24G' if j['gpu'] else '8G'),'--time='+str(math.ceil(j['seconds']/60)),
              '--partition='+('a6000' if j['gpu'] else 'defq'),'--qos='+('normal-a6000' if j['gpu'] else 'normal'),
              '--job-name=acv0r1-'+j['key'],'--output='+str(run/(j['key']+'-%j.out')),
              '--error='+str(run/(j['key']+'-%j.err'))]
        if j['gpu']:args+=['--gres=gpu:1']
        args += [str(c.ROOT/'run_worker.sh'), str(c.ROOT),str(self.approval),str(run),j['key'],str(j['gpu'])]
        p=subprocess.run(args,capture_output=True,text=True,timeout=60)
        c.require(p.returncode==0 and p.stdout.strip().split(';')[0].isdigit(), 'Ambiguous submission: '+p.stderr)
        return p.stdout.strip().split(';')[0]

    def wait(self,job,spec):
        while True:
            # A query failure is unresolved, never authority to resubmit.
            p=subprocess.run(['sacct','-X','-n','-P','-j',job,'--format=JobIDRaw,State,ExitCode,ElapsedRaw,AllocCPUS,AllocTRES,NodeList'],capture_output=True,text=True,timeout=60)
            c.require(p.returncode==0,'Scheduler observation unavailable: '+p.stderr)
            rows=[line.split('|') for line in p.stdout.splitlines() if line.split('|')[0]==job]
            c.require(len(rows)<=1,'Ambiguous scheduler rows')
            if rows:
                r=rows[0];state=r[1].split()[0]
                if state not in ('PENDING','RUNNING','CONFIGURING','COMPLETING'):
                    tres=dict(v.split('=',1) for v in r[5].split(',') if '=' in v)
                    return {'state':state,'exit_code':r[2],'seconds':int(r[3]),'allocated_cpus':r[4],'allocated_tres':r[5],
                            'gpus':int(tres.get('gres/gpu',0)),'node':r[6]}
            time.sleep(15)


def main():
    p=argparse.ArgumentParser();p.add_argument('--approval',required=True);p.add_argument('--run',required=True);a=p.parse_args()
    auth=c.Authorization(a.approval,a.run)  # BEFORE scheduler commands or research opens
    from controller_runtime import verify
    verify()
    jobs=c.grid(); run=auth.run
    c.require(not run.exists(),'Existing run; no restart/resumption')
    reconciliation=recovery.reconcile()
    auth.runtime()
    run.mkdir(parents=True,exist_ok=False);c.write(run/'APPROVAL.json',auth.approval)
    c.write(run/'CONTROLLER.json',{'pid':os.getpid(),'start_ticks':Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19], 'package':auth.approval['package_sha256']})
    c.write(run/'PRIOR-RECONCILIATION.json',reconciliation)
    recovery.copy_prior(run)
    recovery.append(run/'CAMPAIGN-ATTEMPTS.jsonl',recovery.historical_event())
    def record(row):
        row['time']=time.time()
        recovery.append(run/'DISPATCH.jsonl',row)
        recovery.append(run/'CAMPAIGN-ATTEMPTS.jsonl',row)
        if row['event']=='scientific_task_accepted':
            recovery.append(run/'SCIENTIFIC-TASKS.jsonl',dict(row,seal_sha256=c.sha(run/row['key']/'SEAL.json')))
    def check(j):
        s=c.verify_seal(run/j['key'],j)
        tech=c.read(run/j['key']/'TECHNICAL.json')
        c.require(tech['passed'] is True and tech['package']==auth.approval['package_sha256'] and tech['approval']==auth.approval_sha,'Technical identity')
        if j['gpu']:
            from hardware import EXPECTED_DEVICE
            h=c.read(run/j['key']/'HARDWARE.json')
            rows=[c.json.loads(line) for line in (run/'DISPATCH.jsonl').read_text().splitlines()]
            terminal=[r for r in rows if r['event']=='terminal' and r['spec']['key']==j['key']]
            c.require(len(terminal)==1 and h['slurm_job_id']==terminal[0]['job'] and h['hostname']==terminal[0]['node'],'Hardware allocation identity')
            c.require(h['accepted'] and h['query_status']=='complete' and h['device_name']==EXPECTED_DEVICE and h['visible_device_count']==1 and h['cuda_available'] is True,'Hardware gate')
            c.require(tech['hardware']==h,'Hardware receipt/technical equality')
        return s
    def gate(name,rows):
        if name=='technical':
            c.require([r['spec']['reference'] for r in rows]==[490,545], 'Included first two sources')
            for j in jobs[:2]:check(j)
            c.write(run/'TECHNICAL-TRANCHE-PASSED.json',{'seals':{j['key']:c.sha(run/j['key']/'SEAL.json') for j in jobs[:2]},'scientific_selection':False})
        elif name=='models':
            from model_seal import model_freeze
            model_freeze(run,auth.approval['package_sha256'])
        else:c.write(run/'PRE-ANALYSIS-ACCOUNTING.json',{'jobs':rows})
    try:
        result=execute(jobs,Slurm(auth,Path(a.approval).resolve()),record,check,gate,lambda:storage(c.ROOT,run,jobs))
        result['storage']=storage(c.ROOT,run,jobs)
        result['campaign_accounting']=recovery.final_acceptance(run,result)
        c.write(run/'COMPUTE-COMPLETE.json',result)
    except BaseException as e:
        c.write(run/'STOP.json',{'error':repr(e),'automatic_retry':False,'action':'Preserve evidence and reconcile exact allocations; explicit recovery required'})
        raise


if __name__=='__main__':main()
