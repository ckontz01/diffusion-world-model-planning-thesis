import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCREL = 'docs/world-model-diagnostic-a2-native-v3-20261015'
DOC = ROOT / DOCREL
REMOTE = '/lustreFS/data/superworld/ckontzias/thesis'
RUN = REMOTE + '/experiments/wm-diag0-a2-20261015/native-v3'
PRIOR = REMOTE + '/experiments/wm-diag0-a2-20261015/preflight-v1-stage-r1'
PLAN = 'e648465420311a69a3df237b9f199ecd070e1c1241481376888ffbffe593630f'

def identity(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for raw in iter(lambda: f.read(1048576), b''): h.update(raw)
    return {'bytes': Path(path).stat().st_size, 'sha256': h.hexdigest()}

def write_new(path, row):
    raw = json.dumps(row, sort_keys=True, indent=2, allow_nan=False).encode()
    if len(raw) > 2_000_000: raise ValueError('bounded metadata')
    with Path(path).open('xb') as f: f.write(raw)

def canonical(row):
    return hashlib.sha256(json.dumps(row, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
