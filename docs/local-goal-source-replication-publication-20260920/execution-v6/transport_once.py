"""Exact source-only transport; no research execution and no retry path.

Uses Windows files and configured WSL SSH stdin, never the unhealthy WSL D: mount.
Kept outside the reviewed source closure. Failed/existing destinations are left
intact and require explicit reconciliation, not another invocation.
"""
import argparse
import hashlib
import io
import json
import shlex
import subprocess
import sys
import tarfile
import time
from pathlib import Path, PurePosixPath

ARCHIVE = Path('D:/THESIS-BACKUPS/local-goal-source-replication-20260920/preparation-v6.tar')
ARCHIVE_SHA = 'f9e097120c3e332ca42823d30b6f6788cb398a1bba47a128dfe161db6c8421dd'
SOURCE_SHA = 'a8fa92772272e11a279aac6c13699fc5b6da9f8160bd3264bab15e3f6bf68cec'
SOURCE = '/lustreFS/data/superworld/ckontzias/thesis/snapshots/local-goal-source-replication-20260920-a8fa92772272e11a'
MANIFEST = 'LGP-RB2-SOURCE-MANIFEST.sha256'
SSH = ['wsl.exe', '-d', 'Thesis-Ubuntu', '-u', 'chris', '--', 'ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=20', 'prometheus']

REMOTE = r'''
import hashlib,io,json,sys,tarfile,time
from pathlib import Path,PurePosixPath
source=Path(SOURCE)
assert not source.exists(), 'Existing source: preserve and reconcile; do not retry'
data=sys.stdin.buffer.read(20_000_001)
assert len(data)==3_788_800 and hashlib.sha256(data).hexdigest()==ARCHIVE_SHA, 'Archive bytes/hash'
with tarfile.open(fileobj=io.BytesIO(data),mode='r:') as tf:
    members=tf.getmembers()
    assert len(members)==111 and len({m.name for m in members})==111
    for m in members:
        p=PurePosixPath(m.name)
        assert m.isfile() and not p.is_absolute() and '..' not in p.parts and str(p)==m.name
    contents={m.name:tf.extractfile(m).read() for m in members}
assert hashlib.sha256(contents[MANIFEST]).hexdigest()==SOURCE_SHA
listed={line[66:]:line[:64] for line in contents[MANIFEST].decode().splitlines()}
assert set(contents)==set(listed)|{MANIFEST,'APPROVAL-TEMPLATE.json'}
assert all(hashlib.sha256(contents[n]).hexdigest()==h for n,h in listed.items())
assert json.loads(contents['APPROVAL-TEMPLATE.json'])['execution_authorized'] is False
source.mkdir(exist_ok=False)
for name,data in contents.items():
    out=source/name
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('xb') as f:f.write(data)
sys.path.insert(0,str(source/'cluster/prometheus'))
import lgprb2_contract as c
c.old.verify(source,MANIFEST)
print(json.dumps(dict(source=str(source),source_sha256=SOURCE_SHA,archive_sha256=ARCHIVE_SHA,files=len(contents),source_bytes=sum(map(len,contents.values())),unix=time.time(),research_execution=False),sort_keys=True))
'''


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--verify-local-only',action='store_true')
    a=p.parse_args()
    data=ARCHIVE.read_bytes()
    assert len(data)==3_788_800 and hashlib.sha256(data).hexdigest()==ARCHIVE_SHA
    with tarfile.open(fileobj=io.BytesIO(data),mode='r:') as tf:
        members=tf.getmembers()
        assert len(members)==111 and len({m.name for m in members})==111
        assert all(m.isfile() and not PurePosixPath(m.name).is_absolute() and '..' not in PurePosixPath(m.name).parts for m in members)
        assert hashlib.sha256(tf.extractfile(MANIFEST).read()).hexdigest()==SOURCE_SHA
    header='\n'.join(f'{k}={v!r}' for k,v in dict(SOURCE=SOURCE,ARCHIVE_SHA=ARCHIVE_SHA,SOURCE_SHA=SOURCE_SHA,MANIFEST=MANIFEST).items())+'\n'
    code=header+REMOTE
    compile(code,'<exact-source-transport>','exec')
    if a.verify_local_only:
        print(json.dumps(dict(archive_bytes=len(data),members=len(members),archive_sha256=ARCHIVE_SHA,remote_code_compiles=True,no_remote_calls=True)))
        return
    receipt=Path(__file__).with_name('SOURCE-UPLOAD.json')
    with receipt.open('x',encoding='utf-8',newline='\n') as f:
        # Claim local ownership before the network mutation. Never overwrite.
        started=time.time()
        result=subprocess.run(SSH+['/usr/bin/python3.9 -B -S -c '+shlex.quote(code)],input=data,capture_output=True,timeout=120)
        record=dict(started=started,ended=time.time(),exit_code=result.returncode,stdout=result.stdout.decode(),stderr=result.stderr.decode())
        json.dump(record,f,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps(record))
    if result.returncode:raise SystemExit('Transport stopped; preserve destination and reconcile. No retry.')


if __name__=='__main__':main()
