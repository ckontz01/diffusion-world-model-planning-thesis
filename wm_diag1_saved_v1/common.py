"""Exclusive new-study evidence and bounded, non-executable input handling."""
import hashlib,json,math,os,stat,time
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
DOC=ROOT/'docs/world-model-diagnostic-diag1-saved-v1-20261017'
PKG=ROOT/'wm_diag1_saved_v1'
BRANCH='world-model-diagnostic-diag1-saved-20261017'
OLD=ROOT/'docs/world-model-diagnostic-rc1-final-close-v1-20261017'
PYTHON='C:/Users/Chris/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
REMOTE='/lustreFS/data/superworld/ckontzias/thesis/experiments/wm-diag1-saved-20261017'
SETTINGS=(('pusht','lewm'),('pusht','dinowm_noprop'),('reacher','lewm'),('reacher','dinowm_noprop'))

def canonical(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode('utf8')
def unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('duplicate JSON key')
        result[key]=value
    return result
def ordinary(path):
    p=Path(path)
    if not p.is_absolute() or '..' in p.parts:raise ValueError('absolute nonredirected path')
    for q in (p,)+tuple(p.parents):
        s=q.lstat()
        if stat.S_ISLNK(s.st_mode) or getattr(s,'st_file_attributes',0)&0x400:raise ValueError('no input/output alias or reparse redirect')
    return p
def identity(path):
    p=ordinary(Path(path));s=p.stat();h=hashlib.sha256();n=0
    if not stat.S_ISREG(s.st_mode):raise ValueError('ordinary file')
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):n+=len(b);h.update(b)
    after=p.stat()
    if (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns_ns if hasattr(after,'st_mtime_ns_ns') else after.st_mtime_ns):raise ValueError('file changed during authentication')
    return {'bytes':n,'sha256':h.hexdigest()}
def write_new(path,value,limit=4000000):
    raw=value if isinstance(value,bytes) else canonical(value);p=Path(path)
    if len(raw)>limit:raise ValueError('finite new artifact pre-write cap')
    p.parent.mkdir(parents=True,exist_ok=True);ordinary(p.parent)
    with p.open('xb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
    return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def read_bound(path,want,limit=4000000):
    p=ordinary(Path(path))
    if want['bytes']>limit or identity(p)!=want:raise ValueError('required saved artifact identity mismatch: '+str(p))
    raw=p.read_bytes()
    if len(raw)!=want['bytes'] or hashlib.sha256(raw).hexdigest()!=want['sha256']:raise ValueError('authenticated read changed')
    return raw
def json_bound(path,want,limit=4000000):return json.loads(read_bound(path,want,limit),object_pairs_hook=unique)
def check_time(end):
    if time.monotonic()>=end:raise TimeoutError('fixed operation deadline; no retry')

def prep_history():
    rows=[]
    for p in DOC.glob('LOCAL-*.started.json'):
        end=DOC/p.name.replace('.started.json','.json')
        if not end.exists():raise RuntimeError('ambiguous/running owned preparation operation: '+p.name)
    for p in DOC.glob('LOCAL-*.json'):
        if not p.name.endswith('.started.json'):rows.append(json.loads(p.read_text()))
    return rows
