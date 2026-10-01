"""Exclusive deployment, one detached launch, and technical-only observations."""
import argparse,base64,hashlib,json,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
DOC=ROOT/'docs/dtv-success-cost-20261001'

BASE=r'''
import base64,hashlib,io,json,os,pathlib,subprocess,sys,tarfile,time
P=pathlib.Path
I=IDENTITY_PLACEHOLDER
source=P(I['source']);control=P(I['control']);run=P(I['run'])
def sha(p):
 h=hashlib.sha256()
 with P(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def write(p,value):
 with P(p).open('x') as f:json.dump(value,f,indent=2);f.flush();os.fsync(f.fileno())
def command(args,timeout=60):
 r=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
 v=dict(command=args,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr)
 if r.returncode:raise RuntimeError('non-retry command fault '+repr(v))
 return v
def process_identity(pid):
 p=P('/proc')/str(pid)/'stat'
 if not p.exists():return None
 a=p.read_text().rsplit(')',1)[1].split()
 return dict(pid=pid,state=a[0],start_ticks=int(a[19]))
def exclusive_check():
 queue=command(['squeue','-h','-u','ckontzias','-o','%i|%j|%T|%N'])
 history=command(['sacct','-n','-P','-X','-u','ckontzias','-S','2026-09-01','--format=JobIDRaw,JobName%200,State,ExitCode,ElapsedRaw,AllocTRES,NodeList'])
 for r in (queue,history):r['stdout']='\n'.join(x for x in r['stdout'].splitlines() if len(x.split('|'))>1 and x.split('|')[1].strip().startswith('dtveff1-'))
 controllers=[]
 for p in P('/proc').glob('[0-9]*'):
  try:
   if p.stat().st_uid!=os.getuid():continue
   argv=(p/'cmdline').read_bytes().split(b'\0')
   if b'dtv_success_cost.campaign' in argv:controllers.append(process_identity(int(p.name)))
  except (OSError,ValueError):pass
 existing=[str(p) for p in run.parent.glob('run-*')] if run.parent.exists() else []
 state=dict(queue=queue,history=history,controllers=controllers,existing_run_directories=existing)
 if queue['stdout'].strip() or history['stdout'].strip() or controllers or existing:raise RuntimeError('existing/ambiguous study launch '+repr(state))
 return state
def inventory(root=P('/lustreFS/data/superworld/ckontzias/thesis')):
 paths=set((root/'manifests').rglob('*.tsv'))
 paths.update((root/'data/stablewm/derived/candidate-pools/pusht-v1').glob('*/manifest.json'))
 for study in ('gdp-cem-e14','gdp-cem-e16','gdp-cem-e18'):
  paths.update((root/'experiments'/study).glob('*/p2-manifests/**/queries.tsv'))
 return [dict(path=p.relative_to(root).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(paths) if p.is_file()]
def role_check(c):
 if inventory()!=c['role_inventory']:raise RuntimeError('intervening source-role inventory conflict; no ID replacement')
 if any(len(c['cohort'][t])!=320 for t in ('pusht','reacher','cube')):raise RuntimeError('exact cohort count')
 return dict(files=len(c['role_inventory']),bytes=sum(r['bytes'] for r in c['role_inventory']),parents_per_task=320,metadata_only=True,payload_reads=0)
def runtime_check():
 text="import json,numpy,sys,shutil; print(json.dumps(dict(python=sys.version,numpy=numpy.__version__,slurm={s:shutil.which(s) for s in ('sbatch','sacct','squeue')},research_execution=False)))"
 r=command([I['control_python'],'-B','-c',text]);v=json.loads(r['stdout'])
 if not all(v['slurm'].values()):raise RuntimeError('existing interpreter lacks scheduler PATH')
 return v
'''

def call(script,label,timeout=240):
    receipt=HERE/(label+'.json');started=time.monotonic()
    if receipt.exists():raise RuntimeError('exclusive operational receipt already exists')
    try:
        r=subprocess.run(['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=15','prometheus','python3.9 -'],input=script.encode(),capture_output=True,timeout=timeout)
        record=dict(returncode=r.returncode,stdout=r.stdout.decode(errors='replace'),stderr=r.stderr.decode(errors='replace'),local_wall_seconds=time.monotonic()-started,automatic_retry=False)
    except subprocess.TimeoutExpired as e:
        record=dict(returncode=None,stdout=(e.stdout or b'').decode(errors='replace'),stderr=(e.stderr or b'').decode(errors='replace'),local_wall_seconds=time.monotonic()-started,ambiguous_transport=True,automatic_retry=False)
    with receipt.open('x') as f:json.dump(record,f,indent=2)
    if record['returncode']!=0:raise RuntimeError('preserved operational fault '+str(receipt)+' '+record['stderr'])
    value=json.loads(record['stdout']);print(json.dumps(value,indent=2));return value

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('precheck','stage','launch','observe'));p.add_argument('--label',required=True);a=p.parse_args()
    identity=json.loads((HERE/'IDENTITIES.json').read_text())
    selection=HERE/'CONTROL-RUNTIME.json'
    if selection.exists():
        identity['control_python']=json.loads(selection.read_text())['control_python']
        identity['control_runtime_sha256']=hashlib.sha256(selection.read_bytes()).hexdigest()
    base=BASE.replace('IDENTITY_PLACEHOLDER',repr(identity))
    if a.mode=='precheck':
        body='c='+repr(json.loads((DOC/'BINDINGS.json').read_text()))+'\n'+r'''
state=exclusive_check()
if source.exists() or control.exists():raise RuntimeError('source/control namespace already exists')
roles=role_check(c);runtime=runtime_check()
print(json.dumps(dict(status='exclusive_prelaunch_clear',observed_unix=time.time(),host=os.uname().nodename,checks=state,roles=roles,runtime=runtime,source_absent=True,control_absent=True,run_absent=True)))
'''
    elif a.mode=='stage':
        ops={p.name:base64.b64encode(p.read_bytes()).decode() for p in HERE.iterdir() if p.is_file()}
        archive=Path(identity['archive']).read_bytes();manifest=(DOC/'PACKAGE-MANIFEST.json').read_bytes()
        body='data=base64.b64decode('+repr(base64.b64encode(archive).decode())+')\nmanifest_bytes=base64.b64decode('+repr(base64.b64encode(manifest).decode())+')\nops='+repr(ops)+'\n'+r'''
state=exclusive_check()
if source.exists() or control.exists():raise RuntimeError('exclusive staging namespace conflict')
if len(data)!=I['export_bytes'] or hashlib.sha256(data).hexdigest()!=I['export_sha256'] or hashlib.sha256(manifest_bytes).hexdigest()!=I['package_sha256']:raise RuntimeError('transport export binding mismatch')
rows=json.loads(manifest_bytes)['files'];expected={r['path']:r for r in rows}
expected['PACKAGE-MANIFEST.json']=dict(bytes=len(manifest_bytes),sha256=I['package_sha256'])
with tarfile.open(fileobj=io.BytesIO(data),mode='r:') as t:
 members=t.getmembers()
 if len(members)!=445 or len({m.name for m in members})!=445 or {m.name for m in members}!=set(expected):raise RuntimeError('source member inventory')
 for m in members:
  p=P(m.name);v=t.extractfile(m).read() if m.isfile() else b''
  if not m.isfile() or p.is_absolute() or '..' in p.parts or '\\' in m.name or len(v)!=expected[m.name]['bytes'] or hashlib.sha256(v).hexdigest()!=expected[m.name]['sha256']:raise RuntimeError('unsafe/unauthenticated export member')
 c=json.loads(t.extractfile('docs/dtv-success-cost-20261001/BINDINGS.json').read());roles=role_check(c);runtime=runtime_check()
 control.mkdir(parents=True);source.mkdir(parents=True)
 with (control/'SOURCE-EXPORT.tar').open('xb') as f:f.write(data)
 for m in members:
  target=source/m.name;target.parent.mkdir(parents=True,exist_ok=True)
  with target.open('xb') as f:f.write(t.extractfile(m).read())
 target=source/'docs/dtv-success-cost-20261001/PACKAGE-MANIFEST.json'
 with target.open('xb') as f:f.write(manifest_bytes)
for name,value in ops.items():
 if P(name).name!=name:raise RuntimeError('unsafe operational filename')
 with (control/name).open('xb') as f:f.write(base64.b64decode(value))
sys.path.insert(0,str(source));sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
from dtv_success_cost.common import gate
gate(control/'EXECUTION-APPROVAL.json')
if sha(control/'AUTHORIZATION.json')!=I['authority_sha256'] or sha(control/'EXECUTION-APPROVAL.json')!=I['enabled_approval_sha256']:raise RuntimeError('staged authority bytes')
if sha(control/'AUTHORIZATION-INSTRUCTION.txt')!=I['instruction_sha256']:raise RuntimeError('staged instruction bytes')
if sha(control/'CONTROL-RUNTIME.json')!=I['control_runtime_sha256']:raise RuntimeError('selected existing controller runtime changed')
env=dict(os.environ,PYTHONPATH=str(source),PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4')
check=subprocess.run([I['control_python'],'-B','-c','import numpy,dtv_success_cost.campaign,dtv_success_cost.accept,dtv_success_cost.analysis,dtv_success_cost.preserve; print("production_control_imports_ok")'],env=env,cwd=source,capture_output=True,text=True,timeout=30)
if check.returncode:raise RuntimeError('existing non-research import/path check '+check.stderr)
for r in rows:
 if sha(source/r['path'])!=r['sha256']:raise RuntimeError('staged immutable source changed')
source_bytes=sum(p.stat().st_size for p in source.rglob('*') if p.is_file())
if source_bytes>c['source_bytes']:raise RuntimeError('complete deployed source cap')
receipt=dict(status='exact_export_staged',observed_unix=time.time(),roles=roles,runtime=runtime,imports=check.stdout,source_bytes=source_bytes,package_sha256=I['package_sha256'],authority_sha256=I['authority_sha256'],enabled_approval_sha256=I['enabled_approval_sha256'],research_payload_reads=0,physics=False,gpu=False,checks=state)
write(control/'STAGE.json',receipt);print(json.dumps(receipt))
'''
    elif a.mode=='launch':
        body=r'''
state=exclusive_check()
if (control/'LAUNCH-INTENT.json').exists() or (control/'CONTROLLER-PROCESS.json').exists():raise RuntimeError('launch already attempted/ambiguous; never repeat')
sys.path.insert(0,str(source));sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
from dtv_success_cost.common import gate
c=gate(control/'EXECUTION-APPROVAL.json');roles=role_check(c)
if sha(control/'AUTHORIZATION.json')!=I['authority_sha256'] or sha(control/'EXECUTION-APPROVAL.json')!=I['enabled_approval_sha256']:raise RuntimeError('authority changed')
if sha(control/'CONTROL-RUNTIME.json')!=I['control_runtime_sha256']:raise RuntimeError('controller runtime selection changed')
argv=[I['control_python'],'-B','-m','dtv_success_cost.campaign','--submit','--approval',str(control/'EXECUTION-APPROVAL.json')]
write(control/'LAUNCH-INTENT.json',dict(unix=time.time(),argv=argv,automatic_retry=False))
out=(control/'controller.out').open('xb');err=(control/'controller.err').open('xb')
env=dict(os.environ,PYTHONPATH=str(source),PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4')
started=time.time();process=subprocess.Popen(argv,cwd=source,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
identity=process_identity(process.pid)
if not identity:raise RuntimeError('spawn identity unavailable; preserve and reconcile, never repeat')
record=dict(status='launched_once',launch_unix=started,pid=process.pid,process=identity,argv=argv,package_sha256=I['package_sha256'],enabled_approval_sha256=I['enabled_approval_sha256'],authority_sha256=I['authority_sha256'],control_runtime_sha256=I['control_runtime_sha256'],automatic_retry=False,exclusive_checks=state,roles=roles)
write(control/'CONTROLLER-PROCESS.json',record);out.close();err.close()
deadline=time.monotonic()+30
while not run.is_dir():
 current=process_identity(process.pid)
 if not current or current['start_ticks']!=identity['start_ticks'] or current['state']=='Z' or time.monotonic()>deadline:raise RuntimeError('launched controller did not create run; no retry')
 time.sleep(.1)
provenance=run/'launch-provenance';provenance.mkdir()
for p in control.iterdir():
 if p.is_file() and p.name not in ('SOURCE-EXPORT.tar','controller.out','controller.err'):
  with (provenance/p.name).open('xb') as f:f.write(p.read_bytes())
os.link(control/'controller.out',provenance/'controller.out');os.link(control/'controller.err',provenance/'controller.err')
print(json.dumps(record))
'''
    else:
        body=r'''
launch=json.loads((control/'CONTROLLER-PROCESS.json').read_text());current=process_identity(launch['pid']);expected=launch['process']
alive=bool(current and current['start_ticks']==expected['start_ticks'] and current['state']!='Z')
events=[json.loads(x) for x in (run/'DISPATCH.jsonl').read_text().splitlines()] if (run/'DISPATCH.jsonl').exists() else []
submitted=[x for x in events if x['event']=='submitted'];terminal=[x for x in events if x['event']=='terminal'];accepted=[x for x in events if x['event']=='accepted'];ids=[x['allocation_id'] for x in submitted]
scheduler=command(['sacct','-n','-P','-X','-j',','.join(ids),'--format=JobIDRaw,JobName%200,State,ExitCode,ElapsedRaw,AllocTRES,NodeList']) if ids else None
receipt=dict(observed_unix=time.time(),exact_controller_alive=alive,current_process=current,expected_process=expected,controller_stderr_bytes=(control/'controller.err').stat().st_size,submitted=submitted,terminal=terminal,accepted=accepted,technical_gate=[x for x in events if x['event']=='technical_tranche_passed'],stop=json.loads((run/'STOP.json').read_text()) if (run/'STOP.json').exists() else None,complete=(run/'COMPUTE-COMPLETE.json').exists(),scheduler=scheduler,run_bytes=sum(p.stat().st_size for p in run.rglob('*') if p.is_file()),control_bytes=sum(p.stat().st_size for p in control.rglob('*') if p.is_file()),source_bytes=sum(p.stat().st_size for p in source.rglob('*') if p.is_file()),partial_scientific_results_opened=False)
print(json.dumps(receipt))
'''
    call(base+'\n'+body,a.label,timeout=300 if a.mode=='stage' else 180)

if __name__=='__main__':main()
