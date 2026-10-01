"""Study-specific capability, exclusive evidence and immutable byte bindings."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / 'docs/dtv-success-cost-20261001'
REMOTE = PurePosixPath('/lustreFS/data/superworld/ckontzias/thesis')
TASKS = ('pusht', 'reacher', 'cube')
CONFIGS = tuple(f'{m}{r}' for m in ('dtv', 'acid', 'forward', 'plain') for r in (30, 28))
SEEDS = (6101, 6102, 6103)
N = 320

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''): h.update(b)
    return h.hexdigest()

def write(path, value):
    with Path(path).open('x', encoding='utf-8') as f:
        json.dump(value, f, sort_keys=True, separators=(',', ':'), allow_nan=False)
        f.flush(); os.fsync(f.fileno())

def load(path): return json.loads(Path(path).read_text(encoding='utf-8'))

def gate(approval):
    a = load(approval)
    if a.get('study') != 'DTV-EFF1' or a.get('execute') is not True or a.get('research_execution_authorized') is not True:
        raise RuntimeError('DTV-EFF1 execution disabled; a new explicit immutable instruction is required')
    for key, path in [('bindings_sha256', DOC/'BINDINGS.json'), ('package_sha256', DOC/'PACKAGE-MANIFEST.json')]:
        if a.get(key) != sha(path): raise RuntimeError('execution capability binding changed')
    if a.get('cohort_sha256') != sha(DOC/'COHORT.json') or a.get('source_role') != 'DTV-EFF1-P2-320-per-task':
        raise RuntimeError('new source capability absent; old approvals are not valid here')
    authority = Path(a['authorization_record'])
    if sha(authority) != a['authorization_sha256']: raise RuntimeError('authority bytes changed')
    instruction = load(authority)
    if any(instruction.get(k) != a[k] for k in ('study','execute','research_execution_authorized','bindings_sha256','package_sha256','cohort_sha256','source_role')):
        raise RuntimeError('authority does not bind this executable study')
    for r in load(DOC/'PACKAGE-MANIFEST.json')['files']:
        p = (ROOT/r['path']).resolve()
        if not p.is_relative_to(ROOT) or sha(p) != r['sha256']: raise RuntimeError('package member changed')
    return load(DOC/'BINDINGS.json')

def run_namespace(c): return Path(REMOTE/'experiments/dtv-success-cost-20261001'/('run-'+sha(DOC/'BINDINGS.json')[:16]))

def seal(directory, identity):
    directory=Path(directory)
    members=[dict(path=p.name, bytes=p.stat().st_size, sha256=sha(p)) for p in sorted(directory.iterdir()) if p.is_file() and p.name!='SEAL.json']
    write(directory/'SEAL.json', dict(identity=identity, files=members))

def read_seal(directory, identity):
    d=Path(directory); s=load(d/'SEAL.json')
    if s['identity']!=identity: raise RuntimeError('sealed identity differs')
    if {p.name for p in d.iterdir()} != {r['path'] for r in s['files']}|{'SEAL.json'}: raise RuntimeError('unsealed member')
    for r in s['files']:
        p=d/r['path']
        if Path(r['path']).name!=r['path'] or p.stat().st_size!=r['bytes'] or sha(p)!=r['sha256']: raise RuntimeError('seal authentication failed')
    return s
