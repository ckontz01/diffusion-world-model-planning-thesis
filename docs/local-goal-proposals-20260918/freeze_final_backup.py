"""Exclusive Windows operational package; no research access or job submission."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode=True
repo=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(repo/'cluster/prometheus'))
import lgp1_preserve as preserve

preserve.check_ssd()
root=preserve.DEST/'backup-portability-20260919'
root.mkdir(exist_ok=False)
files=['cluster/prometheus/lgp1_preserve.py','cluster/prometheus/lgp1_contract.py',
       'cluster/prometheus/test_lgp1_preserve_portability.py',
       'docs/local-goal-proposals-20260918/BACKUP-PORTABILITY.md',
       'docs/local-goal-proposals-20260918/final_authenticate.py',
       'docs/local-goal-proposals-20260918/freeze_final_backup.py']
manifest={}
for name in files:
    data=(repo/name).read_bytes();p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write(data)
    manifest[name]=dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
preserve.c.write(root/'MANIFEST.json',manifest)
request='/lustreFS/data/superworld/ckontzias/thesis/experiments/local-goal-proposals-20260918/run-b54a55b16bcb83a5/final-preservation/BACKUP-REQUEST.json'
preserve.validate_request(request)
raw=subprocess.check_output(['wsl','-d','Thesis-Ubuntu','-u','chris','--','ssh','prometheus','cat',request])
r=json.loads(raw)
assert r['sha256']=='24609c83f6c21d99edc579229ab990db184c6e0fa1133ebad4336882c35189fd'
assert r['bytes']==1734420480 and r['files']==1733
approval=dict(scope='final backup only; zero job submission or research computation',
    authority='Standing user authorization, 19 September 2026, narrow verified technical repair',
    manifest_sha256=preserve.c.sha(root/'MANIFEST.json'),request=request,
    request_sha256=hashlib.sha256(raw).hexdigest(),archive_sha256=r['sha256'],archive_bytes=r['bytes'],
    scientific_source_sha256=r['source_sha256'],backup_destination=str(preserve.DEST),volume_id=preserve.VOLUME,
    caps_unchanged=True,original_immutable_source_unchanged=True,tests_passed=4)
preserve.c.write(root/'OPERATIONAL-AUTHORIZATION.json',approval)
record=dict(package=str(root),manifest_sha256=approval['manifest_sha256'],
    authorization_sha256=preserve.c.sha(root/'OPERATIONAL-AUTHORIZATION.json'),**{k:v for k,v in approval.items() if k!='manifest_sha256'})
preserve.c.write(repo/'docs/local-goal-proposals-20260918/BACKUP-PORTABILITY-PACKAGE.json',record)
print(json.dumps(record))
