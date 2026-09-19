"""LGP-RB1: fixed frozen-model refinement-budget comparison; no model imports."""
from pathlib import Path
import json
import lgp1_contract as old

DOC='docs/local-goal-search-budget-20260919'
NAME='local-goal-search-budget-20260919'
ROOT=old.ROOT
OLD_SOURCE=ROOT/'snapshots/local-goal-proposals-20260918-b54a55b16bcb83a5'
OLD_RUN=ROOT/'experiments/local-goal-proposals-20260918/run-b54a55b16bcb83a5'
OLD_FITS=ROOT/'experiments/local-goal-proposals-20260918/run-b6d307bf26325ba6'
OLD_SOURCE_SHA='b54a55b16bcb83a5092f15703a63fadb81fdbce3fa91f4e6a21b907c934cf361'
INPUT_SHA='b21bac97520696b8bb2008a3cfef3f5188d4c59dd117bc158cc2fe2e86ff5aaa'
FREEZE_SHA='a8a5a0ff456cd870e540f838d2c8b62d00b542be6d7a2da53b377fbd91cbc305'
CAPS=dict(gpu_seconds=70320,cpu_seconds=7200,worker_bytes=2_000_000_000,
          control_bytes=100_000_000,total_with_history_bytes=8_000_000_000,episode_bytes=10_000_000)
MANIFEST='LGP-RB1-SOURCE-MANIFEST.sha256'
sha,read,write,require=old.sha,old.read,old.write,old.require

def grid(refs):
    require(len(refs)==len(set(refs))==32 and all(type(r) is int and 0<=r<1600 for r in refs),'Exact development role')
    tasks=[dict(name='compatibility-'+f,kind='compatibility',family=f,seed=8301,reference=refs[0],gpu=True,seconds=600)
           for f in old.FAMILIES]
    tasks += [dict(name=f'evaluation-r{n}-{f}-{s}-{r}',kind='evaluation',populations=n,family=f,seed=s,reference=r,gpu=True,seconds=180)
              for n in (1,5) for f in old.FAMILIES for s in old.SEEDS for r in refs]
    tasks += [dict(name='analysis',kind='analysis',gpu=False,seconds=7200)]
    require(len(tasks)==387 and sum(t['seconds'] for t in tasks if t['gpu'])==CAPS['gpu_seconds'],'Exact envelope')
    return tasks

def authorize(source,approval):
    source=Path(source);old.verify(source,MANIFEST);a=read(approval)
    require(a.get('execution_authorized') is True,'Preparation disabled: separate researcher approval required')
    refs=read(source/old.DOC/'DATA-ROLES.json')['development_reference_indices']
    expected=template(source)
    expected['execution_authorized']=True
    require(a==expected,'Exact separately approved execution contract')
    require(sha(source/old.DOC/'INPUTS.json')==INPUT_SHA,'Unchanged executed input lock')
    require(refs==read(source/DOC/'REUSE.json')['references'] and grid(refs)==read(source/DOC/'GRID.json'),'Same sources and executable grid')
    return a,grid(refs)

def template(source):
    source=Path(source)
    return dict(study='LGP-RB1',execution_authorized=False,source_sha256=sha(source/MANIFEST),
        protocol_sha256=sha(source/DOC/'PROTOCOL.md'),reuse_sha256=sha(source/DOC/'REUSE.json'),
        grid_sha256=sha(source/DOC/'GRID.json'),input_sha256=INPUT_SHA,caps=CAPS,
        new_main_episodes=768,reused_main_episodes=384,technical_full_episodes=0,
        technical_first_decisions=16,new_fits=0,new_optimizer_updates=0,
        gpu_allocations=386,cpu_allocations=1,automatic_retry=False,
        backup_volume_id='0a2f1ba9-0000-0000-0000-100000000000',
        backup_destination='D:/THESIS-BACKUPS/'+NAME)

def verify_reuse(source,*,all_workers=True):
    lock=read(Path(source)/DOC/'REUSE.json')
    require(sha(Path(source)/old.DOC/'INPUTS.json')==INPUT_SHA,'New source preserves exact old inputs')
    for name,digest in lock['unchanged_scientific_components'].items():
        require(sha(Path(source)/name)==digest,'Unchanged scientific component: '+name)
    require(sha(OLD_SOURCE/'LGP1-SOURCE-MANIFEST.sha256')==OLD_SOURCE_SHA,'Executed LGP1 source')
    old.verify(OLD_SOURCE,'LGP1-SOURCE-MANIFEST.sha256')
    require(sha(OLD_SOURCE/old.DOC/'INPUTS.json')==INPUT_SHA,'Executed input lock')
    require(sha(OLD_RUN/'PRE-EVALUATION-FREEZE.json')==FREEZE_SHA,'Original model freeze')
    require(sha(OLD_RUN/'analysis/sha256.txt')==lock['aggregate_seal_sha256'],'Original aggregate seal')
    for name,entry in lock['models'].items():
        root=OLD_FITS/name
        old.verify(root)
        require(sha(root/'model.pt')==entry['model_sha256'] and sha(root/'sha256.txt')==entry['seal'],'Same six final models')
    if all_workers:
        for entry in lock['main_workers']:
            root=OLD_RUN/entry['name'];old.verify(root)
            require(sha(root/'sha256.txt')==entry['seal'],'Historical worker seal')
            meta=read(root/'TECHNICAL.json')
            require(meta['task']==entry['task'] and meta['complete'] and meta['models_unchanged'] and
                    meta['source_sha256']==OLD_SOURCE_SHA and meta['approval_sha256']==lock['canonical_approval_sha256'],'Original worker provenance')
    return lock

def historical_size():
    # Shared historical bytes are counted, never copied into new worker roots.
    return old.size(OLD_SOURCE)+old.size(OLD_RUN)+sum(old.size(p) for _,p in old.preserved_paths(OLD_RUN))

def control_path(run):return ROOT/'staging'/(NAME+'-'+Path(run).name.removeprefix('run-'))

def storage(source,run):
    source,run=Path(source),Path(run)
    workers=sum(old.size(p) for p in run.iterdir() if p.is_dir() and p.name!='final-preservation')
    control=old.size(source)+sum(p.stat().st_size for p in run.iterdir() if p.is_file())+old.size(control_path(run))
    total=old.size(source)+old.size(run)+old.size(control_path(run))+historical_size()
    require(workers<=CAPS['worker_bytes'] and control<=CAPS['control_bytes'] and total<=CAPS['total_with_history_bytes'],'Preserved storage cap')
    return dict(new_worker_bytes=workers,new_source_control_bytes=control,total_with_history_bytes=total)
