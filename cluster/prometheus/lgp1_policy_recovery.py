"""Explicit one-use policy recovery. Reuse every cache/fit; never execute either."""
import json,os,subprocess,time
from pathlib import Path
import lgp1_contract as c
from lgp1_validation_recovery import PRIOR as CACHE_RUN,FIRST,CACHE_SEAL

PRIOR=c.ROOT/'experiments/local-goal-proposals-20260918/run-b6d307bf26325ba6'
LEDGER='746b42c91685237004ef4f0d4fd0055a46357e861647df0bca4a41ba881e47f4'
FREEZE='a8a5a0ff456cd870e540f838d2c8b62d00b542be6d7a2da53b377fbd91cbc305'
FAILURE='d53a0c2a910a700b572b41d6b24eecccce073b43b1a74b80cff6cff48d2e5beb'
JOBS={'301977':['FAILED','1:0','46'],'301979':['COMPLETED','0:0','3388'],
      '301980':['FAILED','1:0','252'],'301981':['COMPLETED','0:0','57'],
      '301982':['COMPLETED','0:0','293'],'301983':['COMPLETED','0:0','297'],
      '301984':['COMPLETED','0:0','506'],'301985':['COMPLETED','0:0','507'],
      '301986':['COMPLETED','0:0','509'],'301987':['FAILED','1:0','22']}

def contract():
    return dict(failed_job='301987',prior_ledger_sha256=LEDGER,original_freeze_sha256=FREEZE,
                failure_seal_sha256=FAILURE,cache_seal_sha256=CACHE_SEAL,
                prior_gpu_seconds=5877,prior_cpu_seconds=0,prior_gpu_allocations=10,
                reused_coordinates=7,remaining_gpu_allocations=196,remaining_cpu_allocations=1,
                optimizer_updates_to_repeat=0,automatic_retry=False)

def authorize(a):
    c.require(not a.get('recovery') and not a.get('validation_recovery'),'Separate explicit policy recovery')
    c.require(a['policy_recovery']==contract(),'Exact policy recovery contract')
    c.require(5877+196*1200<=c.CAPS['gpu_seconds'],'Prior plus complete remaining reservations')

def roots(a):
    from lgp1_validation_recovery import roots as old_roots
    # Old root function only uses the source hash to identify that run's control.
    old=old_roots(dict(source_sha256='b6d307bf26325ba63956a9d615d433a41a8fba5f13b7cdbab51a15a701028e1b'))
    old=[('validation-control' if n=='new-control' else n,p) for n,p in old]
    return old+[
        ('validation-run',PRIOR),
        ('validation-source',c.ROOT/'snapshots/local-goal-proposals-20260918-b6d307bf26325ba6'),
        ('new-control',c.ROOT/('staging/lgp1-policy-recovery-'+a['source_sha256'][:16]))]

def reused_root(spec):
    c.require(spec['kind'] in ('cache','fit'),'Only cache/fit reuse')
    return (CACHE_RUN if spec['kind']=='cache' else PRIOR)/spec['name']

def verify_reuse(specs,a):
    from lgp1_verify import task
    c.require(c.sha(PRIOR/'PRE-EVALUATION-FREEZE.json')==FREEZE,'Original freeze identity')
    frozen=c.read(PRIOR/'PRE-EVALUATION-FREEZE.json')
    fits=[s for s in specs if s['kind']=='fit']
    c.require(set(frozen['models'])==set(frozen['seals'])=={s['name'] for s in fits},'Exact six frozen fits')
    for spec in specs[:7]:
        root=reused_root(spec)
        seal=CACHE_SEAL if spec['kind']=='cache' else frozen['seals'][spec['name']]
        c.require(c.sha(root/'sha256.txt')==seal,'Exact reused worker seal')
        meta=task(root,spec);origin=c.read(root.parent/'APPROVAL.json')
        c.require(origin['input_sha256']==a['input_sha256'] and meta['source_sha256']==origin['source_sha256']
                  and meta['approval_sha256']==c.sha(root.parent/'APPROVAL.json'),'Reuse input/source/approval')
        if spec['kind']=='fit':c.require(c.sha(root/'model.pt')==frozen['models'][spec['name']],'Frozen model bytes')
    return frozen

def preflight(source,a):
    authorize(a);specs=c.execution_grid(source,a)
    c.require(c.sha(PRIOR/'DISPATCH.jsonl')==LEDGER,'Stopped ledger identity')
    failed=PRIOR/'technical-gmm-8301-1269'
    c.require(c.sha(failed/'sha256.txt')==FAILURE,'Failed technical seal');c.verify(failed)
    c.require({p.name for p in failed.iterdir()}=={'FAILURE.json','sha256.txt'},'No episode output in failed task')
    verify_reuse(specs,a)
    text=subprocess.check_output(['sacct','-X','-n','-P','--starttime=2026-09-18',
            '--format=JobID,JobName%80,State,ExitCode,ElapsedRaw'],text=True)
    observed={v[0]:v[2:5] for line in text.splitlines() if len(v:=line.strip().split('|'))>=5 and v[1].startswith('lgp1-')}
    c.require(observed==JOBS,'Reconcile exact terminal attempts; reject unknown/live job')
    c.require(sum(int(v[2]) for v in observed.values())==5877,'Every prior allocation charged')
    for name,path in roots(a):
        if name.endswith('-control') and name!='new-control':
            process=c.read(path/'CONTROLLER-PROCESS.json');p=Path('/proc',str(process['pid']),'stat')
            c.require(not p.exists() or p.read_text().rsplit(')',1)[1].split()[19]!=process['start_ticks'],
                      'Historical controller is still active')
    return dict(prior_jobs=observed,charged_gpu_seconds=5877,charged_cpu_seconds=0,
                original_freeze_sha256=FREEZE,cache_seal_sha256=CACHE_SEAL,
                reuse_count=7,remaining_gpu_reservation=196*1200,combined_gpu_reservation=241077)

def run(source,approval_file,run,approved):
    from lgp1_dispatch import Controller,Slurm
    from lgp1_verify import task
    c.require(run.parent.resolve()==c.ROOT/'experiments/local-goal-proposals-20260918' and
              run.name=='run-'+approved['source_sha256'][:16] and not run.exists(),'Exclusive new policy recovery')
    c.require(set(run.parent.iterdir())=={FIRST,CACHE_RUN,PRIOR},'No other run or previous policy recovery')
    evidence=preflight(source,approved);specs=c.execution_grid(source,approved)
    run.mkdir(exist_ok=False);c.write(run/'APPROVAL.json',approved)
    c.write(run/'PRIOR-ALLOCATION-ACCOUNTING.json',evidence)
    # Preserve byte-for-byte original pre-evaluation freeze and its timestamp.
    with (run/'PRE-EVALUATION-FREEZE.json').open('xb') as f:f.write((PRIOR/'PRE-EVALUATION-FREEZE.json').read_bytes())
    c.require(c.sha(run/'PRE-EVALUATION-FREEZE.json')==FREEZE,'Copied original freeze')
    def record(row):
        row['unix']=time.time()
        with (run/'DISPATCH.jsonl').open('a') as f:f.write(json.dumps(row,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
    historical=[json.loads(s) for p in (CACHE_RUN,PRIOR) for s in (p/'DISPATCH.jsonl').read_text().splitlines()]
    reused=[]
    for spec in specs[:7]:
        row=next(r for r in historical if r['event']=='terminal' and r['task']==spec and r['state']=='COMPLETED' and r['exit_code']=='0:0')
        reused.append(row)
        record(dict(event='reused',task=spec,job=row['job'],root=str(reused_root(spec)),seal=c.sha(reused_root(spec)/'sha256.txt')))
    c.write(run/'REUSED-COORDINATES.json',dict(coordinates=7,optimizer_updates=72000,
            optimizer_updates_this_recovery=0,source_roots=[str(CACHE_RUN),str(PRIOR)],original_freeze_sha256=FREEZE))
    technical=[]
    def check(spec):
        task(c.task_root(run,spec),spec)
        if spec['kind']=='technical':
            technical.append(spec['name'])
            if len(technical)==4:
                c.write(run/'TECHNICAL-STAGE-PASSED.json',dict(unix=time.time(),tasks=technical,
                    seals={n:c.sha(run/n/'sha256.txt') for n in technical},performance_selection=False))
    def freeze(stage,completed):
        if stage=='models':
            c.require(len(completed)==7,'Seven reused successful coordinates')
            verify_reuse(specs,approved)
            c.require(c.sha(run/'PRE-EVALUATION-FREEZE.json')==FREEZE,'Original model freeze preserved')
        else:
            c.require(len(completed)==203 and len(technical)==4,'Complete GPU coordinates')
            c.write(run/'PRE-ANALYSIS-ACCOUNTING.json',dict(jobs=completed,prior_allocations=evidence,
                reused_coordinates=7,avoid_double_count='All seven reused successes are already in prior 5877 GPU seconds'))
    def bytes_used():
        sizes=c.storage(source,run)
        return sizes['worker_bytes']+sizes['source_control_log_bytes']-c.size(source)
    ctl=Controller(specs[7:],Slurm(source,run/'APPROVAL.json',run),record,bytes_used,check,freeze,c.size(source))
    ctl.gpu=5877;ctl.completed=reused
    try:
        final=ctl.run();final['storage']=c.storage(source,run)
        final.update(prior_allocations=evidence,reused_coordinates=7,new_allocations=197,
                     attempts_including_prior=207,gpu_attempts_including_prior=206,
                     optimizer_updates_this_recovery=0,remote_bytes_before_archive=final['storage']['total_remote_bytes'])
        c.write(run/'COMPUTE-COMPLETE.json',final)
    except BaseException as exc:
        c.write(run/'STOP.json',dict(error=str(exc),gpu_seconds=ctl.gpu,cpu_seconds=ctl.cpu,
                no_retry=True,reused_coordinates=7,new_terminal_attempts=len(ctl.completed)-7));raise
