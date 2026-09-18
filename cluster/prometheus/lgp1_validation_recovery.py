"""One expressly authorized validation-only recovery; never retrains saved GMM."""
import json,subprocess,time,os
from pathlib import Path
import lgp1_contract as c

PRIOR=c.ROOT/'experiments/local-goal-proposals-20260918/run-b96b797315320184'
FIRST=c.ROOT/'experiments/local-goal-proposals-20260918/run-b514472d1d8a7f55'
CACHE_SEAL='7923e9590e3c520c44ac3a36c2bf9000f6d91a4b06a6333f528f3930a4580734'
FIT_SEAL='e28e6e56366d8ea3c90de6fed9fd91a5532dfd13da8a504e87027fd2e8fe454d'
MODEL='2283b7aef1b38d50d546beeb6f73ad36e9fbc6f1fb1bc5001b830d182f062286'
LEDGER='90c18122dbdb134732f503c6d7cb8fbb12f85b1f571817a2c68bf795b963cd4a'

def roots(approval):
    return [('failed-run',FIRST),('prior-run',PRIOR),
        ('failed-source',c.ROOT/'snapshots/local-goal-proposals-20260918-b514472d1d8a7f55'),
        ('prior-source',c.ROOT/'snapshots/local-goal-proposals-20260918-b96b797315320184'),
        ('failed-control',c.ROOT/'staging/lgp1-execution-b514472d1d8a7f55'),
        ('prior-control',c.ROOT/'staging/lgp1-action-recovery-b96b797315320184'),
        ('new-control',c.ROOT/('staging/lgp1-validation-recovery-'+approval['source_sha256'][:16]))]

def authorize(approval):
    r=approval['validation_recovery']
    c.require(not approval.get('recovery'),'Distinct explicit recovery binding')
    c.require(r==dict(failed_job='301980',cache_job='301979',prior_gpu_seconds=3686,prior_cpu_seconds=0,
        prior_gpu_allocations=3,validation_seconds=14100,cache_seal_sha256=CACHE_SEAL,
        fit_seal_sha256=FIT_SEAL,model_sha256=MODEL,prior_ledger_sha256=LEDGER,
        automatic_retry=False,optimizer_updates_to_repeat=0),'Exact validation recovery contract')

def preflight(approval):
    authorize(approval)
    c.require(c.sha(PRIOR/'DISPATCH.jsonl')==LEDGER,'Prior ledger identity')
    c.require(c.sha(PRIOR/'cache/sha256.txt')==CACHE_SEAL and c.sha(PRIOR/'fit-gmm-8301/sha256.txt')==FIT_SEAL,'Prior seals')
    c.verify(PRIOR/'cache');c.verify(PRIOR/'fit-gmm-8301')
    c.require(c.sha(PRIOR/'fit-gmm-8301/model.pt')==MODEL,'Prior final model')
    final=c.read(PRIOR/'fit-gmm-8301/FINAL-CHECKPOINT.json')
    c.require(final==dict(selection='fixed_final',updates=12000,sha256=MODEL),'Saved full training completion')
    old=c.read(PRIOR/'APPROVAL.json')
    c.require(old['input_sha256']==approval['input_sha256'],'Unchanged inputs')
    meta=c.read(PRIOR/'cache/TECHNICAL.json')
    c.require(meta['complete'] and meta['source_sha256']==old['source_sha256'] and
              meta['approval_sha256']==c.sha(PRIOR/'APPROVAL.json'),'Reused cache source/approval')
    from lgp1_verify import task
    task(PRIOR/'cache',dict(name='cache',kind='cache',gpu=True,seconds=14340))
    text=subprocess.check_output(['sacct','-X','-n','-P','-j','301977,301979,301980',
        '--format=JobID,State,ExitCode,ElapsedRaw'],text=True)
    observed={v[0]:v[1:4] for line in text.splitlines() if (v:=line.strip().split('|'))[0]}
    c.require(observed=={'301977':['FAILED','1:0','46'],'301979':['COMPLETED','0:0','3388'],
        '301980':['FAILED','1:0','252']},'Fresh accounting exact terminal jobs')
    text=subprocess.check_output(['sacct','-X','-n','-P','--starttime=2026-09-18','--format=JobID,JobName'],text=True)
    ids={x.split('|')[0] for x in text.splitlines() if len(x.split('|'))>1 and x.split('|')[1].startswith('lgp1-')}
    c.require(ids==set(observed),'Unrecorded prior or live LGP1 job')
    for key,path in roots(approval):
        if key in ('failed-control','prior-control'):
            proc=c.read(path/'CONTROLLER-PROCESS.json');p=Path('/proc',str(proc['pid']),'stat')
            c.require(not p.exists() or p.read_text().rsplit(')',1)[1].split()[19]!=proc['start_ticks'],
                      'Old controller still active')
    return dict(prior_jobs=observed,charged_gpu_seconds=3686,cache_seal=CACHE_SEAL,model_sha256=MODEL)

def run(source,approval_file,run,approved):
    from lgp1_dispatch import Controller,Slurm
    from lgp1_verify import task
    c.require(run.parent.resolve()==c.ROOT/'experiments/local-goal-proposals-20260918' and
        run.name=='run-'+approved['source_sha256'][:16] and not run.exists(),'Exclusive recovery namespace')
    c.require(set(run.parent.iterdir())=={FIRST,PRIOR},'No repeated recovery or unexpected run')
    evidence=preflight(approved)
    run.mkdir(exist_ok=False);c.write(run/'APPROVAL.json',approved)
    c.write(run/'REUSED-CACHE.json',dict(root=str(PRIOR/'cache'),seal=CACHE_SEAL,source=c.read(PRIOR/'APPROVAL.json')['source_sha256']))
    c.write(run/'PRIOR-ALLOCATION-ACCOUNTING.json',evidence)
    specs=c.execution_grid(source,approved)
    def record(row):
        row['unix']=time.time()
        with (run/'DISPATCH.jsonl').open('a') as f:f.write(json.dumps(row,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
    prior_rows=[json.loads(x) for x in (PRIOR/'DISPATCH.jsonl').read_text().splitlines()]
    reused=next(x for x in prior_rows if x['event']=='terminal' and x['job']=='301979')
    record(dict(event='reused',job='301979',task=specs[0],root=str(PRIOR/'cache'),seal=CACHE_SEAL))
    def check(spec):task(c.task_root(run,spec),spec)
    def freeze(stage,completed):
        if stage=='models':
            c.require(len(completed)==7,'Reused cache plus all six completed fits')
            fits=[s for s in specs if s['kind']=='fit']
            for s in fits:check(s)
            c.require(c.sha(run/'fit-gmm-8301/model.pt')==MODEL,'Saved first GMM unchanged')
            c.write(run/'PRE-EVALUATION-FREEZE.json',dict(unix=time.time(),
                models={s['name']:c.sha(run/s['name']/'model.pt') for s in fits},
                seals={s['name']:c.sha(run/s['name']/'sha256.txt') for s in fits}))
        else:
            c.require(len(completed)==203,'Complete GPU coordinates before analysis')
            c.write(run/'PRE-ANALYSIS-ACCOUNTING.json',dict(jobs=completed,prior_allocations=evidence,
                reused_cache_job='301979',avoid_double_count='Cache is included in prior 3686s, not charged again'))
    def bytes_used():
        sizes=c.storage(source,run)
        return sizes['worker_bytes']+sizes['source_control_log_bytes']-c.size(source)
    ctl=Controller(specs[1:],Slurm(source,run/'APPROVAL.json',run),record,bytes_used,check,freeze,c.size(source))
    ctl.gpu=3686;ctl.completed=[reused]
    try:
        final=ctl.run();final['storage']=c.storage(source,run)
        final.update(prior_allocations=evidence,reused_coordinates=1,new_allocations=203,
                     attempts_including_prior=206,gpu_attempts_including_prior=205,
                     remote_bytes_before_archive=final['storage']['total_remote_bytes'])
        c.write(run/'COMPUTE-COMPLETE.json',final)
    except BaseException as e:
        c.write(run/'STOP.json',dict(error=str(e),gpu_seconds=ctl.gpu,cpu_seconds=ctl.cpu,
            no_retry=True,preserved_attempts=len(ctl.completed)-1,cache_reused=True));raise
