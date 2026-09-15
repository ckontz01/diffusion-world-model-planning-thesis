"""Serial staged Slurm dispatcher; stdlib only, no automatic restart or retry."""
import argparse
import json
from pathlib import Path
import subprocess
import time
import shutil
import os
import stat
import candidate_value_contract as ct


def command(*args):return subprocess.check_output(args,universal_newlines=True).strip()


def file_bytes(paths):
    total=0
    for p in paths:
        try:info=Path(p).stat()
        except FileNotFoundError:continue  # Concurrently removed temporary file.
        if stat.S_ISREG(info.st_mode):total+=info.st_size
    return total


def bytes_used(run):
    def onerror(exc):
        if not isinstance(exc,FileNotFoundError):raise exc
    return sum(file_bytes(Path(root)/name for name in names)
               for root,dirs,names in os.walk(str(run),onerror=onerror))


def technical_report(directory):
    """Authenticate all bytes; decode only top-level technical scalar fields."""
    p=Path(directory);names=set()
    for line in (p/'sha256.txt').read_text().splitlines():
        expected,name=line.split('  ',1)
        ct.require(name not in names and ct.sha(ct.child(p,name))==expected,'Resume output checksum')
        names.add(name)
    ct.require(names=={x.relative_to(p).as_posix() for x in p.rglob('*')
                      if x.is_file() and x.name!='sha256.txt'} and names,'Resume unsealed files')
    keys={'kind','index','source_sha256','capsule_sha256','technical_valid',
          'protected_payload_reads','historical_decisions_changed','maxrss_bytes',
          'bytes_before_report','reference','h'}
    out={}
    for line in (p/'REPORT.json').read_text().splitlines():
        if not line.startswith('  "'):continue
        key=line.split('"',2)[1]
        if key in keys:
            ct.require(key not in out,'Duplicate technical scalar')
            out[key]=json.loads('{'+line.strip().rstrip(',')+'}')[key]
    return out


def resume_state(source,run,approval,capsule,source_sha,receipt,receipt_sha):
    """One authorized train-81 continuation; no failed/scientific-stop recovery."""
    ct.require(ct.sha(receipt)==receipt_sha,'Resume approval hash')
    r=ct.json_read(receipt);run=Path(run)
    ct.require(r['researcher_approved'] is True and r['next_train_index']==81 and
               r['controller_sha256']==ct.sha(__file__) and r['run']==str(run) and
               r['source_sha256']==source_sha and r['capsule_sha256']==ct.sha(capsule) and
               r['approval_sha256']==ct.sha(approval) and r['caps']==ct.CAPS and
               r['protocol_sha256']==ct.sha(Path(source)/ct.DOC),'Resume approval scope')
    ct.require(ct.sha(run/'DISPATCH.jsonl')==r['dispatch_sha256'],'Original dispatch changed')
    events=[json.loads(x) for x in (run/'DISPATCH.jsonl').read_text().splitlines()]
    stop=events[-1]
    ct.require(stop['event']=='dispatch_stopped' and stop['error_type']=='FileNotFoundError'
               and stop['active_job']=='301256' and 'tmp-train-80/' in stop['message'],
               'Not the authorized storage race')
    submitted=[e for e in events if e['event']=='submitted']
    expected=[ct.task('preflight',i) for i in range(2)]+[ct.task('train',i) for i in range(81)]
    ct.require([e['task'] for e in submitted]==expected,'Resume prefix is not exact')
    ct.require(len({e['job'] for e in submitted})==83,'Duplicate historical allocation')
    ct.require(any(e['event']=='technical_pilot_passed' for e in events),'Missing pilot gate')
    rows=r['completed'];ct.require(len(rows)==83,'Missing completed jobs')
    observed={}
    response=command('sacct','-X','-n','-P','-j',','.join(e['job'] for e in submitted),
                     '--format=JobID,State,ExitCode,ElapsedRaw')
    for line in response.splitlines():
        job,state,exit_code,seconds=line.split('|')[:4]
        ct.require(job not in observed,'Duplicate scheduler row')
        observed[job]=(state,exit_code,int(seconds))
    ct.require(set(observed)=={e['job'] for e in submitted},'Missing/extra scheduler identity')
    prior,gpu,cpu=prior_costs(approval);jobs=[]
    terminals={e['job']:e for e in events if e['event']=='terminal'}
    ct.require(set(terminals)=={e['job'] for e in submitted[:-1]},'Unexpected original terminals')
    expected_dirs=set()
    for e,spec,row in zip(submitted,expected,rows):
        job=e['job'];d='%s-%d'%(spec['kind'],spec['index']);expected_dirs.add(d)
        ct.require(row['job']==job and row['task']==spec and type(row['seconds']) is int
                   and 0<=row['seconds']<=spec['seconds'] and
                   observed[job]==('COMPLETED','0:0',row['seconds']),'Historical worker not completed')
        if job in terminals:
            old=terminals[job]
            ct.require((old['state'],old['exit_code'],old['seconds'])==observed[job],
                       'Historical accounting changed')
        ct.require(ct.sha(run/d/'sha256.txt')==row['seal_sha256'],'Historical seal changed')
        meta=technical_report(run/d)
        ct.require((meta['kind'],meta['index'],meta['source_sha256'],meta['capsule_sha256'])==
                   (spec['kind'],spec['index'],source_sha,ct.sha(capsule)) and
                   meta['technical_valid'] is True and meta['protected_payload_reads']==0 and
                   meta['historical_decisions_changed'] is False,'Historical technical identity')
        gpu+=row['seconds'];jobs.append(dict(job=job,task=spec))
    ct.require(gpu==r['gpu_seconds']==17151 and cpu==r['cpu_seconds']==0,'Resume cumulative cost')
    ct.require({p.parent.name for p in run.glob('*/sha256.txt')}==expected_dirs,'Unexpected completed stage')
    for spec in ct.grid():
        d='%s-%d'%(spec['kind'],spec['index'])
        if d not in expected_dirs:
            ct.require(not (run/d).exists() and not (run/('tmp-'+d)).exists()
                       and not list(run.glob('slurm-'+d+'-*')),'Unaccounted later task')
    ct.require(not (run/'terminal').exists() and not (run/'DISPATCH-FINAL.json').exists()
               and not list(run.glob('BACKUP-REQUEST-*')),'Unexpected stage/terminal decision')
    return prior,gpu,cpu,jobs


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


def launch(source,run,approval,capsule,source_sha,resume=None,resume_sha=None):
    ct.authorize(source,run,approval,capsule,source_sha)
    # Charge a conservative reservation for source tar + extracted closure and
    # launch capsule/approval, rather than hiding those outside the artifact cap.
    source_reserve=50000000
    ct.require(2*bytes_used(source)+Path(capsule).stat().st_size+Path(approval).stat().st_size<source_reserve,
               'Source/control package exceeds its 50MB reservation')
    run=Path(run);jobs=[]
    if resume:
        prior,used_gpu,used_cpu,jobs=resume_state(source,run,approval,capsule,source_sha,resume,resume_sha)
        ct.require(bytes_used(Path(resume).parent)+2*bytes_used(source)<source_reserve,'Control/source reservation')
        ct.json_write(run/'RESUME-CLAIM.json',dict(approval_sha256=resume_sha,controller_sha256=ct.sha(__file__)))
    else:
        run.parent.mkdir(parents=True,exist_ok=True);run.mkdir(exist_ok=False)
        prior,used_gpu,used_cpu=prior_costs(approval)
    capsule_sha=ct.sha(capsule);reports=[];backed=set()
    active_job=None
    with (run/('DISPATCH-RESUME.jsonl' if resume else 'DISPATCH.jsonl')).open('x',buffering=1) as log:
        def record(event,**kw):log.write(json.dumps(dict(event=event,utc=time.time(),**kw),sort_keys=True)+'\n')
        if prior:record('prior_allocations_charged',prior_allocations=prior,used_gpu=used_gpu,used_cpu=used_cpu)
        if resume:record('authorized_continuation',next_train_index=81,completed_jobs=jobs,
                         approval_sha256=resume_sha,used_gpu=used_gpu,used_cpu=used_cpu)
        def execute(kind,index):
            nonlocal used_gpu,used_cpu,active_job
            spec=ct.task(kind,index)
            ct.require(not any(j['task']==spec for j in jobs),'Refuse completed task resubmission')
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
                job_bytes+=file_bytes(run.glob('slurm-%s-%d-*'%(kind,index)))
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
            if resume:
                copy_evidence(resume,terminal/'RESUME-APPROVAL.json')
                copy_evidence(__file__,terminal/'RESUME-CONTROLLER.py')
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
        ready=Path(resume or approval).with_name('BACKUP-READY.json')
        readiness=ct.json_read(ready)
        ct.require(readiness.get('external_mount')=='/mnt/d' and readiness.get('free_bytes',0)>=ct.CAPS['backup_free_bytes']
                   and readiness.get('source_sha256')==source_sha and
                   0<=time.time()-readiness.get('utc',0)<3600,'Fresh external SSD readiness required')
        try:
            if not resume:
                for i in range(2):execute('preflight',i)
                for i in range(8):execute('train',i)
                pilot=[r for r in reports if r['kind']=='train']
                ct.require(max(r['maxrss_bytes'] for r in pilot)<=16*(1<<30),'Pilot host memory')
                ct.require(max(r['allocation_seconds'] for r in pilot)<=600 and
                           sum(r['bytes_before_report'] for r in pilot)/8*256<ct.CAPS['storage_bytes']*.8,
                           'Pilot resource projection; do not change cases or caps')
                record('technical_pilot_passed',references=ct.allocation()['train'][:4])
            for i in range(81 if resume else 8,192):execute('train',i)
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
    p.add_argument('--resume');p.add_argument('--resume-sha')
    a=p.parse_args();launch(a.source,a.run,a.approval,a.capsule,a.source_sha,a.resume,a.resume_sha)
