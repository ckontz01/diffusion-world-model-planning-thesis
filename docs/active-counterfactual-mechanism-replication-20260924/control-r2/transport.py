"""Single-attempt stage/launch and read-only observations, with native SSD route."""
import r1 as r
import argparse
import base64
from pathlib import Path
import subprocess
import time
import tarfile

PUB=r.REPO/'docs/active-counterfactual-mechanism-replication-publication-20260924/recovery-r2'
def remote(code):
    return subprocess.run(['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=15','-o','ServerAliveInterval=10','-o','ServerAliveCountMax=2','prometheus','/usr/bin/python3.9','-B','-'],input=code.encode(),capture_output=True,timeout=180)

def local_approval():
    a=r.read(PUB/'EXECUTION-APPROVAL.json')
    r.require(a['authorized'] is True and a['binding']==r.binding() and a['instruction']==(r.ROOT/'INSTRUCTION.txt').read_text(),'Exact enabled recovery authority')
    for n,h in r.read(r.ROOT/'SOURCE-MANIFEST.json')['files'].items():r.require(r.sha(r.ROOT/n)==h,'Recovery bytes')
    r.c.source_check()
    return a

def prelude():
    b=r.binding()
    return 'import sys,json,time,subprocess,os\nfrom pathlib import Path\nroot=Path('+repr(b['source'])+')\ncontrol=Path('+repr(b['control'])+')\nsys.path.insert(0,str(root));import r1 as r\nctx=r.Context(control/"EXECUTION-APPROVAL.json")\n'

def main():
    p=argparse.ArgumentParser();p.add_argument('operation',choices=['stage','launch','observe','backup']);p.add_argument('--receipt',required=True);p.add_argument('--request');a=p.parse_args()
    dest=PUB/a.receipt;r.require(Path(a.receipt).name==a.receipt and not dest.exists(),'Exclusive operation receipt')
    approval=local_approval();b=approval['binding']
    if a.operation=='backup':
        import preserve_r1
        # Complete archive capability stays original; new request includes all R1/R2 roots.
        original=PUB.parent/'execution-v2/EXECUTION-APPROVAL.json'
        auth=r.c.Authorization(original,r.RUN)
        start=time.monotonic()
        path=preserve_r1.backup(auth,a.request)
        r.write(dest,dict(destination=str(path),wall_seconds=time.monotonic()-start,verified=r.read(path/'BACKUP-VERIFIED.json'),recovery_manifest=b['manifest']))
        return
    if a.operation=='stage':
        from preserve import ssd,verify_tar
        ssd();receipt=r.read(PUB/'PACKAGE-VERIFIED.json')
        tar=PUB/'SOURCE-PACKAGE.tar';r.require(r.sha(tar)==receipt['archive']['sha256'] and r.sha(receipt['ssd_path'])==receipt['archive']['sha256'],'Verified R2 source SSD bytes')
        for n,h in r.c.reconciliation()['role_ledger_inventory'].items():r.require(r.sha(r.REPO/n)==h,'Intervening recorded role conflict')
        raw=base64.b64encode(tar.read_bytes()).decode();ap=base64.b64encode((PUB/'EXECUTION-APPROVAL.json').read_bytes()).decode()
        code='import base64,hashlib,tarfile,io,json,sys\nfrom pathlib import Path\n'
        code+='source=Path('+repr(b['source'])+');control=Path('+repr(b['control'])+')\n'
        code+='''assert not source.exists() and not control.exists(),'Exclusive recovery namespace'
source.mkdir(parents=True);control.mkdir(parents=True)
data=base64.b64decode('''+repr(raw)+''');assert hashlib.sha256(data).hexdigest()=='''+repr(receipt['archive']['sha256'])+'''
with tarfile.open(fileobj=io.BytesIO(data),mode='r:') as t:
 seen=set()
 for m in t:
  assert m.isfile() and Path(m.name).name==m.name and m.name not in seen
  seen.add(m.name)
  with (source/m.name).open('xb') as f:f.write(t.extractfile(m).read())
with (control/'EXECUTION-APPROVAL.json').open('xb') as f:f.write(base64.b64decode('''+repr(ap)+'''))
sys.path.insert(0,str(source));import r1 as r
ctx=r.Context(control/'EXECUTION-APPROVAL.json');r.baseline(ctx,exact_run=True)
assert r.c.sha(ctx.auth.inputs['registry_path'])==ctx.auth.inputs['registry_sha256']
r.write(control/'STAGED.json',dict(unix=__import__('time').time(),source=str(source),binding=ctx.binding,approval=ctx.approval_sha))
print(json.dumps(dict(source=str(source),control=str(control),approval=ctx.approval_sha,manifest=ctx.binding['manifest'])))
'''
    elif a.operation=='launch':
        code=prelude()+'''r.baseline(ctx,exact_run=True)
assert r.read(control/'STAGED.json')['approval']==ctx.approval_sha
assert not any((control/n).exists() for n in ('LAUNCH-INTENT.json','CONTROLLER-STARTED.json','CAMPAIGN.jsonl','STOP.json'))
for p,h in r.read(r.c.ROOT/'CONTROLLER-RUNTIME.json')['files'].items():assert r.sha(p)==h
r.write(control/'LAUNCH-INTENT.json',dict(unix=time.time(),recovery=ctx.binding['manifest']))
with (control/'controller.out').open('xb') as out,(control/'controller.err').open('xb') as err:
 p=subprocess.Popen(['/usr/bin/python3.9','-B',str(root/'controller.py'),'--approval',str(control/'EXECUTION-APPROVAL.json')],stdin=subprocess.DEVNULL,stdout=out,stderr=err,cwd=root,start_new_session=True)
ticks=Path('/proc',str(p.pid),'stat').read_text().rsplit(')',1)[1].split()[19]
record=dict(pid=p.pid,start_ticks=ticks,unix=time.time());r.write(control/'CONTROLLER-PROCESS.json',record);print(json.dumps(record))
'''
    else:
        code=prelude()+'''import acceptance_r1 as a
state=a.ledger(control,ctx.jobs,False)
result=dict(unix=time.time(),recovery=ctx.binding['manifest'],approval=ctx.approval_sha,submitted=list(state['submitted'].values()),accepted=len(state['accepted']),accepted_fits=sum(e['key'].startswith('fit-') for e in state['accepted'].values()),accepted_evaluations=sum(e['key'].startswith('evaluate-') for e in state['accepted'].values()),gpu_seconds=state['gpu_seconds'],cpu_seconds=state['cpu_seconds']+8,unresolved_claims=sorted(set(state['claimed'])-set(state['submitted'])),unaccepted=sorted(set(state['submitted'])-set(state['accepted'])),prior_failed_attempts=['304589','304591'])
for n in ('STOP.json','COMPUTE-COMPLETE.json','CONTROLLER-PROCESS.json'):
 p=control/n;result[n]=dict(record=r.read(p),sha256=r.sha(p)) if p.exists() else None
identity=result['CONTROLLER-PROCESS.json']
if identity:
 pid=identity['record']['pid'];p=Path('/proc')/str(pid)
 result['process']=dict(pid=pid,exists=p.exists())
 if p.exists():
  stat=(p/'stat').read_text().rsplit(')',1)[1].split();result['process'].update(start_ticks=stat[19],state=stat[0],exact_start=stat[19]==str(identity['record']['start_ticks']))
result['stderr_bytes']=(control/'controller.err').stat().st_size
for n in ('ALL-MODELS-FROZEN.json','TECHNICAL-TRANCHE-PASSED.json'):
 p=ctx.run/n;result[n]=dict(record=r.read(p),sha256=r.sha(p)) if p.exists() else None
if result['STOP.json']:
 result['controller_error']=(control/'controller.err').read_text()
 keys=sorted(set(state['submitted'])-set(state['accepted']))
 result['technical_errors']={}
 for key in keys:
  for p in (ctx.run/'logs').glob(key+'*.err'):
   result['technical_errors'][p.name]=p.read_text(errors='replace')[:8192]
  fail=ctx.run/key/'FAILURE.json'
  if fail.exists():result['technical_errors'][str(fail)]=r.read(fail)
print(json.dumps(result))
'''
    try:
        response=remote(code)
        record=dict(operation=a.operation,unix=time.time(),returncode=response.returncode,stdout=response.stdout.decode(errors='replace'),stderr=response.stderr.decode(errors='replace'),automatic_retry=False)
        r.write(dest,record);r.require(response.returncode==0,'Operation failure/ambiguity retained; do not repeat blindly')
        print(record['stdout'])
    except BaseException as e:
        if not dest.exists():r.write(dest,dict(operation=a.operation,unix=time.time(),error=repr(e),automatic_retry=False))
        raise

if __name__=='__main__':main()
