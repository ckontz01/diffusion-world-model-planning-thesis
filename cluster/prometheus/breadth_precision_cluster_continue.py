"""One-use cluster-only BP1 continuation; completed work is never restarted."""
import argparse
import json
from pathlib import Path
import shutil
import time
import breadth_precision_contract as p
import candidate_value_contract as ct
import breadth_precision_recovery2 as previous
from breadth_precision_execute import arguments, command
from breadth_precision_infra import bytes_used, file_bytes
from breadth_precision_recovery import name, overlay_check, check_meta, recovery_meta

SOURCE_SHA = previous.SOURCE_SHA
OLD_APPROVAL_SHA = previous.OLD_APPROVAL_SHA
PREFIX = 150
PRIOR_GPU = 32469
R2_CONTROL = p.ROOT/'staging/cvl-bp1-recovery2-20260917'
R2_OVERLAY = p.ROOT/'snapshots/cvl-bp1-recovery2-e8f1e44b90e5370b'
R2_APPROVAL_SHA = 'cb58d691f4890da5de9037123303d5891e50ab2745f675a0621b656fbec0a7e7'
R2_LEDGER_SHA = '719595552439fe476965a53d9c5b858a1fb012d191e5b2b2746758bad7a0b813'
R2_STOP_SHA = 'ba901c49a902230dce5921ac4f102dedbdd42b84afbbbd9f20eb8d2daa14118b'


def prior_state(run):
    """Authenticate accepted controls and technical projections only."""
    run=Path(run)
    for path,digest in [(R2_CONTROL/'RECOVERY2-APPROVAL.json',R2_APPROVAL_SHA),
        (run/'RECOVERY2-DISPATCH.jsonl',R2_LEDGER_SHA),(run/'RECOVERY2-STOP.json',R2_STOP_SHA),
        (run/'DISPATCH.jsonl',previous.ORIGINAL_LEDGER_SHA),
        (run/'DISPATCH-STOP.json',previous.old.STOP_SHA),
        (run/'RECOVERY-DISPATCH.jsonl',previous.RECOVERY_LEDGER_SHA),
        (run/'RECOVERY-STOP.json',previous.RECOVERY_STOP_SHA)]:
        p.require(p.sha(path)==digest,'Preserved historical control: '+path.name)
    r=ct.json_read(R2_CONTROL/'RECOVERY2-APPROVAL.json')
    p.require(r['completed_prefix']==148 and r['gpu_seconds']==32004 and r['cpu_seconds']==0,
              'Accepted prior recovery charges')
    jobs=list(r['prior_jobs'])
    events=[json.loads(x) for x in (run/'RECOVERY2-DISPATCH.jsonl').read_text().splitlines()]
    submissions=[x for x in events if x['event']=='submitted']
    terminals=[x for x in events if x['event']=='terminal']
    p.require([x['task'] for x in submissions]==p.grid()[148:150] and
              [x['job'] for x in submissions]==['301630','301631'] and len(terminals)==2,
              'Only two additional completed tasks')
    for sub,term,seconds in zip(submissions,terminals,(173,292)):
        p.require(sub['job']==term['job'] and term['state']=='COMPLETED' and
                  term['exit_code']=='0:0' and term['seconds']==seconds,'Closed terminal ledger')
        jobs.append(dict(job=sub['job'],task=sub['task'],state=term['state'],
                         exit_code=term['exit_code'],seconds=seconds))
    p.require(len(jobs)==len({x['job'] for x in jobs})==151 and
              sum(x['seconds'] for x in jobs)==PRIOR_GPU and
              [x['task'] for x in jobs if x['state']=='COMPLETED']==p.grid()[:PREFIX],
              'Exact 150 completed coordinates and all charges')
    stop=ct.json_read(run/'RECOVERY2-STOP.json')
    p.require(stop['active_job'] is None and stop['unresolved_reservation_seconds']==0 and
              stop['gpu_seconds']==PRIOR_GPU and stop['cpu_wall_seconds']==0,'No unresolved allocation')
    # Old external coverage remains recorded; new two outputs are explicitly not backed yet.
    covered=dict(r['completed_seals'])
    for stage,identity in previous.BACKUPS.items():
        req=run/('BACKUP-REQUEST-'+stage+'.json');ack=run/('BACKUP-ACK-'+stage+'.json')
        p.require(p.sha(req)==identity['request'] and p.sha(ack)==identity['ack'],'Existing backup record')
    for d,digest in covered.items():
        p.require(p.sha(run/d/'sha256.txt')==digest,'Historical covered seal')
    expected=dict(covered)
    expected['recovery2-evidence-20260917']='0641de4e747478885a1ba95b7cab346f2fa4a8289c62019f581c98a5e1a705c0'
    for spec in p.grid()[148:PREFIX]:
        expected[name(spec)]=p.sha(run/name(spec)/'sha256.txt')
    p.require({x.parent.name for x in run.glob('*/sha256.txt')}==set(expected),'Exact completed root inventory')
    for d,digest in expected.items():
        p.require(p.sha(run/d/'sha256.txt')==digest,'Preserved root identity')
    for spec in p.grid()[:PREFIX]:
        check_meta(recovery_meta(run/name(spec)),spec)
    for spec in p.grid()[PREFIX:]:
        d=name(spec)
        p.require(not (run/d).exists() and not (run/('tmp-'+d)).exists() and
                  not list(run.glob('slurm-'+d+'-*')),'Never rerun submitted/completed work')
    p.require(not (run/'terminal').exists() and not (run/'DISPATCH-FINAL.json').exists() and
              not (run/'CLUSTER-COMPUTE-COMPLETE.json').exists(),'No later completion')
    p.require(all(not Path('/proc/'+x).exists() for x in ('3489337','4125577','97218')),
              'Previous controllers absent')
    return jobs,dict(directories=sorted(covered),seals=expected)


def source_control_bytes(source,control,overlay):
    return previous.source_control_bytes(source,R2_CONTROL,R2_OVERLAY)+2*bytes_used(overlay)+bytes_used(control)


def prepare(source,run,approval,overlay,overlay_sha,target):
    a,_=p.authorize(source,run,approval)
    p.require(a['source_sha256']==SOURCE_SHA and p.sha(approval)==OLD_APPROVAL_SHA,'Original scientific source')
    overlay_check(overlay,overlay_sha)
    jobs,inventory=prior_state(run)
    scheduler=command('sacct','-X','-n','-P','-j','301630,301631',
                      '--format=JobID,State,ExitCode,ElapsedRaw')
    rows=[x.split('|')[:4] for x in scheduler.splitlines() if x.strip()]
    p.require(rows==[['301630','COMPLETED','0:0','173'],['301631','COMPLETED','0:0','292']],
              'Independent terminal scheduler reconciliation')
    p.require(p.reservation(PRIOR_GPU,0,bytes_used(run),p.grid()[PREFIX:]),'Original aggregate caps')
    value=dict(researcher_approved=True,
        authorization='User 17 September explicitly authorized cluster-only continuation with external backup at end; do not restart training or completed work.',
        backup_policy='external_after_compute',external_backup_risk_accepted=True,
        scientific_changes=False,partial_outcomes_decoded=False,
        run=str(Path(run)),scientific_source=str(Path(source)),source_sha256=SOURCE_SHA,
        old_approval=str(Path(approval)),old_approval_sha256=OLD_APPROVAL_SHA,
        protocol_sha256=a['protocol_sha256'],role_manifest_sha256=a['role_manifest_sha256'],caps=p.CAPS,
        overlay=str(Path(overlay)),overlay_sha256=overlay_sha,completed_prefix=PREFIX,
        prior_jobs=jobs,gpu_seconds=PRIOR_GPU,cpu_seconds=0,remaining_tasks=p.grid()[PREFIX:],
        original_dispatch_sha256=previous.ORIGINAL_LEDGER_SHA,completed_seals=inventory['seals'],
        already_backed_directories=inventory['directories'],scheduler_rows=rows,
        automatic_job_retries=False,max_additional_replacement_attempts=0,total_attempts_if_complete=451)
    ct.json_write(target,value)
    return value


def dispatch(recovery, recovery_sha):
    recovery = Path(recovery)
    p.require(p.sha(recovery) == recovery_sha, 'Exact recovery authorization')
    r = ct.json_read(recovery); run = Path(r['run']); source = Path(r['scientific_source'])
    approval = Path(r['old_approval']); control = recovery.parent
    p.require(r['researcher_approved'] is True and r['caps'] == p.CAPS and r['source_sha256'] == SOURCE_SHA and
              r['completed_prefix'] == PREFIX and r['backup_policy'] == 'external_after_compute' and
              r['remaining_tasks'] == p.grid()[PREFIX:] and r['max_additional_replacement_attempts'] == 0 and
              r['automatic_job_retries'] is False, 'Narrow authorized recovery only')
    p.authorize(source, run, approval)
    p.require(p.sha(approval) == OLD_APPROVAL_SHA, 'Original execution approval')
    overlay_check(r['overlay'], r['overlay_sha256'])
    p.require(Path(__file__).resolve().parent == Path(r['overlay']).resolve(), 'Run sealed recovery controller')
    jobs, request = prior_state(run)
    p.require(request['seals'] == r['completed_seals'], 'Approved existing seal inventory')
    p.require(jobs == r['prior_jobs'] and p.sha(run/'DISPATCH.jsonl') == r['original_dispatch_sha256'],
              'Approved historical prefix unchanged')
    p.require(not Path('/proc/3489337').exists(), 'Old controller must remain absent')
    p.require(source_control_bytes(source,control,r['overlay']) < p.CAPS['source_bytes'],
              'Whole source/control reserve')
    ct.json_write(run/'CLUSTER-CONTINUE-CLAIM.json',dict(approval_sha256=recovery_sha, overlay_sha256=r['overlay_sha256'],utc=time.time()))
    gpu=PRIOR_GPU; cpu=0; active=None; spec=None
    backed=set(request['directories'])
    with (run/'CLUSTER-CONTINUE-DISPATCH.jsonl').open('x',buffering=1) as log:
        def event(event_name, **kw):
            log.write(json.dumps(dict(event=event_name,utc=time.time(),**kw),sort_keys=True)+'\n')
        def barrier(stage):
            if stage == 'train':
                wanted = [s for s in p.grid() if s['kind'] in ('breadth','precision')]
            elif stage == 'models':
                wanted = [p.task('fit',0)]
            else:
                wanted = [s for s in p.grid() if s['kind']=='evaluation']
            for item in wanted:
                check_meta(recovery_meta(run/name(item)),item)
            value = dict(stage=stage,source_sha256=SOURCE_SHA,approval_sha256=recovery_sha,
                directories=[name(s) for s in wanted],
                seals={name(s):p.sha(run/name(s)/'sha256.txt') for s in wanted},
                external_backup_deferred=True,not_a_backup=True,utc=time.time())
            ct.json_write(run/('CLUSTER-STAGE-'+stage+'.json'),value)
            event('cluster_stage_verified',stage=stage)
        try:
            event('authorized_recovery',approval_sha256=recovery_sha,completed_reused=PREFIX,
                  cancelled_cost_seconds=63,gpu_seconds=gpu,additional_replacement_limit=0)
            evidence=run/'cluster-continue-evidence-20260917';evidence.mkdir()
            for path in (recovery,R2_CONTROL/'RECOVERY2-APPROVAL.json',approval):
                with path.open('rb') as src,(evidence/path.name).open('xb') as dst:shutil.copyfileobj(src,dst)
            for path in Path(r['overlay']).iterdir():
                if path.is_file():
                    with path.open('rb') as src,(evidence/path.name).open('xb') as dst:shutil.copyfileobj(src,dst)
            ct.seal(evidence)
            fixed=p.grid()
            for pos in range(PREFIX,len(fixed)):
                spec=fixed[pos]
                p.require(p.reservation(gpu,cpu,bytes_used(run),fixed[pos:]),'Whole remaining workload cannot fit original caps')
                p.require(source_control_bytes(source,control,r['overlay'])<p.CAPS['source_bytes'],
                          'Source/control cap')
                if spec['kind']=='fit':barrier('train')
                if spec['kind']=='evaluation' and spec['index']==0:
                    from breadth_precision_freeze import check_frozen
                    check_frozen(run,SOURCE_SHA);barrier('models')
                if spec['kind']=='analyze':barrier('evaluation')
                job_dir=run/name(spec)
                p.require(not job_dir.exists() and not (run/('tmp-'+name(spec))).exists(), 'No output reuse/overwrite')
                cmd=arguments(spec,source,run,approval)
                event('reservation',task=spec,command=cmd,gpu_seconds=gpu,cpu_seconds=cpu)
                active='submission_outcome_unknown'
                job=command(*cmd).split(';')[0]
                p.require(job.isdigit(),'Ambiguous submission; stop, never retry')
                active=job;jobs.append(dict(job=job,task=spec));event('submitted',job=job,task=spec)
                while True:
                    time.sleep(20)
                    size=bytes_used(job_dir)+bytes_used(run/('tmp-'+name(spec)))+file_bytes(run.glob('slurm-'+name(spec)+'-*'))
                    p.require(bytes_used(run)+p.CAPS['source_bytes']<=p.CAPS['storage_bytes'] and size<=p.CAPS['job_bytes'],
                              'Storage cap; stop, preserve partials')
                    text=command('sacct','-X','-n','-P','-j',job,'--format=JobID,State,ExitCode,ElapsedRaw')
                    rows=[x.split('|')[:4] for x in text.splitlines() if x.split('|')[0]==job]
                    p.require(len(rows)<=1,'Ambiguous scheduler state')
                    if not rows or rows[0][1] in ('PENDING','RUNNING','CONFIGURING','COMPLETING','SUSPENDED'):continue
                    _,state,code,seconds=rows[0];seconds=int(seconds);active=None
                    if spec['gpu']:gpu+=seconds
                    else:cpu+=seconds
                    jobs[-1].update(state=state,exit_code=code,seconds=seconds)
                    event('terminal',job=job,state=state,exit_code=code,seconds=seconds,gpu_seconds=gpu,cpu_seconds=cpu)
                    p.require(state=='COMPLETED' and code=='0:0' and 0<=seconds<=spec['seconds'],'Failed allocation; no retry')
                    break
                check_meta(recovery_meta(job_dir),spec)
            terminal=run/'terminal';terminal.mkdir()
            summary=dict(completed_development_only=True,gpu_seconds=gpu,cpu_wall_seconds=cpu,jobs=jobs,
                successful_coordinates=450,allocation_attempts=len(jobs),prior_cancelled_seconds=63,
                storage_bytes=bytes_used(run),no_followup_launched=True,recovery_approval_sha256=recovery_sha)
            ct.json_write(terminal/'REPORT.json',summary)
            for path in (run/'DISPATCH.jsonl',run/'DISPATCH-STOP.json',run/'RECOVERY-DISPATCH.jsonl',run/'RECOVERY-STOP.json',run/'RECOVERY2-DISPATCH.jsonl',run/'RECOVERY2-STOP.json',run/'CLUSTER-CONTINUE-DISPATCH.jsonl',run/'CLUSTER-STAGE-train.json',run/'CLUSTER-STAGE-models.json',run/'CLUSTER-STAGE-evaluation.json',recovery):
                with path.open('rb') as src,(terminal/path.name).open('xb') as dst:shutil.copyfileobj(src,dst)
            ct.seal(terminal)
            # Completion of computation is not completion of the external backup.
            directories=sorted(x.name for x in run.iterdir() if x.is_dir() and
                               (x/'sha256.txt').is_file() and x.name not in backed)
            ct.json_write(run/'BACKUP-REQUEST-cluster-final.json',dict(
                stage='cluster-final',run=str(run),directories=directories,source_sha256=SOURCE_SHA,
                seals={d:p.sha(run/d/'sha256.txt') for d in directories}))
            ct.json_write(run/'CLUSTER-COMPUTE-COMPLETE.json',dict(
                summary,external_backup_verified=False,external_backup_pending=True))
            event('compute_complete_backup_pending',successful_coordinates=450,allocation_attempts=len(jobs))
        except BaseException as exc:
            if active and active.isdigit():
                try:command('scancel',active)
                except Exception:pass
            stop=dict(reason=str(exc),type=type(exc).__name__,active_job=active,gpu_seconds=gpu,cpu_wall_seconds=cpu,
                unresolved_reservation_seconds=spec['seconds'] if active and spec else 0,
                requires_terminal_accounting_and_failure_backup=True,no_automatic_retry=True)
            event('stopped',**stop);ct.json_write(run/'CLUSTER-CONTINUE-STOP.json',stop)
            raise

if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('mode',choices=['prepare','dispatch'])
    for field in ('source','run','approval','overlay','overlay-sha','target','recovery','recovery-sha'):
        cli.add_argument('--'+field)
    args=cli.parse_args()
    if args.mode=='prepare':
        prepare(args.source,args.run,args.approval,args.overlay,args.overlay_sha,args.target)
    else:dispatch(args.recovery,args.recovery_sha)
