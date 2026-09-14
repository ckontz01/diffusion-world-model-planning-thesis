"""CVL executable contract and fail-closed authentication (stdlib, host-safe)."""
import hashlib
import json
import os
from pathlib import Path

VERSION='candidate-value-v1-20260914'
BASELINE='4ed1b801b4f1f08f4517f05e2d7ec900541c43bc'
ROOT=Path('/lustreFS/data/superworld/ckontzias/thesis')
RUN_PARENT=ROOT/'experiments/candidate-value-learning-20260914'
HISTORICAL=(1269,582,525,722,567,716,630,1066,1074,1565,70,867,221,905,1287,
            621,428,288,1488,757,641,855,1280,420,860,98,886,432,181,783,706,989)
CAPS={'gpu_seconds':180000,'cpu_seconds':7200,'storage_bytes':20000000000,
      'job_bytes':1000000000,'backup_free_bytes':40000000000}
MODEL_SHA='f0c666cc011ab057390f7e1571cf3d8bde905d13ff11f1d406f6d3dd8575340d'
ARMS=('continuation','immediate','value','linear')
TRAIN_SEEDS=(8201,8202,8203)
DOC='docs/candidate-value-learning-20260914/PROTOCOL.md'


def require(ok,message):
    if not ok: raise RuntimeError(message)


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()


def json_read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def json_write(path,value):
    with Path(path).open('x',encoding='utf-8',newline='\n') as f:
        json.dump(value,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')


def digest(*parts):
    return hashlib.sha256('|'.join(map(str,(VERSION,)+parts)).encode()).hexdigest()


def allocation():
    ids=sorted(set(range(1600))-set(HISTORICAL),key=lambda r:(digest('reference-allocation',r),r))
    return dict(train=ids[:96],validation=ids[96:128],closed_loop=ids[128:160])


def tail_seeds(reference,h,t):
    # Even/odd encoding makes the paired streams distinct by construction.
    base=int(digest('tail-pair',reference,h,t)[:15],16)<<1
    return (base,base|1)


def grid():
    a=allocation();out=[]
    for i in range(2):out.append(dict(kind='preflight',index=i,gpu=True,seconds=300))
    for split in ('train','validation'):
        for i,ref in enumerate(a[split]):
            for h in (75,150):
                out.append(dict(kind=split,index=i*2+(h==150),reference=ref,h=h,
                                gpu=True,seconds=600))
    for kind,seconds in (('fit',6000),('validate',600),('report',600)):
        out.append(dict(kind=kind,index=0,gpu=False,seconds=seconds))
    for i,ref in enumerate(a['closed_loop']):
        out.append(dict(kind='closed',index=i,reference=ref,gpu=True,seconds=600))
    return out


def task(kind,index):
    hits=[r for r in grid() if (r['kind'],r['index'])==(kind,index)]
    require(len(hits)==1,'Unregistered execution coordinate')
    return hits[0]


def child(root,name):
    root=Path(root).resolve();p=root/name
    require(not p.is_symlink() and p.resolve()!=root and root in p.resolve().parents,'Escaping path')
    return p


def seal(directory):
    p=Path(directory)
    files=sorted(x for x in p.rglob('*') if x.is_file() and x.name!='sha256.txt')
    require(files and not any(x.is_symlink() for x in files),'Empty/link output')
    with (p/'sha256.txt').open('x',encoding='utf-8',newline='\n') as f:
        for x in files:f.write(sha(x)+'  '+x.relative_to(p).as_posix()+'\n')


def verify_seal(directory):
    p=Path(directory);names=[]
    for line in (p/'sha256.txt').read_text().splitlines():
        expected,name=line.split('  ',1)
        require(name not in names and sha(child(p,name))==expected,'Output checksum')
        names.append(name)
    actual={x.relative_to(p).as_posix() for x in p.rglob('*') if x.is_file() and x.name!='sha256.txt'}
    require(actual==set(names) and names,'Unsealed or missing output')
    return json_read(p/'REPORT.json')


def verify_source(source,expected):
    source=Path(source);manifest=source/'SOURCE-MANIFEST.sha256'
    require(sha(manifest)==expected,'Source manifest identity')
    names=set()
    for line in manifest.read_text().splitlines():
        s,n=line.split('  ',1)
        require(n not in names and sha(child(source,n))==s,'Source member identity: '+n)
        names.add(n)
    actual={p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()}
    require(actual==names|{'SOURCE-MANIFEST.sha256'},'Unmanifested source files')


def capsule(source,path,source_sha):
    verify_source(source,source_sha)
    c=json_read(path)
    require(c['version']==VERSION and c['source_sha256']==source_sha
            and c['protocol_sha256']==sha(Path(source)/DOC),'Capsule provenance')
    a=allocation();ids=set(sum(a.values(),[]))
    require(set(map(int,c['records']))==ids,'Exact selected-only reference manifest')
    keys=[r['source_key'] for r in c['records'].values()]
    require(len(set(keys))==160,'Aliased sources; never replace references')
    for ref,row in c['records'].items():
        require(row['file']==str(ROOT/'experiments/independent-pusht/final-20260906-4a608e5/collection'/
                                  ('reference-%05d.npz'%int(ref))), 'Input path scope')
        require(len(row['sha256'])==64 and isinstance(row['environment_seed'],int),'Record metadata')
    return c


def authorize(source,run,approval,capsule_path,source_sha):
    a=json_read(approval)
    require(a.get('researcher_approved') is True and a.get('experiment')==VERSION
            and a.get('caps')==CAPS and a.get('source_sha256')==source_sha
            and a.get('capsule_sha256')==sha(capsule_path)
            and a.get('protocol_sha256')==sha(Path(source)/DOC),'No exact launch approval')
    run=Path(run).resolve()
    require(run.parent==RUN_PARENT and run.name=='run-'+source_sha[:16], 'Run namespace')
    c=capsule(source,capsule_path,source_sha)
    # Source/package approval cannot authorize different environment bytes.
    require(c['runtime_files'] and c['runtime_roots'],'Unpinned runtime')
    for name,s in c['runtime_files'].items():require(sha(name)==s,'Runtime file changed: '+name)
    for root,expected in c['runtime_roots'].items():
        require(tree_hash(Path(root))==expected,'Runtime tree changed: '+root)
    for root,expected in c['runtime_code_roots'].items():
        require(tree_hash(Path(root),code_only=True)==expected,'Runtime code changed: '+root)
    return c


def tree_hash(root,code_only=False):
    """Pin regular bytes and link text, independent of link resolution view.

    The environment's Python aliases point into the separately byte-pinned SIF.
    Dereferencing those links made host (dangling) and container (resolved)
    inventories differ. Link destinations remain authenticated, not omitted;
    regular environment files and the container image remain byte-authenticated.
    Never call this on a research data/artifact root.
    """
    require(root.is_dir(),'Missing runtime root')
    h=hashlib.sha256();count=0
    for p in sorted(root.rglob('*')):
        if code_only and p.suffix not in ('.py','.so','.pth','.toml','.yaml','.yml'):
            continue
        if '__pycache__' in p.parts or '.git' in p.parts:continue
        if p.is_symlink():
            count+=1;h.update(p.relative_to(root).as_posix().encode())
            h.update(b'\0symlink\0');h.update(os.readlink(str(p)).encode());h.update(b'\0')
        elif p.is_file():
            count+=1;h.update(p.relative_to(root).as_posix().encode());h.update(sha(p).encode())
    require(count>0,'Empty runtime root')
    return h.hexdigest()


def check_report(directory,kind,index,source_sha,capsule_sha):
    r=verify_seal(directory)
    require((r['kind'],r['index'],r['source_sha256'],r['capsule_sha256'])==
            (kind,index,source_sha,capsule_sha) and r['technical_valid'] is True,'Stage identity/validity')
    return r


def reservation(used_gpu,used_cpu,reserved_gpu,reserved_cpu,size,next_task):
    gpu=next_task['seconds'] if next_task['gpu'] else 0
    cpu=next_task['seconds'] if not next_task['gpu'] else 0
    return (used_gpu+reserved_gpu+gpu<=CAPS['gpu_seconds'] and
            used_cpu+reserved_cpu+cpu<=CAPS['cpu_seconds'] and
            size+CAPS['job_bytes']<=CAPS['storage_bytes'])
