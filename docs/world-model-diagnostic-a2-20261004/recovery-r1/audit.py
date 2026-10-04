"""Metadata-only staged Git closure authentication; never imports acquired code."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[3]
DOC=ROOT/'docs/world-model-diagnostic-a2-20261004'
rows=json.loads((DOC/'SOURCE-AUDIT-RECEIPTS.json').read_text())
rows+=json.loads((DOC/'ENCODER-PIN.json').read_text())['source_receipts']
paths=[]
for row in rows:
    n=row['path'].replace('\\','/')
    if not n.startswith('docs/world-model-diagnostic-a2-20261004/source-audit/'):
        raise ValueError('Outside targeted source closure')
    raw=(ROOT/n).read_bytes()
    wanted={'bytes':row['bytes'],'sha256':row['sha256']}
    def identity(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
    if identity(raw)!=wanted:raise ValueError('Acquired receipt bytes changed: '+n)
    staged=subprocess.check_output(['git','show',':'+n],cwd=ROOT)
    if identity(staged)!=wanted:raise ValueError('Staged byte identity: '+n)
    paths.append(n)
print(json.dumps({'status':'ALL_STAGED_SOURCE_RECEIPTS_AUTHENTICATED','members':len(paths),
                  'models_loaded':False,'native_work':False,'source_paths':paths},indent=2))
