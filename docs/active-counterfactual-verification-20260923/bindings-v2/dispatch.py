"""Serial339, write-ahead allocation ledger, no automatic recovery/retry."""
import common as c
import argparse
import math
import os
from pathlib import Path
import subprocess
import time


def storage(source, run, jobs):
    sizes = {j['key']:sum(f.stat().st_size for f in (run/j['key']).rglob('*') if f.is_file()) for j in jobs}
    for j in jobs: c.require(sizes[j['key']]<=j['byte_cap'], 'Worker byte cap: '+j['key'])
    # Full remaining outputs are reserved, not merely already-written bytes.
    gpu_outputs = sum(j['byte_cap'] for j in jobs if j['gpu'])
    control = sum(f.stat().st_size for f in run.glob('*') if f.is_file())
    source_bytes = sum((c.REPO/name).stat().st_size for name in c.read(source/'SOURCE-MANIFEST.json')['files'])
    source_bytes += (source/'SOURCE-MANIFEST.json').stat().st_size+(source/'APPROVAL-TEMPLATE.json').stat().st_size
    other = control + source_bytes + sum(sizes[j['key']] for j in jobs if not j['gpu'])
    c.require(other<=500_000_000,'Source/model/control/analysis500MB')
    reserved_live = gpu_outputs + 500_000_000
    c.require(reserved_live<=2_000_000_000,'Full future live reservation')
    # 3 copies: live+uncompressed tar+partial; fourth reserve covers headers/logs.
    c.require(4*reserved_live<=8_000_000_000,'Live/archive/partial reservation')
    return {'current_worker_bytes':sum(sizes.values()),'full_live_reservation':reserved_live,
            'inclusive_reservation':4*reserved_live,'source_control_models_analysis':other}


def execute(jobs, scheduler, record, check, gate, bytes_check):
    completed=[]; gpu=cpu=0; ids=set()
    for i,j in enumerate(jobs):
        bytes_check()
        c.require(gpu+sum(k['seconds'] for k in jobs[i:] if k['gpu'])<=220800, 'Remaining GPU reservation')
        c.require(cpu+sum(k['seconds'] for k in jobs[i:] if not k['gpu'])<=21600, 'Remaining CPU reservation')
        if i==2: gate('technical',completed)
        if i==82: gate('models',completed)
        if j['stage']=='analysis': gate('analysis',completed)
        record({'event':'claim','spec':j,'reserved_seconds':j['seconds'],'attempt':1})
        try: job=scheduler.submit(j)
        except BaseException as e:
            record({'event':'submission_unresolved','spec':j,'reservation_retained':j['seconds'],'error':str(e)})
            raise
        c.require(job not in ids,'Duplicate scheduler ID');ids.add(job)
        record({'event':'submitted','spec':j,'job':job})
        try:terminal=scheduler.wait(job,j)
        except BaseException as e:
            record({'event':'observation_unresolved','spec':j,'job':job,'reservation_retained':j['seconds'],'error':str(e)})
            raise
        seconds=int(terminal['seconds']);c.require(seconds>=0,'Negative charge')
        if j['gpu']:gpu+=seconds*int(terminal.get('gpus',1))
        else:cpu+=seconds
        row={'event':'terminal','spec':j,'job':job,**terminal,'gpu_seconds':gpu,'cpu_seconds':cpu}
        record(row); completed.append(row)  # failures charged BEFORE failure check
        c.require(seconds<=j['seconds'] and terminal['state']=='COMPLETED' and terminal['exit_code']=='0:0', 'Fail-stop: no automatic retry')
        c.require(int(terminal.get('allocated_cpus',4))==4 and int(terminal.get('gpus',j['gpu']))==j['gpu'],'Unexpected actual allocation resources')
        check(j)
    return {'jobs':completed,'gpu_seconds':gpu,'cpu_seconds':cpu,'attempts':len(completed),'retry_count':0}


class Slurm:
    def __init__(self,auth,approval):self.auth=auth;self.approval=approval
    def submit(self,j):
        run=self.auth.run
        args=['sbatch','--parsable','--no-requeue','--account=superworld','--cpus-per-task=4',
              '--mem='+('24G' if j['gpu'] else '8G'),'--time='+str(math.ceil(j['seconds']/60)),
              '--partition='+('a6000' if j['gpu'] else 'defq'),'--qos='+('normal-a6000' if j['gpu'] else 'normal'),
              '--job-name=acv0b1-'+j['key'],'--output='+str(run/(j['key']+'-%j.out')),
              '--error='+str(run/(j['key']+'-%j.err'))]
        if j['gpu']:args+=['--gres=gpu:1']
        args += [str(c.ROOT/'run_worker.sh'), str(c.ROOT),str(self.approval),str(run),j['key'],str(j['gpu'])]
        p=subprocess.run(args,capture_output=True,text=True,timeout=60)
        c.require(p.returncode==0 and p.stdout.strip().split(';')[0].isdigit(), 'Ambiguous submission: '+p.stderr)
        return p.stdout.strip().split(';')[0]

    def wait(self,job,spec):
        while True:
            # A query failure is unresolved, never authority to resubmit.
            p=subprocess.run(['sacct','-X','-n','-P','-j',job,'--format=JobIDRaw,State,ExitCode,ElapsedRaw,AllocCPUS,AllocTRES'],capture_output=True,text=True,timeout=60)
            c.require(p.returncode==0,'Scheduler observation unavailable: '+p.stderr)
            rows=[line.split('|') for line in p.stdout.splitlines() if line.split('|')[0]==job]
            c.require(len(rows)<=1,'Ambiguous scheduler rows')
            if rows:
                r=rows[0];state=r[1].split()[0]
                if state not in ('PENDING','RUNNING','CONFIGURING','COMPLETING'):
                    tres=dict(v.split('=',1) for v in r[5].split(',') if '=' in v)
                    return {'state':state,'exit_code':r[2],'seconds':int(r[3]),'allocated_cpus':r[4],'allocated_tres':r[5],
                            'gpus':int(tres.get('gres/gpu',0))}
            time.sleep(15)


def main():
    p=argparse.ArgumentParser();p.add_argument('--approval',required=True);p.add_argument('--run',required=True);a=p.parse_args()
    auth=c.Authorization(a.approval,a.run)  # BEFORE scheduler commands or research opens
    from controller_runtime import verify
    verify()
    jobs=c.grid(); run=auth.run
    c.require(not run.exists(),'Existing run; no restart/resumption')
    old=subprocess.run(['sacct','-X','-n','-P','--starttime=2026-09-23','--format=JobName%100'],text=True,capture_output=True,timeout=60)
    c.require(old.returncode==0 and not any(s.startswith('acv0b1-') for s in old.stdout.splitlines()),'Prior/ambiguous namespace allocations')
    auth.runtime()
    run.mkdir(parents=True,exist_ok=False);c.write(run/'APPROVAL.json',auth.approval)
    c.write(run/'CONTROLLER.json',{'pid':os.getpid(),'start_ticks':Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19], 'package':auth.approval['package_sha256']})
    def record(row):
        with (run/'DISPATCH.jsonl').open('ab') as f:
            f.write(c.canonical(dict(row,time=time.time()))+b'\n');f.flush();os.fsync(f.fileno())
    def check(j):
        s=c.verify_seal(run/j['key'],j)
        tech=c.read(run/j['key']/'TECHNICAL.json')
        c.require(tech['passed'] is True and tech['package']==auth.approval['package_sha256'] and tech['approval']==auth.approval_sha,'Technical identity')
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
        c.write(run/'COMPUTE-COMPLETE.json',result)
    except BaseException as e:
        c.write(run/'STOP.json',{'error':repr(e),'automatic_retry':False,'action':'Preserve evidence and reconcile exact allocations; explicit recovery required'})
        raise


if __name__=='__main__':main()
