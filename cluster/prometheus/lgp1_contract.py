"""LGP1 exact tasks, authentication and exclusive seals. No model imports."""
import hashlib,json,os
from pathlib import Path

ROOT=Path('/lustreFS/data/superworld/ckontzias/thesis')
DOC='docs/local-goal-proposals-20260918'
SEEDS=(8301,8302,8303)
FAMILIES=('gmm','diffusion')
CAPS=dict(gpu_seconds=336000,cpu_seconds=7200,remote_bytes=12_000_000_000,
          worker_bytes=5_900_000_000,control_bytes=200_000_000,episode_bytes=10_000_000)
def require(x,message):
    if not x: raise RuntimeError(message)
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''): h.update(block)
    return h.hexdigest()
def read(p): return json.loads(Path(p).read_text())
def write(p,v):
    with Path(p).open('x',encoding='utf8',newline='\n') as f:
        json.dump(v,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')
def size(root): return sum(p.stat().st_size for p in Path(root).rglob('*') if p.is_file())

def storage(source,run):
    run=Path(run);workers=sum(size(p) for p in run.iterdir() if p.is_dir() and p.name!='final-preservation')
    control=size(source)+sum(p.stat().st_size for p in run.iterdir() if p.is_file())
    require(workers<=CAPS['worker_bytes'] and control<=CAPS['control_bytes'],'Worker or source/control/log cap')
    require(size(source)+size(run)<=CAPS['remote_bytes'],'Total remote cap')
    return dict(worker_bytes=workers,source_control_log_bytes=control)
def verify(root,manifest='sha256.txt'):
    root=Path(root).resolve();names=[]
    for line in (root/manifest).read_text().splitlines():
        digest,name=line.split('  ',1);p=root/name
        require(name not in names and root in p.resolve().parents and not p.is_symlink(),'Unsafe seal')
        require(sha(p)==digest,'Hash mismatch: '+name);names.append(name)
    require(names,'Empty seal')
    if manifest=='sha256.txt':
        actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p.name!='sha256.txt'}
        require(actual==set(names),'Unsealed or missing worker artifact')
    else:
        actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
        require(actual-set(names)<= {manifest,'APPROVAL-TEMPLATE.json'},'Unmanifested source file')
    return names
def seal(root):
    root=Path(root)
    paths=sorted(p for p in root.rglob('*') if p.is_file())
    require(paths and not any(p.is_symlink() for p in paths),'Unsafe/empty output')
    with (root/'sha256.txt').open('x') as f:
        f.writelines(sha(p)+'  '+p.relative_to(root).as_posix()+'\n' for p in paths)
    return sha(root/'sha256.txt')
def grid(refs):
    require(len(set(refs))==32 and all(0<=r<1600 for r in refs),'References')
    tasks=[dict(name='cache',kind='cache',gpu=True,seconds=14400)]
    tasks += [dict(name=f'fit-{family}-{seed}',kind='fit',family=family,seed=seed,gpu=True,seconds=14400)
              for family in FAMILIES for seed in SEEDS]
    for kind,ids,seeds in [('technical',refs[:2],SEEDS[:1]),('evaluation',refs,SEEDS)]:
        tasks += [dict(name=f'{kind}-{family}-{seed}-{ref}',kind=kind,family=family,seed=seed,
                       reference=ref,gpu=True,seconds=1200) for family in FAMILIES for seed in seeds for ref in ids]
    tasks.append(dict(name='analysis',kind='analysis',gpu=False,seconds=7200))
    require(len(tasks)==204 and sum(t['seconds'] for t in tasks if t['gpu'])==336000,'Grid reconciliation')
    return tasks
def authorize(source,approval):
    source=Path(source);verify(source,'LGP1-SOURCE-MANIFEST.sha256')
    a=read(approval)
    require(a.get('execution_authorized') is True,'Disabled/unapproved execution')
    require(a['source_sha256']==sha(source/'LGP1-SOURCE-MANIFEST.sha256'),'Approval/source identity')
    require(a['input_sha256']==sha(source/DOC/'INPUTS.json') and a['caps']==CAPS,'Approval input/caps')
    require(a['fits']==6 and a['updates']==72000 and a['main_episodes']==384 and a['technical_episodes']==8,'Approval counts')
    require(a['gpu_allocations']==203 and a['cpu_allocations']==1,'Allocation count')
    require(a.get('backup_volume_id')=='0a2f1ba9-0000-0000-0000-100000000000' and
            a.get('backup_destination')=='D:/THESIS-BACKUPS/local-goal-proposals-20260918','Designated backup identity')
    return a
def authenticate_inputs(source,*,payload=False):
    lock=read(Path(source)/DOC/'INPUTS.json')
    for name,digest in lock['files'].items():
        # Payload hashes are verified inside charged cache/eval jobs, never here
        # during synthetic preparation. No non-allowlisted reference is included.
        if not payload and name in lock['payload_files']: continue
        require(sha(name)==digest,'Input identity: '+name)
    return lock
