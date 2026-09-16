"""One-use, infrastructure-only CVL-BP1 recovery of cancelled allocation 301578.

The existing scientific snapshot and worker entry point remain byte-identical.
Python 3.6/stdlib on the login host; no numerical module imports.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import time
import breadth_precision_contract as p
import candidate_value_contract as ct
from breadth_precision_execute import arguments, command
from breadth_precision_infra import bytes_used, file_bytes, technical_report

SOURCE_SHA = '70e3838c83561b8b24ea2f2c2f6875c2674d7c9b391e682c1023ba3641238975'
ACCOUNT_SHA = '7d26dce2044dc9f089b86c804f21237f567dcd5fdbddd0ca32d39ee0a853d952'
OLD_APPROVAL_SHA = 'e7f6d1e67b9ccc0babfb7b613806dc3826fc9d9dc0225c93fab7b54c424d9bc5'
STOP_SHA = 'a0d9466eb923ec482d1e9583ec44df3eb64507f18d51fe03ec77897c85d51734'
FAILURE_REQUEST_SHA = '5a32ad65a667018d2987a74132a41fb56f4de70651525ca7ab546db8aa0cdb7c'
FAILURE_RECEIPT_SHA = 'e0ad5f3391160c1178238f2f21fcba20fd2d3749785c1abd9648fa8518f4b963'
FAILURE_ACK_SHA = '21486654f879d40385d2c9579c782cff41945888e431375a9d33396a95916478'
FAILURE_ARCHIVE_SHA = '5f09feeabd59032c129940c69a6ab5163f1bf4171d52bc37ef96b7fc4f558bba'
PREFIX = 102
PRIOR_GPU = 21792
FAILED_JOB = '301578'


def name(spec):
    return '%s-%d' % (spec['kind'], spec['index'])


def overlay_check(directory, digest):
    directory = Path(directory)
    p.require(p.sha(directory/'SOURCE-MANIFEST.sha256') == digest, 'Recovery source seal')
    seen = set()
    for line in (directory/'SOURCE-MANIFEST.sha256').read_text().splitlines():
        wanted, rel = line.split('  ', 1)
        p.require(rel not in seen and p.sha(ct.child(directory, rel)) == wanted, 'Recovery source member')
        seen.add(rel)
    actual = {x.relative_to(directory).as_posix() for x in directory.rglob('*')
              if x.is_file() and '__pycache__' not in x.parts and x.name != 'SOURCE-MANIFEST.sha256'}
    p.require(actual == seen and seen, 'Recovery source exact closure')


def tree_inventory(directory):
    directory = Path(directory)
    p.require(directory.is_dir() and not directory.is_symlink(), 'Real attempt directory required')
    files = {}
    for item in directory.rglob('*'):
        p.require(not item.is_symlink(), 'No attempt symlinks')
        if item.is_file():
            files[item.relative_to(directory).as_posix()] = dict(sha256=p.sha(item), bytes=item.stat().st_size)
    return files


def prior_state(run, accounting):
    """Read only scheduler/control metadata and accepted technical projections."""
    run = Path(run)
    p.require(p.sha(accounting) == ACCOUNT_SHA and p.sha(run/'DISPATCH-STOP.json') == STOP_SHA,
              'Exact terminal stop/accounting')
    account = ct.json_read(accounting)
    p.require(account['run'] == str(run) and account['all_terminal'] is True and
              account['controller_absent'] is True and account['scientific_payloads_decoded'] is False and
              account['allocation_count'] == 103 and account['gpu_allocation_seconds'] == PRIOR_GPU and
              account['cpu_stage_seconds'] == 0, 'Reconciled prior allocation accounting')
    events = [json.loads(line) for line in (run/'DISPATCH.jsonl').read_text().splitlines()]
    submitted = [e for e in events if e['event'] == 'submitted']
    fixed = p.grid()
    p.require([e['task'] for e in submitted] == fixed[:PREFIX+1], 'Exact historical submitted prefix')
    ids = [e['job'] for e in submitted]
    p.require(len(set(ids)) == 103 and ids == account['exact_submitted_jobs'] and ids[-1] == FAILED_JOB,
              'Exact historical allocation identities')
    rows = {r['JobID']: r for r in account['rows'] if '.' not in r['JobID']}
    p.require(set(rows) == set(ids), 'Exact terminal allocation rows')
    jobs = []
    for pos, item in enumerate(submitted):
        row = rows[item['job']]
        seconds = int(row['ElapsedRaw'])
        expected = 'COMPLETED' if pos < PREFIX else 'CANCELLED by 1201'
        p.require(row['State'] == expected and row['ExitCode'] == '0:0' and
                  0 <= seconds <= item['task']['seconds'], 'Terminal scheduler state')
        jobs.append(dict(job=item['job'], task=item['task'], state=row['State'],
                         exit_code=row['ExitCode'], seconds=seconds))
    p.require(sum(j['seconds'] for j in jobs) == PRIOR_GPU and jobs[-1]['seconds'] == 63,
              'Keep all completed and cancelled costs')
    terminals = {e['job']: e for e in events if e['event'] == 'terminal'}
    p.require(set(terminals) == set(ids[:-1]), 'No missing successful terminal event')
    for job in jobs[:-1]:
        old = terminals[job['job']]
        p.require((old['state'], old['exit_code'], old['seconds']) ==
                  (job['state'], job['exit_code'], job['seconds']), 'Ledger/accounting match')
    tranches = [e for e in events if e['event'] == 'technical_tranche']
    p.require(len(tranches) == 1 and tranches[0]['projected_gpu_seconds'] == 238080 and
              tranches[0]['projected_storage_bytes'] == 2200301056, 'Retain included initial resource gate')
    p.require(p.sha(run/'BACKUP-REQUEST-failure-20260916.json') == FAILURE_REQUEST_SHA and
              p.sha(run/'BACKUP-ACK-failure-20260916.json') == FAILURE_ACK_SHA, 'Accepted failure backup seals')
    request = ct.json_read(run/'BACKUP-REQUEST-failure-20260916.json')
    receipt = ct.json_read(run/'BACKUP-ACK-failure-20260916.json')
    dirs = {name(s) for s in fixed[:PREFIX]}
    p.require(set(request['directories']) == dirs | {'failure-preservation-20260916'} and
              receipt['verified'] is True and receipt['request_sha256'] == FAILURE_REQUEST_SHA and
              receipt['archive_sha256'] == FAILURE_ARCHIVE_SHA, 'Prior completed coverage backed up')
    for spec in fixed[:PREFIX]:
        d = name(spec)
        p.require(p.sha(run/d/'sha256.txt') == request['seals'][d], 'Completed output seal preserved')
        check_meta(recovery_meta(run/d), spec)
    p.require({x.parent.name for x in run.glob('*/sha256.txt')} == set(request['directories']),
              'Unexpected sealed stage before recovery')
    for spec in fixed[PREFIX+1:]:
        d = name(spec)
        p.require(not (run/d).exists() and not (run/('tmp-'+d)).exists() and
                  not list(run.glob('slurm-'+d+'-*')), 'Unaccounted later work')
    p.require(not (run/'DISPATCH-FINAL.json').exists() and not (run/'terminal').exists() and
              not any((run/('BACKUP-REQUEST-'+s+'.json')).exists() for s in ('train','models','evaluation','terminal')),
              'No later stages opened')
    return jobs, request


def check_meta(meta, spec):
    p.require(meta.get('kind') == spec['kind'] and meta.get('index') == spec['index'] and
              meta.get('source_sha256') == SOURCE_SHA and meta.get('capsule_sha256') == p.OLD_CAPSULE_SHA and
              meta.get('technical_valid') is True and meta.get('protected_payload_reads') == 0 and
              meta.get('historical_decisions_changed') is False, 'Exact technical worker identity')
    if spec['gpu']:
        p.require(meta.get('reference') == spec['reference'] and meta.get('horizon') == spec['h'], 'Fixed source/horizon')


def recovery_meta(directory):
    # Retain the accepted seal reader; add only the actual top-level horizon
    # metadata spelling (the historical projection's "h" was absent).
    meta=technical_report(directory)
    for line in (Path(directory)/'REPORT.json').read_text().splitlines():
        if line.startswith('  "horizon":'):
            p.require('horizon' not in meta,'Duplicate technical horizon')
            meta['horizon']=json.loads('{'+line.strip().rstrip(',')+'}')['horizon']
    return meta


def prepare(source, run, approval, accounting, overlay, overlay_sha, target):
    a, _ = p.authorize(source, run, approval)
    p.require(a['source_sha256'] == SOURCE_SHA and p.sha(approval) == OLD_APPROVAL_SHA, 'Unchanged scientific approval')
    overlay_check(overlay, overlay_sha)
    jobs, request = prior_state(run, accounting)
    run = Path(run)
    partial = {}
    for d in ('breadth-94', 'tmp-breadth-94'):
        files = tree_inventory(run/d)
        preserved = run/'failure-preservation-20260916/auxiliary-run'/d
        p.require(files == tree_inventory(preserved), 'Interrupted bytes must already be preserved and backed up')
        partial[d] = files
    p.require(p.reservation(PRIOR_GPU, 0, bytes_used(run), p.grid()[PREFIX:]), 'Unchanged aggregate envelope')
    value = dict(researcher_approved=True,
        authorization='User YES to scoped backup monitoring repair, reuse of 102 completed outputs, and one replacement attempt for cancelled 301578; unchanged aggregate caps and science.',
        run=str(run), scientific_source=str(Path(source)), source_sha256=SOURCE_SHA,
        old_approval=str(Path(approval)), old_approval_sha256=OLD_APPROVAL_SHA,
        protocol_sha256=a['protocol_sha256'], role_manifest_sha256=a['role_manifest_sha256'], caps=p.CAPS,
        overlay=str(Path(overlay)), overlay_sha256=overlay_sha, accounting=str(Path(accounting)),
        accounting_sha256=ACCOUNT_SHA, original_dispatch_sha256=p.sha(run/'DISPATCH.jsonl'),
        original_stop_sha256=STOP_SHA, completed_prefix=PREFIX, prior_jobs=jobs,
        gpu_seconds=PRIOR_GPU, cpu_seconds=0, replacement_job=FAILED_JOB,
        replacement_task=p.task('breadth',94), remaining_tasks=p.grid()[PREFIX:],
        completed_seals={name(s):request['seals'][name(s)] for s in p.grid()[:PREFIX]},
        interrupted_files=partial, automatic_job_retries=False, max_additional_replacement_attempts=1,
        total_attempts_if_complete=451, scientific_changes=False, partial_outcomes_decoded=False)
    ct.json_write(target, value)
    return value


def relocate_interrupted(run, expected):
    """Move only the already-archived cancelled slot; exclusive destination, no deletion."""
    run = Path(run).resolve()
    p.require(set(expected) == {'breadth-94','tmp-breadth-94'}, 'Only cancelled allocation slot')
    target = run/'interrupted-attempt-301578'
    p.require(not target.exists(), 'No overwrite/repeated relocation')
    for d, files in expected.items():
        old = run/d
        p.require(old.resolve().parent == run and tree_inventory(old) == files, 'Exact relocation source')
    target.mkdir()
    for d, files in expected.items():
        (run/d).rename(target/d)
        p.require(tree_inventory(target/d) == files, 'Byte-identical relocation')
    ct.json_write(target/'RELOCATION.json',dict(original_job=FAILED_JOB, mapping={d:str(target/d) for d in expected},
        original_path_copy_in='failure-preservation-20260916/auxiliary-run',
        verified_external_archive_sha256=FAILURE_ARCHIVE_SHA, files=expected, scientific_outputs_valid=False))
    ct.seal(target)


def lease_valid(value, approval_sha, now):
    return (value.get('approval_sha256') == approval_sha and value.get('source_sha256') == SOURCE_SHA and
            value.get('external_mount') == '/mnt/d' and value.get('free_bytes',0) >= p.CAPS['backup_free_bytes'] and
            0 <= now-value.get('utc',0) <= 150)


def wait_live(control, approval_sha):
    deadline = time.monotonic()+180
    while True:
        p.require(not (control/'BACKUP-RECOVERY-STOP.json').exists(), 'Backup companion stopped')
        live = control/'BACKUP-LIVE.json'
        if live.exists() and lease_valid(ct.json_read(live), approval_sha, time.time()):
            return
        p.require(time.monotonic() < deadline, 'No fresh backup liveness; stop before next submission')
        time.sleep(10)


def dispatch(recovery, recovery_sha):
    recovery = Path(recovery)
    p.require(p.sha(recovery) == recovery_sha, 'Exact recovery authorization')
    r = ct.json_read(recovery); run = Path(r['run']); source = Path(r['scientific_source'])
    approval = Path(r['old_approval']); control = recovery.parent
    p.require(r['researcher_approved'] is True and r['caps'] == p.CAPS and r['source_sha256'] == SOURCE_SHA and
              r['replacement_task'] == p.task('breadth',94) and r['replacement_job'] == FAILED_JOB and
              r['remaining_tasks'] == p.grid()[PREFIX:] and r['max_additional_replacement_attempts'] == 1 and
              r['automatic_job_retries'] is False, 'Narrow authorized recovery only')
    p.authorize(source, run, approval)
    p.require(p.sha(approval) == OLD_APPROVAL_SHA, 'Original execution approval')
    overlay_check(r['overlay'], r['overlay_sha256'])
    p.require(Path(__file__).resolve().parent == Path(r['overlay']).resolve(), 'Run sealed recovery controller')
    jobs, request = prior_state(run, r['accounting'])
    p.require(jobs == r['prior_jobs'] and p.sha(run/'DISPATCH.jsonl') == r['original_dispatch_sha256'],
              'Approved historical prefix unchanged')
    p.require(not Path('/proc/3489337').exists(), 'Old controller must remain absent')
    ready = ct.json_read(control/'BACKUP-RECOVERY-READY.json')
    p.require(ready.get('approval_sha256') == recovery_sha and ready.get('failure_archive_sha256') == FAILURE_ARCHIVE_SHA and
              ready.get('failure_backup_verified') is True, 'Existing external failure backup verified')
    wait_live(control, recovery_sha)
    p.require(2*bytes_used(source)+bytes_used(control)+2*bytes_used(r['overlay']) < p.CAPS['source_bytes'],
              'Whole source/control reserve')
    ct.json_write(run/'RECOVERY-CLAIM.json',dict(approval_sha256=recovery_sha, overlay_sha256=r['overlay_sha256'],utc=time.time()))
    gpu=PRIOR_GPU; cpu=0; active=None; spec=None
    backed=set(request['directories'])
    with (run/'RECOVERY-DISPATCH.jsonl').open('x',buffering=1) as log:
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
                  cancelled_cost_seconds=63,gpu_seconds=gpu,additional_replacement_limit=1)
            relocate_interrupted(run,r['interrupted_files'])
            evidence=run/'recovery-evidence-301578';evidence.mkdir()
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
                p.require(2*bytes_used(source)+bytes_used(control)+2*bytes_used(r['overlay'])<p.CAPS['source_bytes'],
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
            for path in (run/'DISPATCH.jsonl',run/'DISPATCH-STOP.json',run/'RECOVERY-DISPATCH.jsonl',recovery):
                with path.open('rb') as src,(terminal/path.name).open('xb') as dst:shutil.copyfileobj(src,dst)
            ct.seal(terminal);backup('terminal');ct.json_write(run/'DISPATCH-FINAL.json',summary)
        except BaseException as exc:
            if active and active.isdigit():
                try:command('scancel',active)
                except Exception:pass
            stop=dict(reason=str(exc),type=type(exc).__name__,active_job=active,gpu_seconds=gpu,cpu_wall_seconds=cpu,
                unresolved_reservation_seconds=spec['seconds'] if active and spec else 0,
                requires_terminal_accounting_and_failure_backup=True,no_automatic_retry=True)
            event('stopped',**stop);ct.json_write(run/'RECOVERY-STOP.json',stop)
            raise


if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('mode',choices=['prepare','dispatch'])
    for field in ('source','run','approval','accounting','overlay','overlay-sha','target','recovery','recovery-sha'):
        cli.add_argument('--'+field)
    args=cli.parse_args()
    if args.mode=='prepare':
        prepare(args.source,args.run,args.approval,args.accounting,args.overlay,args.overlay_sha,args.target)
    else:dispatch(args.recovery,args.recovery_sha)
