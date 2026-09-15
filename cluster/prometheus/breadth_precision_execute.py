"""Future guarded worker/serial dispatch. Nothing runs without separate approval."""
import argparse
import json
import os
from pathlib import Path
import resource
import subprocess
import time
import breadth_precision_contract as p
import candidate_value_contract as ct


def worker(source,run,approval,kind,index):
    a,manifest=p.authorize(source,run,approval);spec=p.task(kind,index)
    p.require(os.environ.get('SLURM_JOB_ID'),'Slurm-only worker')
    import torch
    torch.set_num_threads(4);torch.set_num_interop_threads(1)
    from breadth_precision_learning import train,analyze,check_frozen
    from breadth_precision_data import collect,record,original
    if kind=='evaluation':check_frozen(run,a['source_sha256'])
    out=Path(run)/('%s-%d'%(kind,index));out.mkdir(exist_ok=False);began=time.monotonic()
    try:
        if spec['gpu']:
            from candidate_value_runtime import RealBackend
            backend=RealBackend()
            role=dict(breadth='extra_train',precision='original_train',evaluation='evaluation')[kind]
            rec,seed=record(manifest,spec['reference'],spec['h'],role)
            prior=original(spec['reference'],spec['h'],True) if kind=='precision' else None
            report=collect(backend,rec,seed,spec['reference'],spec['h'],kind,out,prior)
            report.update(gpu_peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                          gpu_peak_reserved_bytes=torch.cuda.max_memory_reserved())
        elif kind=='fit':report=train(run,out,a['source_sha256'])
        elif kind=='analyze':report=analyze(run,out,a['source_sha256'])
        else:raise RuntimeError('Unregistered worker')
        size=sum(x.stat().st_size for x in out.rglob('*') if x.is_file())
        p.require(size<p.CAPS['job_bytes'] and time.monotonic()-began<=spec['seconds'],'Per-allocation cap')
        report.update(kind=kind,index=index,new_source_sha256=a['source_sha256'],source_sha256=a['source_sha256'],
            capsule_sha256=p.OLD_CAPSULE_SHA,technical_valid=True,protected_payload_reads=0,
            historical_decisions_changed=False,maxrss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            bytes_before_report=size,worker_seconds=time.monotonic()-began,process_cpu_seconds=time.process_time())
        ct.json_write(out/'REPORT.json',report);ct.seal(out)
    except BaseException as exc:
        ct.json_write(out/'TECHNICAL-FAILURE.json',dict(type=type(exc).__name__,message=str(exc),
            scientific_outputs_valid=False,wall_seconds=time.monotonic()-began))
        raise


def arguments(task,source,run,approval):
    cmd=['sbatch','--parsable','--account=superworld','--cpus-per-task=4',
         '--mem=24G' if task['gpu'] else '--mem=8G','--time=%d'%((task['seconds']+59)//60),
         '--output='+str(Path(run)/('slurm-%s-%d-%%j.out'%(task['kind'],task['index']))),
         '--error='+str(Path(run)/('slurm-%s-%d-%%j.err'%(task['kind'],task['index'])))]
    cmd+=['--partition=a6000','--qos=normal-a6000','--gres=gpu:1'] if task['gpu'] else ['--partition=defq','--qos=normal']
    return cmd+[str(Path(source)/'cluster/prometheus/run_breadth_precision.sh'),str(source),str(run),str(approval),task['kind'],str(task['index'])]


def command(*args):return subprocess.check_output(args,universal_newlines=True).strip()


def dispatch(source,run,approval):
    a,_=p.authorize(source,run,approval)
    from breadth_precision_infra import bytes_used,technical_report,file_bytes
    p.require(2*bytes_used(Path(source))+Path(approval).stat().st_size<p.CAPS['source_bytes'],'Source/control reservation')
    run=Path(run);ready=ct.json_read(Path(approval).with_name('BACKUP-READY.json'))
    p.require(ready['external_mount']=='/mnt/d' and ready['free_bytes']>=p.CAPS['backup_free_bytes'] and
              ready['source_sha256']==a['source_sha256'] and 0<=time.time()-ready['utc']<3600,'Fresh external SSD readiness')
    run.mkdir(parents=True,exist_ok=False);gpu=cpu=0;jobs=[];backed=set();active=None;tranche=[]
    def event(name,**kw):
        with (run/'DISPATCH.jsonl').open('a') as f:f.write(json.dumps(dict(event=name,utc=time.time(),**kw))+'\n')
    def backup(stage):
        dirs=sorted(d.name for d in run.iterdir() if d.is_dir() and (d/'sha256.txt').is_file() and d.name not in backed)
        request=dict(stage=stage,run=str(run),directories=dirs,source_sha256=a['source_sha256'],
                     seals={d:p.sha(run/d/'sha256.txt') for d in dirs})
        req=run/('BACKUP-REQUEST-'+stage+'.json');ct.json_write(req,request);deadline=time.monotonic()+3600
        ack=run/('BACKUP-ACK-'+stage+'.json')
        while not ack.exists():
            p.require(time.monotonic()<deadline,'Backup timeout; no retry');time.sleep(20)
        receipt=ct.json_read(ack)
        p.require(receipt['verified'] and receipt['request_sha256']==p.sha(req),'Exact external backup acknowledgement')
        backed.update(dirs);event('backup_verified',stage=stage,archive_sha256=receipt['archive_sha256'])
    try:
        fixed=p.grid()
        for pos,spec in enumerate(fixed):
            p.require(p.reservation(gpu,cpu,bytes_used(run),fixed[pos:]),'Whole remaining workload reservation cannot fit')
            if spec['kind']=='fit':backup('train')
            if spec['kind']=='evaluation' and spec['index']==0:
                from breadth_precision_learning import check_frozen
                check_frozen(run,a['source_sha256']);backup('models')
            if spec['kind']=='analyze':backup('evaluation')
            cmd=arguments(spec,source,run,approval)
            event('reservation',task=spec,command=cmd)
            active='submission_outcome_unknown'
            job=command(*cmd).split(';')[0]
            p.require(job.isdigit(),'Ambiguous submission; stop, never retry')
            active=job;jobs.append(dict(job=job,task=spec));event('submitted',job=job,task=spec)
            while True:
                time.sleep(20)
                job_dir=run/('%s-%d'%(spec['kind'],spec['index']))
                job_size=bytes_used(job_dir)+bytes_used(run/('tmp-%s-%d'%(spec['kind'],spec['index'])))
                job_size+=file_bytes(run.glob('slurm-%s-%d-*'%(spec['kind'],spec['index'])))
                if bytes_used(run)+p.CAPS['source_bytes']>p.CAPS['storage_bytes'] or job_size>p.CAPS['job_bytes']:
                    command('scancel',job);event('storage_stop',job=job,full_reservation_charged=spec['seconds'])
                    raise RuntimeError('Storage cap; retain reservation and partial files')
                text=command('sacct','-X','-n','-P','-j',job,'--format=JobID,State,ExitCode,ElapsedRaw')
                rows=[r.split('|')[:4] for r in text.splitlines() if r.split('|')[0]==job]
                p.require(len(rows)<=1,'Ambiguous scheduler state')
                if not rows or rows[0][1] in ('PENDING','RUNNING','CONFIGURING','COMPLETING','SUSPENDED'):continue
                _,state,code,seconds=rows[0];seconds=int(seconds);active=None
                if spec['gpu']:gpu+=seconds
                else:cpu+=seconds
                event('terminal',job=job,state=state,exit_code=code,seconds=seconds,gpu_seconds=gpu,cpu_seconds=cpu)
                p.require(state=='COMPLETED' and code=='0:0' and seconds<=spec['seconds'],'Failed allocation; no retry')
                break
            meta=technical_report(job_dir)
            p.require(meta['source_sha256']==a['source_sha256'] and meta['technical_valid'],'Technical source identity')
            if pos<16:tranche.append(dict(task=spec,seconds=seconds,bytes=job_size,rss=meta['maxrss_bytes']))
            if pos==15:
                p.require(all(x['rss']<=16*(1<<30) for x in tranche),'Training tranche memory envelope')
                worst=max(x['bytes'] for x in tranche)
                p.require(worst*(384+2*64)<8_000_000_000,'Conservative storage projection; no pruning')
                projected=sum(2*max(x['seconds'] for x in tranche if x['task']['h']==h)*
                    (96+96+64) for h in (75,150))
                event('technical_tranche',projected_gpu_seconds=projected,projected_storage_bytes=worst*512)
                p.require(projected<=p.CAPS['gpu_seconds'],'Cost projection cannot fit; no changed cases')
        terminal=run/'terminal';terminal.mkdir()
        summary=dict(completed_development_only=True,gpu_seconds=gpu,cpu_wall_seconds=cpu,jobs=jobs,
                     storage_bytes=bytes_used(run),no_followup_launched=True)
        ct.json_write(terminal/'REPORT.json',summary)
        for name in ('DISPATCH.jsonl',):
            (terminal/name).write_bytes((run/name).read_bytes())
        ct.seal(terminal);backup('terminal');ct.json_write(run/'DISPATCH-FINAL.json',summary)
    except BaseException as exc:
        # Never leave a known live allocation running after a controller fault.
        # Unknown submission identities require human scheduler reconciliation.
        if active and active.isdigit():
            try:command('scancel',active)
            except Exception:pass
        event('stopped',type=type(exc).__name__,message=str(exc),active_job=active,
              charged_gpu_seconds=gpu,charged_cpu_seconds=cpu,
              unresolved_reservation_seconds=spec['seconds'] if active else 0,automatic_retry=False)
        ct.json_write(run/'DISPATCH-STOP.json',dict(reason=str(exc),active_job=active,
            gpu_seconds=gpu,cpu_wall_seconds=cpu,
            unresolved_reservation_seconds=spec['seconds'] if active else 0,
            requires_terminal_accounting_and_failure_backup=True,no_automatic_retry=True))
        raise


if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('mode',choices=['dispatch','worker'])
    for n in ('source','run','approval'):cli.add_argument('--'+n,required=True)
    cli.add_argument('--kind');cli.add_argument('--index',type=int);a=cli.parse_args()
    if a.mode=='dispatch':dispatch(a.source,a.run,a.approval)
    else:worker(a.source,a.run,a.approval,a.kind,a.index)
