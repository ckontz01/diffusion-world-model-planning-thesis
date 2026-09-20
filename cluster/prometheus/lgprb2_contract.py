"""RB2 fixed source-disjoint replication. Host-safe; no research imports."""
import hashlib,json
from pathlib import Path
import lgp1_contract as old
import lgprb1_contract as rb1

NAME='local-goal-source-replication-20260920'
DOC='docs/'+NAME
MANIFEST='LGP-RB2-SOURCE-MANIFEST.sha256'
ROOT=old.ROOT
SEEDS=old.SEEDS
ARMS=(('gmm',5),('diffusion',5),('gmm',30),('diffusion',30))
CAPS=dict(gpu_seconds=460800,cpu_seconds=7200,worker_bytes=8_000_000_000,
          control_bytes=200_000_000,total_with_history_bytes=24_000_000_000,
          episode_bytes=10_000_000,endpoint_bytes=50000,analysis_bytes=200_000_000,main_job_bytes=5_000_000)
sha,read,write,require=old.sha,old.read,old.write,old.require
RB1_SOURCE=ROOT/'snapshots/local-goal-search-budget-20260919-a0bcdb48029909e0'
RB1_RUN=ROOT/'experiments/local-goal-search-budget-20260919/run-a0bcdb48029909e0'
RB1_SOURCE_SHA='a0bcdb48029909e0b54a86d8b59c54fc4fa60a3734a9634c761e5caea4c9778b'
FREEZE_SHA=rb1.FREEZE_SHA

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def cell_name(cell):return f"{cell['family']}-r{cell['populations']}-h{cell['horizon']}"

def allocate(roles,universe=range(1600)):
    universe=set(universe)
    require(universe==set(range(1600)),'Exact already-exposed population')
    require(roles and all(type(r) is int and r in universe for ids in roles.values() for r in ids),'Registered role namespace')
    excluded=set().union(*(set(ids) for ids in roles.values()))
    eligible=sorted(universe-excluded,key=lambda r:(hashlib.sha256(f'lgp-rb2-source-v1|{r}'.encode()).hexdigest(),r))
    require(len(eligible)>=512,'Fewer than 512 eligible sources; no shrink/substitution')
    return dict(ordered_references=eligible[:512],eligible_count=len(eligible),excluded_union_count=len(excluded),
                exclusion_roles={k:sorted(set(v)) for k,v in sorted(roles.items())},
                role_counts={k:len(set(v)) for k,v in sorted(roles.items())},
                selection_rule='SHA256(lgp-rb2-source-v1|<decimal-id>), integer tie; first 512',
                allocation_digest=digest(eligible[:512]),remaining_eligible=len(eligible)-512)

def grid(refs):
    require(len(refs)==len(set(refs))==512 and all(type(r) is int and 0<=r<1600 for r in refs),'Exact RB2 source role')
    blocks=[(r,s) for r in refs for s in SEEDS]
    # Assign rotations by identifier-hash rank: each of 8 cells occupies each
    # position exactly 192 times across the complete 1536-block grid.
    ranked=sorted(blocks,key=lambda x:(hashlib.sha256(f'lgp-rb2-order-v1|{x[0]}|{x[1]}'.encode()).hexdigest(),x))
    rotation={key:i%8 for i,key in enumerate(ranked)}
    cells=[dict(family=f,populations=n,horizon=h) for f,n in ARMS for h in (75,150)]
    tasks=[]
    for i,(r,s) in enumerate(blocks):
        k=rotation[r,s];ordered=cells[k:]+cells[:k]
        tasks.append(dict(name=f'evaluation-{s}-{r}',kind='evaluation',reference=r,seed=s,
                          gpu=True,seconds=300,technical_tranche=i<4,episodes=ordered))
    tasks.append(dict(name='analysis',kind='analysis',gpu=False,seconds=7200))
    return tasks

def template(source):
    source=Path(source)
    return dict(study='LGP-RB2',execution_authorized=False,source_sha256=sha(source/MANIFEST),
        protocol_sha256=sha(source/DOC/'PROTOCOL.md'),roles_sha256=sha(source/DOC/'DATA-ROLES.json'),
        grid_sha256=sha(source/DOC/'GRID.json'),input_sha256=sha(source/DOC/'INPUTS.json'),
        reuse_sha256=sha(source/DOC/'REUSE.json'),caps=CAPS,main_episodes=12288,main_gpu_allocations=1536,
        cpu_allocations=1,technical_tranche_included=4,new_fits=0,new_optimizer_updates=0,
        bootstrap_seed=20260920,bootstrap_resamples=10000,automatic_retry=False,
        backup_volume_id='0a2f1ba9-0000-0000-0000-100000000000',backup_destination='D:/THESIS-BACKUPS/'+NAME)

def authorize(source,approval):
    source=Path(source);old.verify(source,MANIFEST);a=read(approval)
    require(a.get('execution_authorized') is True,'Preparation disabled: explicit delegated execution instruction required')
    expected=template(source);expected['execution_authorized']=True
    require(a==expected,'Exact separately frozen execution contract')
    roles=read(source/DOC/'DATA-ROLES.json')
    require(allocate(roles['exclusion_roles'])=={k:roles[k] for k in allocate(roles['exclusion_roles'])},'Identifier allocation drift')
    tasks=grid(roles['ordered_references']);require(tasks==read(source/DOC/'GRID.json'),'Exact packaged grid')
    require(set(read(source/DOC/'INPUTS.json')['references'])==set(map(str,roles['ordered_references'])),'Only RB2 payload allowlist')
    return a,tasks

def verify_models(source):
    lock=read(Path(source)/DOC/'REUSE.json')
    for name,entry in lock['unchanged_files'].items():
        require(sha(Path(source)/name)==entry,'Unchanged scientific source '+name)
    require(sha(rb1.OLD_RUN/'PRE-EVALUATION-FREEZE.json')==FREEZE_SHA,'Original all-six freeze')
    for name,entry in lock['models'].items():
        root=rb1.OLD_FITS/name;old.verify(root)
        require(sha(root/'model.pt')==entry['model_sha256'] and sha(root/'sha256.txt')==entry['seal'],'Original six model identities')
    return lock

def authenticate_inputs(source):
    lock=read(Path(source)/DOC/'INPUTS.json')
    for name,d in lock['files'].items():
        if name not in lock['payload_files']:require(sha(name)==d,'Runtime/input identity '+name)
    return lock

def control_path(run):return ROOT/'staging'/(NAME+'-'+Path(run).name.removeprefix('run-'))

def historical_paths():
    return [('rb1-source',RB1_SOURCE),('rb1-run',RB1_RUN),('rb1-control',rb1.control_path(RB1_RUN)),
            ('lgp1-source',rb1.OLD_SOURCE),('lgp1-run',rb1.OLD_RUN)]+old.preserved_paths(rb1.OLD_RUN)

def storage(source,run):
    source,run=Path(source),Path(run)
    workers=sum(old.size(p) for p in run.iterdir() if p.is_dir() and p.name!='final-preservation')
    controls=old.size(source)+sum(p.stat().st_size for p in run.iterdir() if p.is_file())+old.size(control_path(run))
    history=sum(old.size(p) for _,p in historical_paths())
    total=old.size(source)+old.size(run)+old.size(control_path(run))+history
    reserved=1536*CAPS['main_job_bytes']+CAPS['analysis_bytes']+CAPS['control_bytes']
    require(history+2*reserved+85_000_000<=CAPS['total_with_history_bytes'],'Full work plus final archive reservation')
    require(workers<=CAPS['worker_bytes'] and controls<=CAPS['control_bytes'] and total<=CAPS['total_with_history_bytes'],'Storage envelope')
    return dict(new_worker_bytes=workers,new_source_control_bytes=controls,historical_bytes=history,total_with_history_bytes=total)
