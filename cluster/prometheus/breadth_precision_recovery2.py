"""Second, explicitly authorized host-only BP1 resumption; no completed-job retry."""
import argparse
import json
from pathlib import Path
import shutil
import time
import breadth_precision_contract as p
import candidate_value_contract as ct
import breadth_precision_recovery as old
from breadth_precision_execute import arguments, command
from breadth_precision_infra import bytes_used, file_bytes
from breadth_precision_recovery import name, overlay_check, check_meta, recovery_meta, wait_live

SOURCE_SHA = old.SOURCE_SHA
OLD_APPROVAL_SHA = old.OLD_APPROVAL_SHA
PREFIX = 148
PRIOR_GPU = 32004
ACCOUNT_SHA = '2b0df6c05f7acf0ce1a629a8d428abbcf15b59d95614fe9451b003418eec8f53'
ORIGINAL_LEDGER_SHA = 'c9f4605b8af5541792e2f9c5be1fecfdbb3c2f20e45a19b250ada2716a647686'
RECOVERY_LEDGER_SHA = '64a48ef929b3582a0f414468c35a81d065eb823e8445e6d95181142f2aa4c04e'
RECOVERY_STOP_SHA = 'a1f610dd9876de2a79fcbffed5a2923def9dc1cb1faa138bf92e0db11201937b'
OLD_RECOVERY_APPROVAL_SHA = '9640ca030809f1bd0d176c6dacd5e4a8d160f08d0198bd158f4cdbd975de3260'
OLD_STAGE = p.ROOT/'staging/candidate-value-breadth-precision-20260915-70e3838c83561b8b'
OLD_CONTROL = p.ROOT/'staging/cvl-bp1-recovery-301578-20260916'
OLD_OVERLAY = p.ROOT/'snapshots/cvl-bp1-recovery-301578-47726fc626f9c7a6'
VOLUME_ID = '\\\\?\\Volume{0a2f1ba9-0000-0000-0000-100000000000}\\'
BACKUPS = {
 'failure-20260916': dict(request=old.FAILURE_REQUEST_SHA, archive=old.FAILURE_ARCHIVE_SHA,
                         receipt=old.FAILURE_RECEIPT_SHA, ack=old.FAILURE_ACK_SHA),
 'recovery-stop-20260916': dict(
  request='2e800637463fc1fbb121e8939875c553f004d71c4fbf84320001567af0321383',
  archive='b5bbf19cc470ccbf58fad39f350ccfecf38fed2867b7eaf8344d2f8e6cc12d46',
  receipt='ebb4d9606f7ecc75484c1d50505a9dae5a4dcfa59864ee1a622cb1cad3244a83',
  ack='3d806dd5824bb2dc6baa504543e398f18bc01dbb9b69383ac3aae8d86aa9b245')
}


def prior_state(run, accounting):
    """Authenticate accepted terminal controls/seals; no scientific decoding."""
    run = Path(run)
    for path, digest in [
        (Path(accounting), ACCOUNT_SHA),
        (run/'DISPATCH.jsonl', ORIGINAL_LEDGER_SHA),
        (run/'DISPATCH-STOP.json', old.STOP_SHA),
        (run/'RECOVERY-DISPATCH.jsonl', RECOVERY_LEDGER_SHA),
        (run/'RECOVERY-STOP.json', RECOVERY_STOP_SHA),
        (OLD_CONTROL/'RECOVERY-APPROVAL.json', OLD_RECOVERY_APPROVAL_SHA)]:
        p.require(p.sha(path) == digest, 'Unchanged accepted terminal evidence: '+path.name)
    previous = ct.json_read(OLD_CONTROL/'RECOVERY-APPROVAL.json')
    account = ct.json_read(accounting)
    p.require(account['all_terminal'] is True and account['controller_absent'] is True and
              account['backup_companion_absent'] is True and account['scientific_payloads_decoded'] is False and
              account['gpu_allocation_seconds'] == PRIOR_GPU and account['cpu_stage_seconds'] == 0 and
              account['successful_coordinates'] == PREFIX and account['allocation_attempts'] == 149 and
              account['unresolved_reservations'] == 0, 'Accepted reconciled accounting')
    events = [json.loads(line) for line in (run/'RECOVERY-DISPATCH.jsonl').read_text().splitlines()]
    submissions = [e for e in events if e['event'] == 'submitted']
    terminals = [e for e in events if e['event'] == 'terminal']
    p.require([e['task'] for e in submissions] == p.grid()[old.PREFIX:PREFIX] and len(terminals) == 46,
              'Exact successful recovery prefix')
    jobs = list(previous['prior_jobs'])
    new = []
    for submit, terminal in zip(submissions, terminals):
        p.require(submit['job'] == terminal['job'] and terminal['state'] == 'COMPLETED' and
                  terminal['exit_code'] == '0:0' and 0 <= terminal['seconds'] <= submit['task']['seconds'],
                  'Completed terminal event required')
        new.append(dict(job=submit['job'],task=submit['task'],state=terminal['state'],
                        exit_code=terminal['exit_code'],seconds=terminal['seconds']))
    p.require(new == account['recovery_rows'] and sum(j['seconds'] for j in new) == 10212,
              'Exact recovery accounting')
    jobs += new
    p.require(len(jobs) == len({j['job'] for j in jobs}) == 149 and
              sum(j['seconds'] for j in jobs) == PRIOR_GPU, 'Retain every prior charge')
    successful = [j['task'] for j in jobs if j['state'] == 'COMPLETED']
    p.require(successful == p.grid()[:PREFIX], 'No completed coordinate retry')
    stop = ct.json_read(run/'RECOVERY-STOP.json')
    p.require(stop['active_job'] is None and stop['unresolved_reservation_seconds'] == 0 and
              stop['gpu_seconds'] == PRIOR_GPU, 'No uncertain live work')
    seals = {}
    for stage, identity in BACKUPS.items():
        request_path = run/('BACKUP-REQUEST-'+stage+'.json')
        ack_path = run/('BACKUP-ACK-'+stage+'.json')
        p.require(p.sha(request_path) == identity['request'] and p.sha(ack_path) == identity['ack'],
                  'Accepted backup identities')
        request, ack = ct.json_read(request_path), ct.json_read(ack_path)
        p.require(ack['verified'] is True and ack['request_sha256'] == identity['request'] and
                  ack['archive_sha256'] == identity['archive'] and request['run'] == str(run),
                  'Accepted external coverage')
        for directory, digest in request['seals'].items():
            p.require('/' not in directory and directory not in ('.','..'), 'Safe sealed root')
            p.require(directory not in seals or seals[directory] == digest, 'Consistent overlap')
            seals[directory] = digest
    p.require({x.parent.name for x in run.glob('*/sha256.txt')} == set(seals),
              'All current sealed roots covered by accepted backups')
    for directory, digest in seals.items():
        p.require(p.sha(run/directory/'sha256.txt') == digest, 'Preserved seal unchanged')
    for spec in p.grid()[:PREFIX]:
        check_meta(recovery_meta(run/name(spec)), spec)
    for spec in p.grid()[PREFIX:]:
        d = name(spec)
        p.require(not (run/d).exists() and not (run/('tmp-'+d)).exists() and
                  not list(run.glob('slurm-'+d+'-*')), 'Only unsubmitted fixed remainder')
    p.require(not (run/'DISPATCH-FINAL.json').exists() and not (run/'terminal').exists() and
              not any((run/('BACKUP-REQUEST-'+s+'.json')).exists() for s in ('train','models','evaluation','terminal')),
              'No later stage already executed')
    p.require(all(not Path('/proc/'+pid).exists() for pid in ('3489337','4125577')),
              'Historical controllers absent')
    return jobs, dict(directories=sorted(seals), seals=seals)


def source_control_bytes(source, control, overlay):
    return (2*bytes_used(source)+2*bytes_used(overlay)+2*bytes_used(OLD_OVERLAY)+
            bytes_used(OLD_STAGE)+bytes_used(OLD_CONTROL)+bytes_used(control))


def prepare(source, run, approval, accounting, overlay, overlay_sha, target):
    a, _ = p.authorize(source, run, approval)
    p.require(a['source_sha256'] == SOURCE_SHA and p.sha(approval) == OLD_APPROVAL_SHA,
              'Unchanged scientific authorization')
    overlay_check(overlay, overlay_sha)
    jobs, coverage = prior_state(run, accounting)
    p.require(p.reservation(PRIOR_GPU, 0, bytes_used(run), p.grid()[PREFIX:]), 'Original caps')
    value = dict(researcher_approved=True,
        authorization='User yes on 17 September to repair SSD-check interoperability and resume only 302 unsubmitted tasks, reusing all148 completed outputs with unchanged scientific settings and budgets.',
        run=str(Path(run)),scientific_source=str(Path(source)),source_sha256=SOURCE_SHA,
        old_approval=str(Path(approval)),old_approval_sha256=OLD_APPROVAL_SHA,
        protocol_sha256=a['protocol_sha256'],role_manifest_sha256=a['role_manifest_sha256'],caps=p.CAPS,
        overlay=str(Path(overlay)),overlay_sha256=overlay_sha,accounting=str(Path(accounting)),
        accounting_sha256=ACCOUNT_SHA,original_dispatch_sha256=ORIGINAL_LEDGER_SHA,
        recovery_dispatch_sha256=RECOVERY_LEDGER_SHA,recovery_stop_sha256=RECOVERY_STOP_SHA,
        completed_prefix=PREFIX,prior_jobs=jobs,gpu_seconds=PRIOR_GPU,cpu_seconds=0,
        remaining_tasks=p.grid()[PREFIX:],completed_seals=coverage['seals'],
        automatic_job_retries=False,max_additional_replacement_attempts=0,total_attempts_if_complete=451,
        external_volume_id=VOLUME_ID,scientific_changes=False,partial_outcomes_decoded=False)
    ct.json_write(target,value)
    return value


def dispatch(recovery, recovery_sha):
    recovery = Path(recovery)
    p.require(p.sha(recovery) == recovery_sha, 'Exact recovery authorization')
    r = ct.json_read(recovery); run = Path(r['run']); source = Path(r['scientific_source'])
    approval = Path(r['old_approval']); control = recovery.parent
    p.require(r['researcher_approved'] is True and r['caps'] == p.CAPS and r['source_sha256'] == SOURCE_SHA and
              r['completed_prefix'] == PREFIX and r['external_volume_id'] == VOLUME_ID and
              r['remaining_tasks'] == p.grid()[PREFIX:] and r['max_additional_replacement_attempts'] == 0 and
              r['automatic_job_retries'] is False, 'Narrow authorized recovery only')
    p.authorize(source, run, approval)
    p.require(p.sha(approval) == OLD_APPROVAL_SHA, 'Original execution approval')
    overlay_check(r['overlay'], r['overlay_sha256'])
    p.require(Path(__file__).resolve().parent == Path(r['overlay']).resolve(), 'Run sealed recovery controller')
    jobs, request = prior_state(run, r['accounting'])
    p.require(request['seals'] == r['completed_seals'], 'Approved complete backup coverage')
    p.require(jobs == r['prior_jobs'] and p.sha(run/'DISPATCH.jsonl') == r['original_dispatch_sha256'],
              'Approved historical prefix unchanged')
    p.require(not Path('/proc/3489337').exists(), 'Old controller must remain absent')
    ready = ct.json_read(control/'BACKUP-RECOVERY-READY.json')
    p.require(ready.get('approval_sha256') == recovery_sha and ready.get('archives') == {s:v['archive'] for s,v in BACKUPS.items()} and
              ready.get('all_prior_backups_verified') is True, 'Existing external failure backup verified')
    wait_live(control, recovery_sha)
    p.require(source_control_bytes(source,control,r['overlay']) < p.CAPS['source_bytes'],
              'Whole source/control reserve')
    ct.json_write(run/'RECOVERY2-CLAIM.json',dict(approval_sha256=recovery_sha, overlay_sha256=r['overlay_sha256'],utc=time.time()))
    gpu=PRIOR_GPU; cpu=0; active=None; spec=None
    backed=set(request['directories'])
    with (run/'RECOVERY2-DISPATCH.jsonl').open('x',buffering=1) as log:
        def event(event_name, **kw):
            log.write(json.dumps(dict(event=event_name,utc=time.time(),**kw),sort_keys=True)+'\n')
        def backup(stage):
            directories=sorted(x.name for x in run.iterdir() if x.is_dir() and
                               (x/'sha256.txt').is_file() and x.name not in backed)
            req=run/('BACKUP-REQUEST-'+stage+'.json')
            ct.json_write(req,dict(stage=stage,run=str(run),directories=directories,source_sha256=SOURCE_SHA,
                seals={d:p.sha(run/d/'sha256.txt') for d in directories}))
            ack=run/('BACKUP-ACK-'+stage+'.json'); deadline=time.monotonic()+3600
            while not ack.exists():
                p.require(not (control/'BACKUP-RECOVERY-STOP.json').exists(),'Backup companion stopped')
                p.require(time.monotonic()<deadline,'Stage backup timeout; no automatic transfer retry')
                time.sleep(20)
            receipt=ct.json_read(ack)
            p.require(receipt.get('verified') is True and receipt['request_sha256']==p.sha(req),'Exact backup acknowledgement')
            backed.update(directories);event('backup_verified',stage=stage,archive_sha256=receipt['archive_sha256'])
        try:
            event('authorized_recovery',approval_sha256=recovery_sha,completed_reused=PREFIX,
                  cancelled_cost_seconds=63,gpu_seconds=gpu,additional_replacement_limit=0)
            evidence=run/'recovery2-evidence-20260917';evidence.mkdir()
            for path in (recovery,Path(r['accounting']),approval):
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
                if spec['kind']=='fit':backup('train')
                if spec['kind']=='evaluation' and spec['index']==0:
                    from breadth_precision_freeze import check_frozen
                    check_frozen(run,SOURCE_SHA);backup('models')
                if spec['kind']=='analyze':backup('evaluation')
                wait_live(control,recovery_sha)
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
            for path in (run/'DISPATCH.jsonl',run/'DISPATCH-STOP.json',run/'RECOVERY-DISPATCH.jsonl',run/'RECOVERY-STOP.json',run/'RECOVERY2-DISPATCH.jsonl',recovery):
                with path.open('rb') as src,(terminal/path.name).open('xb') as dst:shutil.copyfileobj(src,dst)
            ct.seal(terminal);backup('terminal');ct.json_write(run/'DISPATCH-FINAL.json',summary)
        except BaseException as exc:
            if active and active.isdigit():
                try:command('scancel',active)
                except Exception:pass
            stop=dict(reason=str(exc),type=type(exc).__name__,active_job=active,gpu_seconds=gpu,cpu_wall_seconds=cpu,
                unresolved_reservation_seconds=spec['seconds'] if active and spec else 0,
                requires_terminal_accounting_and_failure_backup=True,no_automatic_retry=True)
            event('stopped',**stop);ct.json_write(run/'RECOVERY2-STOP.json',stop)
            raise


if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('mode',choices=['prepare','dispatch'])
    for field in ('source','run','approval','accounting','overlay','overlay-sha','target','recovery','recovery-sha'):
        cli.add_argument('--'+field)
    args=cli.parse_args()
    if args.mode=='prepare':
        prepare(args.source,args.run,args.approval,args.accounting,args.overlay,args.overlay_sha,args.target)
    else:dispatch(args.recovery,args.recovery_sha)
