"""Serial staged Slurm dispatcher; stdlib only, no automatic restart or retry."""
import argparse
import json
from pathlib import Path
import subprocess
import time
import shutil
import candidate_value_contract as ct


def command(*args):return subprocess.check_output(args,universal_newlines=True).strip()


def bytes_used(run):return sum(p.stat().st_size for p in Path(run).rglob('*') if p.is_file())


def copy_evidence(source,destination):
    """Exclusive, verified content copy; no filesystem-owned xattr propagation."""
    with Path(source).open('rb') as src,Path(destination).open('xb') as dst:
        shutil.copyfileobj(src,dst)
    ct.require(ct.sha(source)==ct.sha(destination),'Evidence copy content changed')


def prior_costs(approval):
    prior=ct.json_read(approval).get('prior_allocations',[])
    seen=set();gpu=cpu=0
    for row in prior:
        ct.require(set(row)=={'job','gpu','seconds','state'} and isinstance(row['job'],str)
                   and row['job'].isdigit() and row['job'] not in seen and type(row['gpu']) is bool
                   and type(row['seconds']) is int and row['seconds']>=0 and row['state']=='FAILED',
                   'Invalid approved prior allocation accounting')
        seen.add(row['job'])
        if row['gpu']:gpu+=row['seconds']
        else:cpu+=row['seconds']
    ct.require(gpu<=ct.CAPS['gpu_seconds'] and cpu<=ct.CAPS['cpu_seconds'],'Prior costs exceed cap')
    return prior,gpu,cpu


def sbatch_arguments(spec,source,run,approval,capsule,source_sha):
    seconds=spec['seconds'];kind,index=spec['kind'],spec['index']
    a=['sbatch','--parsable','--account=superworld','--cpus-per-task=4',
       '--mem='+('24G' if spec['gpu'] else '8G'),
       '--time=%02d:%02d:%02d'%(seconds//3600,seconds//60%60,seconds%60),
       '--job-name=candidate-value-'+kind,
       '--output='+str(Path(run)/('slurm-'+kind+'-'+str(index)+'-%j.out')),
       '--error='+str(Path(run)/('slurm-'+kind+'-'+str(index)+'-%j.err'))]
    if spec['gpu']:a+=['--partition=a6000','--qos=normal-a6000','--gres=gpu:1']
    else:a+=['--partition=defq','--qos=normal']
    a += [str(Path(source)/'cluster/prometheus/run_candidate_value.sh'),str(source),str(run),
          str(approval),str(capsule),source_sha,kind,str(index)]
    return a


def launch(source,run,approval,capsule,source_sha):
    ct.authorize(source,run,approval,capsule,source_sha)
    # Charge a conservative reservation for source tar + extracted closure and
    # launch capsule/approval, rather than hiding those outside the artifact cap.
    source_reserve=50000000
    ct.require(2*bytes_used(source)+Path(capsule).stat().st_size+Path(approval).stat().st_size<source_reserve,
               'Source/control package exceeds its 50MB reservation')
    run=Path(run);run.parent.mkdir(parents=True,exist_ok=True);run.mkdir(exist_ok=False)
    prior,used_gpu,used_cpu=prior_costs(approval)
    capsule_sha=ct.sha(capsule);reports=[];jobs=[];backed=set()
    active_job=None
    with (run/'DISPATCH.jsonl').open('x',buffering=1) as log:
        def record(event,**kw):log.write(json.dumps(dict(event=event,utc=time.time(),**kw),sort_keys=True)+'\n')
        if prior:record('prior_allocations_charged',prior_allocations=prior,used_gpu=used_gpu,used_cpu=used_cpu)
        def execute(kind,index):
            nonlocal used_gpu,used_cpu,active_job
            spec=ct.task(kind,index)
            ct.require(ct.reservation(used_gpu,used_cpu,0,0,bytes_used(run)+source_reserve,spec),'Total reservation exhausted')
            record('reserved',task=spec,used_gpu=used_gpu,used_cpu=used_cpu)
            # Ambiguous submission stops here; no second attempt exists.
            active_job='submission_outcome_unknown'
            job=command(*sbatch_arguments(spec,source,run,approval,capsule,source_sha)).split(';')[0]
            ct.require(job.isdigit(),'Ambiguous submission; inspect, never retry')
            active_job=job
            jobs.append(dict(job=job,task=spec));record('submitted',job=job,task=spec)
            while True:
                time.sleep(20)
                job_bytes=bytes_used(run/('%s-%d'%(kind,index)))+bytes_used(run/('tmp-%s-%d'%(kind,index)))
                job_bytes+=sum(p.stat().st_size for p in run.glob('slurm-%s-%d-*'%(kind,index)) if p.is_file())
                if bytes_used(run)+source_reserve>ct.CAPS['storage_bytes'] or job_bytes>ct.CAPS['job_bytes']:
                    command('scancel',job);record('storage_stop_cancelled',job=job,reservation=spec['seconds'])
                    raise RuntimeError('Storage stop; outstanding reservation remains charged')
                response=command('sacct','-X','-n','-P','-j',job,'--format=JobID,State,ExitCode,ElapsedRaw')
                rows=[x.split('|') for x in response.splitlines() if x.split('|')[0]==job]
                ct.require(len(rows)<=1,'Scheduler identity ambiguity')
                if not rows:continue
                _,state,code,seconds=rows[0][:4]
                if state in ('PENDING','RUNNING','CONFIGURING','COMPLETING','SUSPENDED'):continue
                seconds=int(seconds)
                active_job=None
                if spec['gpu']:used_gpu+=seconds
                else:used_cpu+=seconds
                record('terminal',job=job,state=state,exit_code=code,seconds=seconds,
                       used_gpu=used_gpu,used_cpu=used_cpu,bytes=bytes_used(run))
                ct.require(state=='COMPLETED' and code=='0:0','Exact failed job '+job+'; no retry')
                ct.require(used_gpu<=ct.CAPS['gpu_seconds'] and used_cpu<=ct.CAPS['cpu_seconds'],'Allocation cap')
                break
            report=ct.check_report(run/('%s-%d'%(kind,index)),kind,index,source_sha,capsule_sha)
            report=dict(report,allocation_seconds=seconds)
            reports.append(report)
            return report
        def finish(decision):
            summary=dict(decision=decision,jobs=jobs,gpu_seconds=used_gpu,
                cpu_wall_seconds=used_cpu,bytes=bytes_used(run),no_automatic_followup=True,
                prior_allocations=prior)
            terminal=run/'terminal';terminal.mkdir()
            ct.json_write(terminal/'REPORT.json',summary)
            copy_evidence(capsule,terminal/'LAUNCH-CAPSULE.json')
            copy_evidence(approval,terminal/'APPROVAL.json')
            copy_evidence(Path(source)/'SOURCE-MANIFEST.sha256',terminal/'SOURCE-MANIFEST.sha256')
            for p in run.iterdir():
                if p.is_file():copy_evidence(p,terminal/p.name)
            ct.require(bytes_used(run)+source_reserve<=ct.CAPS['storage_bytes'],'Terminal artifact cap')
            ct.seal(terminal)
            new=[p.name for p in run.iterdir() if p.is_dir() and (p/'sha256.txt').exists() and p.name not in backed]
            backup('terminal',sorted(new))
            ct.json_write(run/'DISPATCH-FINAL.json',summary)
        def backup(stage,directories):
            request=dict(stage=stage,source_sha256=source_sha,run=str(run),directories=directories,
                         seals={d:ct.sha(run/d/'sha256.txt') for d in directories})
            ct.json_write(run/('BACKUP-REQUEST-'+stage+'.json'),request)
            ack=run/('BACKUP-ACK-'+stage+'.json')
            # This waits on the separately started external-SSD companion, with no GPU allocated.
            deadline=time.monotonic()+3600
            while not ack.exists():
                ct.require(time.monotonic()<deadline,'Backup acknowledgement timeout; stop, no retry')
                time.sleep(20)
            receipt=ct.json_read(ack)
            ct.require(receipt.get('verified') is True and receipt.get('request_sha256')==
                       ct.sha(run/('BACKUP-REQUEST-'+stage+'.json')),'External backup acknowledgement')
            record('backup_verified',stage=stage,archive_sha256=receipt['archive_sha256'])
            backed.update(directories)
        ready=Path(approval).with_name('BACKUP-READY.json')
        readiness=ct.json_read(ready)
        ct.require(readiness.get('external_mount')=='/mnt/d' and readiness.get('free_bytes',0)>=ct.CAPS['backup_free_bytes']
                   and readiness.get('source_sha256')==source_sha and
                   0<=time.time()-readiness.get('utc',0)<3600,'Fresh external SSD readiness required')
        try:
            for i in range(2):execute('preflight',i)
            for i in range(8):execute('train',i)
            pilot=[r for r in reports if r['kind']=='train']
            ct.require(max(r['maxrss_bytes'] for r in pilot)<=16*(1<<30),'Pilot host memory')
            ct.require(max(r['allocation_seconds'] for r in pilot)<=600 and
                       sum(r['bytes_before_report'] for r in pilot)/8*256<ct.CAPS['storage_bytes']*.8,
                       'Pilot resource projection; do not change cases or caps')
            record('technical_pilot_passed',references=ct.allocation()['train'][:4])
            for i in range(8,192):execute('train',i)
            backup('train',['preflight-0','preflight-1']+['train-%d'%i for i in range(192)])
            if not execute('fit',0)['advance']:finish('insufficient_success_support');return
            for i in range(64):execute('validation',i)
            backup('validation',['fit-0']+['validation-%d'%i for i in range(64)])
            if not execute('validate',0)['advance']:finish('stop_no_ranking_promise');return
            for i in range(32):execute('closed',i)
            backup('closed',['validate-0']+['closed-%d'%i for i in range(32)])
            execute('report',0)
            backup('report',['report-0'])
            finish('completed_development_only')
        except BaseException as exc:
            record('dispatch_stopped',error_type=type(exc).__name__,message=str(exc),active_job=active_job)
            # Never seal a possibly live allocation or silently resubmit it.
            # Completed/failed partial outputs get an integrity seal, NOT a
            # scientifically valid REPORT. Existing bytes are not overwritten.
            if active_job is None and not (run/'terminal').exists():
                for p in run.iterdir():
                    if p.is_dir() and not (p/'sha256.txt').exists() and any(x.is_file() for x in p.rglob('*')):
                        ct.seal(p)
                finish('stopped_preserved_no_retry')
            raise


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('source','run','approval','capsule','source-sha'):p.add_argument('--'+n,required=True)
    a=p.parse_args();launch(a.source,a.run,a.approval,a.capsule,a.source_sha)
