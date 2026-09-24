"""Preparation-only utilities; no research runtime import or execution authority."""
import hashlib
import json
import os
from pathlib import Path
import sys

for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[key] = '4'
os.environ['CUDA_VISIBLE_DEVICES'] = ''
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OLD = REPO / 'docs/active-counterfactual-verification-20260923'
PUB = REPO / 'docs/active-counterfactual-verification-publication-20260923/completion-r6'
sys.path.insert(0, str(OLD))
SSD = Path('D:/THESIS-BACKUPS/active-counterfactual-verification-pilot-v1/run-c2c6fcbe8c41fed2')
PINS = {
    'policy.py': '753271dcce8f1e7c21a665e215c4aee2e6a5a8f8098fe6d816a75e2b93a38453',
    'model.py': 'd070acbd69170036fc2cd52a49a7d9eed255e2a1aaf763c55701e087cd93ac15',
    'tree.py': 'e76d05b9e13f78f1dc6568cbe56b8ee23b35528fc1049f11858302aa8c2cf871',
    'bindings-r1/fitting.py': 'c4fa3ee50cdcbac0267d10bb62d62ab7d8ccd16d8040d1043ebdf80109e060e1',
    'bindings-r1/episodes.py': '5f09b7c5c23b9c3ec947dec9e32f216a8a83e6422d379bbba5637b7e96712edc',
}

def digest(raw): return hashlib.sha256(raw).hexdigest()
def read(path): return json.loads(Path(path).read_text(encoding='utf8'))
def write(path, value):
    raw = value if isinstance(value, bytes) else (json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n').encode()
    with Path(path).open('xb') as f: f.write(raw)

def authenticate_code():
    for name, expected in PINS.items():
        if digest((OLD/name).read_bytes()) != expected: raise ValueError('Changed original: '+name)

authenticate_code()
