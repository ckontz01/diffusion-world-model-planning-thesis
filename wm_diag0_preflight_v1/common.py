import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCREL = 'docs/world-model-diagnostic-a2-preflight-v1-20261015'
DOC = ROOT / DOCREL
REMOTE = '/lustreFS/data/superworld/ckontzias/thesis'
RUN = REMOTE + '/experiments/wm-diag0-a2-20261015/preflight-v1'
VENV = REMOTE + '/envs/hi-lewm-artifact-py311-cu121-swm006'
SITE = VENV + '/lib/python3.11/site-packages'
SIF = REMOTE + '/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif'
SIF_HASH = '589af9b428527ae2d315fbd5eaf7ef991efb1aa7249e30a6d28e6731df40afb2'

def identity(path):
    h = hashlib.sha256(); size = 0
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block); size += len(block)
    return dict(bytes=size, sha256=h.hexdigest())

def write_new(path, value):
    raw = json.dumps(value, sort_keys=True, indent=2).encode()
    if len(raw) > 1_000_000: raise ValueError('receipt size bound')
    with Path(path).open('xb') as f: f.write(raw)

def relative(name):
    from pathlib import PurePosixPath
    p = PurePosixPath(name)
    if p.is_absolute() or not name or '\\' in name or ':' in name or any(x in ('..', '.') for x in name.split('/')):
        raise ValueError('invalid relative path')
    return p

def verify(path, expected):
    if Path(path).is_symlink() or identity(path) != expected: raise ValueError('identity mismatch: ' + str(path))

def reservation(cpu_elapsed, other_cpu=12600):
    if not isinstance(cpu_elapsed, int) or cpu_elapsed < 0 or cpu_elapsed + other_cpu > 13800:
        raise ValueError('CPU cumulative plus full future bound')
    return cpu_elapsed + other_cpu
