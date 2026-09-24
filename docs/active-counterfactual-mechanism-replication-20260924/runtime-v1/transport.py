"""Explicit future stage/launch commands; disabled authorization checked FIRST."""
import common as c
import argparse
import base64
from pathlib import Path
import shlex
import subprocess
import time
from preserve import ssd

def remote(code):
    return subprocess.run(['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=15',
                           '-o','ServerAliveInterval=10','-o','ServerAliveCountMax=2','prometheus','/usr/bin/python3.9','-'],input=code.encode(),capture_output=True,timeout=180)
def stage(auth,approval,bundle,backup_receipt):
    receipt=c.read(backup_receipt);ssd()
    c.require(receipt['manifest']==auth.approval['package_sha256'] and c.sha(bundle)==receipt['bundle_sha256'],'Verified small-package backup required')
    copied=Path(receipt['ssd_bundle']);c.require(copied.is_file() and c.sha(copied)==receipt['bundle_sha256'],'Small-package SSD readback')
    # Metadata-only preflight. Never select replacement sources on a mismatch.
    for n,h in c.reconciliation()['role_ledger_inventory'].items(): c.require(c.sha(c.REPO/n)==h,'Intervening role assignment conflict')
    suffix=auth.approval['package_sha256'][:16];source=c.RESEARCH+'/snapshots/'+c.NAMESPACE+'-'+suffix;control=c.RESEARCH+'/staging/'+c.NAMESPACE+'-'+suffix
    c.require(Path(bundle).stat().st_size<=40_000_000,'Small source transport cap')
    raw=base64.b64encode(Path(bundle).read_bytes()).decode();ap=base64.b64encode(Path(approval).read_bytes()).decode()
    rel=c.ROOT.relative_to(c.REPO).as_posix()
    code=f'''import base64,hashlib,io,json,os,sys,tarfile
from pathlib import Path
source=Path({source!r});control=Path({control!r});run=Path({auth.approval['run']!r})
assert not any(p.exists() for p in (source,control,run)), 'Exclusive namespaces already exist; no restage'
data=base64.b64decode({raw!r});assert hashlib.sha256(data).hexdigest()=={receipt['bundle_sha256']!r}
source.mkdir(parents=True);control.mkdir(parents=True);run.mkdir(parents=True)
with tarfile.open(fileobj=io.BytesIO(data),mode='r:') as t:
 seen=set()
 for m in t:
  assert m.isfile() and m.name not in seen and not m.name.startswith('/') and '..' not in Path(m.name).parts
  seen.add(m.name);p=source/m.name;p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('xb') as f:f.write(t.extractfile(m).read())
approval=control/'EXECUTION-APPROVAL.json'
with approval.open('xb') as f:f.write(base64.b64decode({ap!r}))
sys.path.insert(0,str(source/{rel!r}));import common as c
a=c.Authorization(approval,str(run))
assert c.sha(a.inputs['registry_path'])==a.inputs['registry_sha256'], 'Registry metadata identity'
for key in ('logs','submissions'): (run/key).mkdir()
c.write(control/'STAGED.json',dict(package=a.approval['package_sha256'],bundle={receipt['bundle_sha256']!r},source=str(source),run=str(run)))
print(json.dumps(dict(source=str(source),control=str(control),run=str(run))))
'''
    return remote(code)
def launch(auth):
    suffix=auth.approval['package_sha256'][:16];source=c.RESEARCH+'/snapshots/'+c.NAMESPACE+'-'+suffix;control=c.RESEARCH+'/staging/'+c.NAMESPACE+'-'+suffix
    rel=c.ROOT.relative_to(c.REPO).as_posix()
    code=f'''import sys,os,subprocess,time,json
from pathlib import Path
root=Path({source!r})/{rel!r};control=Path({control!r});sys.path.insert(0,str(root));import common as c
approval=control/'EXECUTION-APPROVAL.json';auth=c.Authorization(approval,{auth.approval['run']!r})
assert c.read(control/'STAGED.json')['package']==auth.approval['package_sha256']
assert not any((control/n).exists() for n in ('LAUNCH-INTENT.json','CONTROLLER-STARTED.json','CAMPAIGN.jsonl','STOP.json'))
for p,h in c.read(root/'CONTROLLER-RUNTIME.json')['files'].items():assert c.sha(p)==h
c.write(control/'LAUNCH-INTENT.json',dict(unix=time.time(),package=auth.approval['package_sha256']))
with (control/'controller.out').open('xb') as out,(control/'controller.err').open('xb') as err:
 p=subprocess.Popen(['/usr/bin/python3.9','-B',str(root/'dispatch.py'),'--approval',str(approval),'--run',str(auth.run),'--control',str(control)],stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True,cwd=root)
ticks=Path('/proc',str(p.pid),'stat').read_text().rsplit(')',1)[1].split()[19]
r=dict(pid=p.pid,start_ticks=ticks,unix=time.time());c.write(control/'CONTROLLER-PROCESS.json',r);print(json.dumps(r))
'''
    return remote(code)
def main():
    p=argparse.ArgumentParser();p.add_argument('operation',choices=['stage','launch']);p.add_argument('--approval',required=True);p.add_argument('--run',required=True);p.add_argument('--bundle');p.add_argument('--backup-receipt');p.add_argument('--receipt',required=True);a=p.parse_args()
    auth=c.Authorization(a.approval,a.run);c.require(not Path(a.receipt).exists(),'Exclusive transport receipt')
    try:
        r=stage(auth,a.approval,a.bundle,a.backup_receipt) if a.operation=='stage' else launch(auth)
        c.write(a.receipt,dict(unix=time.time(),operation=a.operation,returncode=r.returncode,stdout=r.stdout.decode(errors='replace'),stderr=r.stderr.decode(errors='replace'),automatic_retry=False))
        c.require(r.returncode==0,'Transport/launch ambiguity retained; never repeat automatically')
    except BaseException as e:
        if not Path(a.receipt).exists():c.write(a.receipt,dict(unix=time.time(),error=repr(e),automatic_retry=False))
        raise
if __name__=='__main__':main()
