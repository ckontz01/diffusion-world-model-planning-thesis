"""ACVM1 capability and byte authentication. Standard library; no data on import."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import sys

ROOT = Path(__file__).resolve().parent
PROPOSAL = ROOT.parent
REPO = ROOT.parents[2]
BASE = REPO / 'docs/active-counterfactual-verification-20260923'
OLD = BASE / 'bindings-r1'
sys.dont_write_bytecode = True
# Accepted scientific modules import THIS new common capability, not ACV0's.
for p in (OLD, BASE):
    if str(p) not in sys.path: sys.path.append(str(p))
CONTROLS = ('static','committed_feedback','no_update','active','ordinary','early-replan')
RESEARCH = '/lustreFS/data/superworld/ckontzias/thesis'
NAMESPACE = 'active-counterfactual-mechanism-replication-v1'
RUN_PARENT = RESEARCH + '/experiments/' + NAMESPACE

def require(ok, message):
    if not ok: raise ValueError(message)

def canonical(v): return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(v): return hashlib.sha256(canonical(v)).hexdigest()
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()
def read(p): return json.loads(Path(p).read_text(encoding='utf8'))
def write(p,v):
    with Path(p).open('xb') as f:
        f.write(canonical(v)+b'\n'); f.flush(); os.fsync(f.fileno())
def append(p,v):
    with Path(p).open('ab') as f:
        f.write(canonical(v)+b'\n'); f.flush(); os.fsync(f.fileno())
def lines(p): return [json.loads(x) for x in Path(p).read_text().splitlines()] if Path(p).exists() else []
def roles(): return read(ROOT/'ROLES.json')['roles']
def grid(): return read(PROPOSAL/'GRID.json')
def caps(): return read(PROPOSAL/'PROTOCOL.json')['resources']
def reconciliation_path():
    p=ROOT/'RECONCILIATION-LIVE.json'
    return p if p.exists() else ROOT/'RECONCILIATION.json'
def reconciliation():return read(reconciliation_path())
def work_seconds(s): return s['work_seconds']
def supervisor_seconds(s): return s['seconds']-10
def files(root):
    root=Path(root)
    for p in sorted(root.rglob('*')):
        require(not p.is_symlink(),'Symlink forbidden: '+str(p))
        if p.is_file(): yield p
def bytes_in(root): return sum(p.stat().st_size for p in files(root)) if Path(root).exists() else 0
def members(root): return {p.relative_to(root).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p)) for p in files(root)}
def seal(root,identity): write(Path(root)/'SEAL.json',dict(identity=identity,files=members(root)))
def verify_seal(root,expected=None):
    root=Path(root); s=read(root/'SEAL.json')
    if expected is not None: require(s['identity']==expected,'Seal task identity')
    actual={p.relative_to(root).as_posix() for p in files(root)}-{'SEAL.json'}
    require(actual==set(s['files']),'Seal member set')
    for n,i in s['files'].items():
        require(n and not n.startswith('/') and '..' not in Path(n).parts,'Unsafe member')
        p=root/n; require(p.stat().st_size==i['bytes'] and sha(p)==i['sha256'],'Seal bytes: '+n)
    return s
def source_check():
    for n,h in read(ROOT/'SOURCE-MANIFEST.json')['files'].items():
        require(sha(REPO/n)==h,'Source changed: '+n)

class Authorization:
    """New-role interlock, NOT a signature. No command enables its template."""
    def __init__(self,approval,run):
        a=read(approval)
        if a.get('authorized') is not True: raise PermissionError('ACVM1 research execution DISABLED')
        expected={'schema','authorized','instruction','package_sha256','bindings','run','no_retry','caps'}
        require(set(a)==expected and a['schema']=='ACVM1-execution-v1','New study authorization required')
        require(a['instruction'].startswith('EXECUTE ACV MECHANISM REPLICATION ') and len(a['instruction'])>70,'Explicit instruction absent')
        require(a['package_sha256']==sha(ROOT/'SOURCE-MANIFEST.json'),'Manifest binding')
        require(a['bindings']==bindings(),'Frozen input/role/grid/model/runtime bindings')
        require(a['caps']==caps() and a['no_retry'] is True,'Unchanged caps/no retry')
        require(str(run)==a['run']==RUN_PARENT+'/run-'+a['package_sha256'][:16],'Exclusive namespace')
        source_check()
        require(reconciliation()['status']=='LIVE_METADATA_RECONCILED','Fresh metadata reconciliation required')
        self.approval=a; self.approval_sha=sha(approval); self.run=Path(run) if os.name!='nt' else PurePosixPath(run)
        self.inputs=read(ROOT/'INPUT-BINDINGS.json')
    def runtime(self):
        if getattr(self,'runtime_verified',False): return
        for p,h in self.inputs['runtime_files'].items(): require(sha(p)==h,'Runtime: '+p)
        require(sha(self.inputs['container']['path'])==self.inputs['container']['sha256'],'Container')
        self.runtime_verified=True
    def checkpoint(self):
        p=self.inputs['lewm']; require(sha(p)==self.inputs['lewm_sha256'],'LeWM authentication'); return p
    def reference(self,index,role):
        require(role=='mechanism_evaluation' and index in roles()[role],'New-role access boundary')
        from models import check_freeze
        check_freeze(self.run,self.approval['package_sha256'])
        if index!=roles()[role][0]:
            from acceptance import check_gate
            check_gate(self.run)
        r=self.inputs['references'][str(index)]
        require(sha(r['file'])==r['sha256'],'Reference bytes')
        return r

def bindings():
    return {n:sha(ROOT/n) for n in ('INPUT-BINDINGS.json','ROLES.json','MODEL-REUSE.json','CONTROLLER-RUNTIME.json')} | {'reconciliation':sha(reconciliation_path()),
        'grid':sha(PROPOSAL/'GRID.json'),'protocol':sha(PROPOSAL/'PROTOCOL.json')}
