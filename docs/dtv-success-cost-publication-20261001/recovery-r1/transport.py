"""New exclusive R1 staging, detached continuation and technical observations."""
import argparse,base64,hashlib,json,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BASE=r'''

import base64,hashlib,io,json,os,pathlib,subprocess,sys,tarfile,time
P=pathlib.Path
I=IDENTITY_PLACEHOLDER
source=P(I['recovery_source']);science=P(I['source']);control=P(I['recovery_control']);oldcontrol=P(I['control']);run=P(I['run'])
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
def reconcile():
 old=json.loads((oldcontrol/'CONTROLLER-PROCESS.json').read_text());current=process_identity(old['pid'])
 if current and current['start_ticks']==old['process']['start_ticks'] and current['state']!='Z':raise RuntimeError('original controller alive; no continuation')
 controllers=[]
 for p in P('/proc').glob('[0-9]*'):
  try:
   if p.stat().st_uid!=os.getuid():continue
   argv=(p/'cmdline').read_bytes().split(b'\0')
   if any(x in argv for x in (b'dtv_success_cost.campaign',b'dtv_success_cost_r1.campaign')):controllers.append(process_identity(int(p.name)))
  except (OSError,ValueError):pass
 if controllers:raise RuntimeError('existing study controller '+repr(controllers))
 history=command(['sacct','-n','-P','-X','-u','ckontzias','-S','2026-10-01','--format=JobIDRaw,JobName%200,State,ExitCode,ElapsedRaw,AllocTRES,NodeList'])
 rows=[x.split('|') for x in history['stdout'].splitlines() if len(x.split('|'))>1 and x.split('|')[1].startswith('dtveff1-')]
 expected=[['312920','dtveff1-preflight','COMPLETED','0:0','178','cpu=4,mem=8G,node=1','gpu03']]
 if rows!=expected:raise RuntimeError('unresolved/live/additional study allocation '+repr(rows))
 return dict(observed_unix=time.time(),old_process=current,terminal_row=rows[0],controllers=controllers)
def setup_imports():
 sys.path[:0]=[str(source),str(science)];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
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
 p=argparse.ArgumentParser();p.add_argument('mode',choices=('stage','launch','observe'));p.add_argument('--label',required=True);a=p.parse_args()
 I=json.loads((HERE/'IDENTITIES.json').read_text());base=BASE.replace('IDENTITY_PLACEHOLDER',repr(I))
 if a.mode=='stage':
  archive=Path(I['recovery_archive']).read_bytes();manifest=(HERE/'PACKAGE-MANIFEST.json').read_bytes()
  ops={p.name:base64.b64encode(p.read_bytes()).decode() for p in HERE.iterdir() if p.is_file() and p.name!='PACKAGE-MANIFEST.json'}
  body='data=base64.b64decode('+repr(base64.b64encode(archive).decode())+')\nmanifest_bytes=base64.b64decode('+repr(base64.b64encode(manifest).decode())+')\nops='+repr(ops)+'\n'+r'''
state=reconcile()
if source.exists() or control.exists() or (run/'recovery-r1').exists():raise RuntimeError('R1 staging namespace already exists')
if len(data)!=I['recovery_export_bytes'] or hashlib.sha256(data).hexdigest()!=I['recovery_export_sha256'] or hashlib.sha256(manifest_bytes).hexdigest()!=I['recovery_manifest_sha256']:raise RuntimeError('R1 transport bytes differ')
expected={r['path']:r for r in json.loads(manifest_bytes)['files']}
expected['PACKAGE-MANIFEST.json']=dict(bytes=len(manifest_bytes),sha256=I['recovery_manifest_sha256'])
with tarfile.open(fileobj=io.BytesIO(data),mode='r:') as t:
 members=t.getmembers()
 if len(members)!=len(expected) or {m.name for m in members}!=set(expected):raise RuntimeError('R1 archive inventory differs')
 for m in members:
  p=P(m.name);v=t.extractfile(m).read() if m.isfile() else b''
  if not m.isfile() or p.is_absolute() or '..' in p.parts or '\\' in m.name or len(v)!=expected[m.name]['bytes'] or hashlib.sha256(v).hexdigest()!=expected[m.name]['sha256']:raise RuntimeError('unsafe R1 member')
 source.mkdir(parents=True);control.mkdir(parents=True)
 with (control/'SOURCE-EXPORT.tar').open('xb') as f:f.write(data)
 for m in members:
  target=source/m.name;target.parent.mkdir(parents=True,exist_ok=True)
  with target.open('xb') as f:f.write(t.extractfile(m).read())
target=source/'docs/dtv-success-cost-publication-20261001/recovery-r1/PACKAGE-MANIFEST.json'
with target.open('xb') as f:f.write(manifest_bytes)
for name,value in ops.items():
 if P(name).name!=name:raise RuntimeError('unsafe R1 authority filename')
 with (control/name).open('xb') as f:f.write(base64.b64decode(value))
setup_imports()
from dtv_success_cost.common import gate,read_seal
from dtv_success_cost.worker import file_identity
from dtv_success_cost_r1.common import STOP_SHA,LEDGER_SHA,SEAL_SHA,AUTH_SHA
c=gate(oldcontrol/'EXECUTION-APPROVAL.json');roles=role_check(c);runtime=runtime_check()
read_seal(run/'preflight','preflight')
if sha(run/'STOP.json')!=STOP_SHA or sha(run/'DISPATCH.jsonl')!=LEDGER_SHA or sha(run/'preflight/SEAL.json')!=SEAL_SHA or sha(run/'preflight/INPUT-AUTHENTICATION.json')!=AUTH_SHA:raise RuntimeError('original failure/preflight evidence differs')
auth=json.loads((run/'preflight/INPUT-AUTHENTICATION.json').read_text())
if auth['bindings_sha256']!=I['bindings_sha256']:raise RuntimeError('preflight binding differs')
for spec in c['models'].values():
 record=auth['datasets'][spec['dataset']]
 if record['sha256']!=spec['dataset_sha256'] or record['identity']!=file_identity(spec['dataset']):raise RuntimeError('preflight dataset metadata changed')
for p,digest in auth['checkpoints'].items():
 if sha(p)!=digest:raise RuntimeError('authenticated reused checkpoint changed')
location=run/'recovery-r1';location.mkdir()
resolution=dict(observed_unix=time.time(),original_stop_sha256=STOP_SHA,original_dispatch_sha256=LEDGER_SHA,
 preflight_seal_sha256=SEAL_SHA,preflight_input_sha256=AUTH_SHA,terminal_row=state['terminal_row'],
 recovery_manifest_sha256=I['recovery_manifest_sha256'],authorization_sha256=I['recovery_authorization_sha256'],
 cpu_seconds=178,gpu_seconds=0,successful_preflight_recomputed=False,scientific_changes=False,
 original_controller=state['old_process'],decision='dated control-only resolution; preserve original STOP and ledger')
write(location/'STOP-RESOLUTION.json',resolution)
for p in control.iterdir():
 if p.is_file() and p.name!='SOURCE-EXPORT.tar':
  with (location/p.name).open('xb') as f:f.write(p.read_bytes())
for p in source.rglob('*'):
 if p.is_file():
  target=location/'source'/p.relative_to(source);target.parent.mkdir(parents=True,exist_ok=True)
  with target.open('xb') as f:f.write(p.read_bytes())
from dtv_success_cost_r1.common import recovery_gate
recovery_gate(control/'EXECUTION-APPROVAL.json')
source_bytes=sum(p.stat().st_size for p in source.rglob('*') if p.is_file())+sum(p.stat().st_size for p in science.rglob('*') if p.is_file())
control_bytes=sum(p.stat().st_size for p in control.rglob('*') if p.is_file())+sum(p.stat().st_size for p in oldcontrol.rglob('*') if p.is_file())
if source_bytes>c['source_bytes'] or control_bytes>c['control_bytes']:raise RuntimeError('cumulative retained source/control cap')
env=dict(os.environ,PYTHONPATH=str(source)+':'+str(science),PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4')
check=subprocess.run([I['control_python'],'-B','-c','import numpy,dtv_success_cost_r1.campaign,dtv_success_cost_r1.accept,dtv_success_cost_r1.analysis_entry,dtv_success_cost_r1.preserve; print("r1_control_imports_ok")'],env=env,cwd=source,capture_output=True,text=True,timeout=30)
if check.returncode:raise RuntimeError('R1 control imports '+check.stderr)
receipt=dict(status='R1_staged_authenticated',observed_unix=time.time(),source_bytes=source_bytes,control_bytes=control_bytes,
 roles=roles,runtime=runtime,imports=check.stdout,reconciliation=state,resolution_sha256=sha(location/'STOP-RESOLUTION.json'),
 recovery_manifest_sha256=I['recovery_manifest_sha256'],research_payloads_decoded=False,allocation_submissions=0)
write(control/'STAGE.json',receipt);write(location/'STAGE.json',receipt);print(json.dumps(receipt))
'''
 elif a.mode=='launch':
  body=r'''
state=reconcile()
if (control/'LAUNCH-INTENT.json').exists() or (control/'CONTROLLER-PROCESS.json').exists():raise RuntimeError('R1 launch previously attempted; do not repeat')
setup_imports()
from dtv_success_cost_r1.common import recovery_gate
c,r=recovery_gate(control/'EXECUTION-APPROVAL.json');roles=role_check(c)
if sha(control/'EXECUTION-APPROVAL.json')!=I['recovery_approval_sha256'] or sha(control/'AUTHORIZATION.json')!=I['recovery_authorization_sha256']:raise RuntimeError('R1 authority differs')
if (run/'recovery-r1/STARTED.json').exists() or any((run/x).exists() for x in [j['id'] for j in c['jobs']]+['analysis']):raise RuntimeError('work already started; no repeat')
argv=[I['control_python'],'-B','-m','dtv_success_cost_r1.campaign','--submit','--approval',str(control/'EXECUTION-APPROVAL.json')]
write(control/'LAUNCH-INTENT.json',dict(unix=time.time(),argv=argv,automatic_retry=False))
out=(control/'controller.out').open('xb');err=(control/'controller.err').open('xb')
env=dict(os.environ,PYTHONPATH=str(source)+':'+str(science),PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4')
started=time.time();process=subprocess.Popen(argv,cwd=source,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
identity=process_identity(process.pid)
if not identity:raise RuntimeError('R1 spawned identity ambiguous; never repeat')
record=dict(status='R1_launched_once',launch_unix=started,pid=process.pid,process=identity,argv=argv,
 recovery_manifest_sha256=I['recovery_manifest_sha256'],approval_sha256=I['recovery_approval_sha256'],
 authorization_sha256=I['recovery_authorization_sha256'],carried_allocation='312920',cpu_carried_seconds=178,automatic_retry=False,roles=roles)
write(control/'CONTROLLER-PROCESS.json',record)
write(run/'recovery-r1/CONTROLLER-PROCESS.json',record)
with (run/'recovery-r1/LAUNCH-INTENT.json').open('xb') as f:f.write((control/'LAUNCH-INTENT.json').read_bytes())
os.link(control/'controller.out',run/'recovery-r1/controller.out');os.link(control/'controller.err',run/'recovery-r1/controller.err')
out.close();err.close();print(json.dumps(record))
'''
 else:
  body=r'''
location=run/'recovery-r1';launch=json.loads((control/'CONTROLLER-PROCESS.json').read_text());current=process_identity(launch['pid']);expected=launch['process']
alive=bool(current and current['start_ticks']==expected['start_ticks'] and current['state']!='Z')
events=[json.loads(x) for x in (location/'DISPATCH-R1.jsonl').read_text().splitlines()] if (location/'DISPATCH-R1.jsonl').exists() else []
submitted=[x for x in events if x['event']=='submitted'];terminal=[x for x in events if x['event']=='terminal'];accepted=[x for x in events if x['event']=='accepted']
ids=['312920']+[x['allocation_id'] for x in submitted]
scheduler=command(['sacct','-n','-P','-X','-j',','.join(ids),'--format=JobIDRaw,JobName%200,State,ExitCode,ElapsedRaw,AllocTRES,NodeList'])
receipt=dict(observed_unix=time.time(),exact_controller_alive=alive,current_process=current,expected_process=expected,
 stderr_bytes=(control/'controller.err').stat().st_size,submitted=submitted,terminal=terminal,accepted=accepted,
 carried=[x for x in events if x['event']=='carried_preflight_accepted'],gate=[x for x in events if x['event']=='technical_tranche_passed'],
 stop=json.loads((location/'STOP-R1.json').read_text()) if (location/'STOP-R1.json').exists() else None,
 complete=(run/'COMPUTE-COMPLETE.json').exists(),scheduler=scheduler,run_bytes=sum(p.stat().st_size for p in run.rglob('*') if p.is_file()),
 scientific_results_opened=False)
print(json.dumps(receipt))
'''
 call(base+'\n'+body,a.label,timeout=300 if a.mode=='stage' else 180)
if __name__=='__main__':main()
