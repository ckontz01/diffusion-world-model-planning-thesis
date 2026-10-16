import hashlib,json,os,stat
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent

DOC=ROOT/'docs/world-model-diagnostic-rc1-recovery-r1-20261016'
OLD='/lustreFS/data/superworld/ckontzias/thesis/experiments/wm-diag0-a2-20261015/campaign-v4-rc1-grid-v1'
RUN=OLD.replace('grid-v1','grid-recovery-r1')
GRID_HASH='da2766c3f8c33266ee54cea9fb2e3bdf650046e9a61ac39c209816f1b1e7514b'
INDICES=list(range(66,124))
HUMAN="Then fix it and continue. I approve 139+ total GPU attempts and the bounded extra work needed to replace the failed run. Keep the science and total GPU-time limit unchanged, and don’t rerun successful runs."

def digest(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def canonical(z):return json.dumps(z,sort_keys=True,separators=(',',':'),allow_nan=False).encode()

def identity(path):
    p=Path(path);s=p.lstat()
    if not stat.S_ISREG(s.st_mode) or getattr(s,'st_file_attributes',0)&0x400:raise ValueError('ordinary nonredirected evidence')
    h=hashlib.sha256();n=0
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b);n+=len(b)
    return {'bytes':n,'sha256':h.hexdigest()}

def write_new(path,obj,limit=1048576):
    p=Path(path);b=canonical(obj)+b'\n'
    if len(b)>limit:raise ValueError('prewrite metadata bound')
    for q in (p.parent,)+tuple(p.parents):
        if q.exists() and (q.is_symlink() or getattr(q.lstat(),'st_file_attributes',0)&0x400):raise ValueError('no destination redirect')
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())

def sampled_bytes(root):
    """Mutable own artifacts only. Ignore vanished entries, never other errors.

    This is a sampled kill guard, not a quota or scientific-input reader.
    One no-follow stat replaces the old is_file()/stat() race. Missing root is
    allowed only for output, which has not necessarily been created yet.
    """
    root=Path(root)
    try:s=root.lstat()
    except FileNotFoundError:
        if root.name=='output':return 0
        raise
    if not stat.S_ISDIR(s.st_mode) or getattr(s,'st_file_attributes',0)&0x400:raise ValueError('ordinary own artifact directory')
    total=0;count=0;stack=[(root,0)]
    while stack:
        directory,depth=stack.pop()
        if depth>32:raise ValueError('bounded own artifact depth')
        try:
            with os.scandir(str(directory)) as entries:
                for entry in entries:
                    try:s=entry.stat(follow_symlinks=False)
                    except FileNotFoundError:continue
                    count+=1
                    if count>20000:raise ValueError('bounded own artifact members')
                    if getattr(s,'st_file_attributes',0)&0x400:raise ValueError('artifact reparse point')
                    if stat.S_ISDIR(s.st_mode):stack.append((Path(entry.path),depth+1))
                    elif stat.S_ISREG(s.st_mode):total+=s.st_size
                    else:raise ValueError('artifact alias or special file')
        except FileNotFoundError:
            if directory==root and root.name!='output':raise
            # A transient nested directory disappeared after being listed.
            continue
    return total

def closed_indices(c):
    r=c['rc1_recovery'];a=r['authority']
    if a['direct_human_instruction']!=HUMAN or r['indices']!=INDICES or r['old_run']!=OLD or c['run']!=RUN:raise ValueError('exact human recovery scope')
    if (r['allocated_before'],r['planned_total_attempts'],r['GPU_terminal_before'],r['GPU_full_future'])!=(81,139,45902,254702):raise ValueError('failure-inclusive finite recovery arithmetic')
    if r['GPU_full_future']!=r['GPU_terminal_before']+len(INDICES)*3600 or r['GPU_full_future']>468000:raise ValueError('unchanged total GPU time')
    if a['replacement_parent_maxima']!={'world_resets':49,'controller_actions':2980,'Reacher_dm_steps':5960,'CEM_decisions':33,'CEM_sequences':297000,'bank_sequences':16,'macro_transitions':1485080,'visual_encoder_calls':1998,'encoded_frames':2062,'action_encoder_calls':5946,'predictor_calls':4955,'cost_api_calls':991}:raise ValueError('one fixed LeWM parent extra work only')
    return r
