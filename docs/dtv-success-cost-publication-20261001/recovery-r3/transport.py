"""Exclusive R3 transport; configured bastion only, no blind retry."""
import argparse,base64,json,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BASE=r'''
import base64,hashlib,io,json,os,pathlib,subprocess,sys,tarfile,time
P=pathlib.Path
I=IDENTITY_PLACEHOLDER
source=P(I['recovery_source']);science=P(I['source']);control=P(I['recovery_control']);oldcontrol=P(I['control']);run=P(I['run']);r1source=P(I['r1_source']);r1control=P(I['r1_control']);r2source=P(I['r2_source']);r2control=P(I['r2_control'])
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
 controllers=[]
 for p in P('/proc').glob('[0-9]*'):
  try:
   if p.stat().st_uid!=os.getuid():continue
   argv=(p/'cmdline').read_bytes().split(b'\0')
   if any(x in argv for x in (b'dtv_success_cost.campaign',b'dtv_success_cost_r1.campaign',b'dtv_success_cost_r2.campaign',b'dtv_success_cost_r3.campaign')):controllers.append(process_identity(int(p.name)))
  except (OSError,ValueError):pass
 if controllers:raise RuntimeError('existing study controller '+repr(controllers))
 history=command(['sacct','-n','-P','-X','-u','ckontzias','-S','2026-10-01','--format=JobIDRaw,JobName%200,State,ExitCode,ElapsedRaw,AllocTRES,NodeList'])
 rows=[x.split('|') for x in history['stdout'].splitlines() if len(x.split('|'))>1 and x.split('|')[1].startswith('dtveff1-')]
 for row in rows:
  if row[-1]=='':row.pop()
 expected=I['terminal_rows']
 if rows!=expected:raise RuntimeError('unresolved/live/additional study allocation '+repr(rows))
 queue=command(['squeue','-h','-u','ckontzias','-o','%i|%j|%T|%N'])
 if any(len(x.split('|'))>1 and x.split('|')[1].startswith('dtveff1-') for x in queue['stdout'].splitlines()):raise RuntimeError('live study allocation, no continuation')
 return dict(observed_unix=time.time(),terminal_rows=rows,controllers=controllers,all_attempts_terminal=True)

def setup_imports():
 sys.path[:0]=[str(source),str(r2source),str(r1source),str(science)];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
'''
STAGE=r'''
state=reconcile()
target=run/'recovery-r3'
if source.exists() or control.exists() or target.exists():raise RuntimeError('R3 staging namespace already exists; retain')
if len(data)!=I['recovery_export_bytes'] or hashlib.sha256(data).hexdigest()!=I['recovery_export_sha256'] or hashlib.sha256(manifest_bytes).hexdigest()!=I['recovery_manifest_sha256']:raise RuntimeError('R3 source transport differs')
expected={x['path']:x for x in json.loads(manifest_bytes)['files']}
expected['PACKAGE-MANIFEST.json']=dict(bytes=len(manifest_bytes),sha256=I['recovery_manifest_sha256'])
with tarfile.open(fileobj=io.BytesIO(data),mode='r:') as tar:
 members=tar.getmembers()
 if len(members)!=len(expected) or {m.name for m in members}!=set(expected):raise RuntimeError('R3 archive inventory differs')
 payloads={}
 for m in members:
  p=P(m.name);v=tar.extractfile(m).read() if m.isfile() else b''
  if not m.isfile() or p.is_absolute() or '..' in p.parts or '\\' in m.name or len(v)!=expected[m.name]['bytes'] or hashlib.sha256(v).hexdigest()!=expected[m.name]['sha256']:raise RuntimeError('unsafe R3 member')
  payloads[m.name]=v
source.mkdir(parents=True);control.mkdir(parents=True)
with (control/'SOURCE-EXPORT.tar').open('xb') as f:f.write(data)
for name,v in payloads.items():
 p=source/name;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(v)
p=source/'docs/dtv-success-cost-publication-20261001/recovery-r3/PACKAGE-MANIFEST.json'
with p.open('xb') as f:f.write(manifest_bytes)
for name,v in ops.items():
 if P(name).name!=name:raise RuntimeError('unsafe authority filename')
 with (control/name).open('xb') as f:f.write(base64.b64decode(v))
setup_imports()
from dtv_success_cost.common import gate,read_seal
from dtv_success_cost.worker import file_identity
from dtv_success_cost_r3.common import *
c=gate(oldcontrol/'EXECUTION-APPROVAL.json');roles=role_check(c);runtime=runtime_check()
authenticate_history(run)
auth=json.loads((run/'preflight/INPUT-AUTHENTICATION.json').read_text())
if auth['bindings_sha256']!=I['bindings_sha256']:raise RuntimeError('preflight binding differs')
for spec in c['models'].values():
 record=auth['datasets'][spec['dataset']]
 if record['sha256']!=spec['dataset_sha256'] or record['identity']!=file_identity(spec['dataset']):raise RuntimeError('saved input metadata changed')
for p,digest in auth['checkpoints'].items():
 if sha(p)!=digest:raise RuntimeError('authenticated reused checkpoint changed')
target.mkdir()
resolution=dict(observed_unix=time.time(),original_stop_sha256=STOP_SHA,r1_stop_sha256=prior.R1_STOP,r2_stop_sha256=load(LINEAGE)['r2_stop_sha256'],r2_dispatch_sha256=load(LINEAGE)['r2_dispatch_sha256'],
 recovery_manifest_sha256=I['recovery_manifest_sha256'],authorization_sha256=I['recovery_authorization_sha256'],
 lineage_sha256=sha(LINEAGE),gpu_seconds=395,cpu_seconds=178,failed_allocations=['312924','312928'],replacement_task=load(LINEAGE)['failed_task'],
 successful_tasks_repeated=False,scientific_changes=False,terminal_rows=state['terminal_rows'],
 decision='dated Cube constructor-reset recovery; preserve original/R1/R2 STOPs, failures and all successful artifacts')
write(target/'STOP-RESOLUTION.json',resolution)
for p in control.iterdir():
 if p.is_file() and p.name!='SOURCE-EXPORT.tar':
  with (target/p.name).open('xb') as f:f.write(p.read_bytes())
for p in source.rglob('*'):
 if p.is_file():
  out=target/'source'/p.relative_to(source);out.parent.mkdir(parents=True,exist_ok=True)
  with out.open('xb') as f:f.write(p.read_bytes())
c,r=recovery_gate(control/'EXECUTION-APPROVAL.json')
from dtv_success_cost_r3.campaign import footprint,reservations,commands
jobs=commands(c,oldcontrol/'EXECUTION-APPROVAL.json',control/'EXECUTION-APPROVAL.json',run,r1source,r2source)
footprint(c,run,jobs,r);reserved=reservations(c,dict(gpu=395,cpu=178),jobs)
env=dict(os.environ,PYTHONPATH=str(source)+':'+str(r2source)+':'+str(r1source)+':'+str(science),PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4')
check=subprocess.run([I['control_python'],'-B','-c','import numpy,dtv_success_cost_r3.campaign,dtv_success_cost_r3.worker,dtv_success_cost_r3.accept,dtv_success_cost_r3.analysis_entry,dtv_success_cost_r3.preserve; print("r2_imports_ok")'],env=env,cwd=source,capture_output=True,text=True,timeout=30)
if check.returncode:raise RuntimeError('R3 imports '+check.stderr)
receipt=dict(status='R3_staged_authenticated',observed_unix=time.time(),roles=roles,runtime=runtime,
 full_reservations=reserved,imports=check.stdout,reconciliation=state,resolution_sha256=sha(target/'STOP-RESOLUTION.json'),
 recovery_manifest_sha256=I['recovery_manifest_sha256'],research_payloads_decoded=False,allocation_submissions=0,
 source_bytes=sum(p.stat().st_size for root in (source,r2source,r1source,science) for p in root.rglob('*') if p.is_file()),
 control_bytes=sum(p.stat().st_size for root in (control,r2control,r1control,oldcontrol) for p in root.rglob('*') if p.is_file()))
write(control/'STAGE.json',receipt);write(target/'STAGE.json',receipt);print(json.dumps(receipt))
'''
LAUNCH=r'''
state=reconcile()
if (control/'LAUNCH-INTENT.json').exists() or (control/'CONTROLLER-PROCESS.json').exists():raise RuntimeError('R3 launch previously attempted; never repeat')
setup_imports()
from dtv_success_cost_r3.common import recovery_gate
from dtv_success_cost_r3.campaign import commands,reservations,footprint
c,r=recovery_gate(control/'EXECUTION-APPROVAL.json');roles=role_check(c)
if sha(control/'EXECUTION-APPROVAL.json')!=I['recovery_approval_sha256'] or sha(control/'AUTHORIZATION.json')!=I['recovery_authorization_sha256']:raise RuntimeError('R3 authority changed')
target=run/'recovery-r3'
if (target/'STARTED.json').exists() or (target/'workers').exists() or (run/'analysis').exists():raise RuntimeError('R3 work already started; never repeat')
jobs=commands(c,oldcontrol/'EXECUTION-APPROVAL.json',control/'EXECUTION-APPROVAL.json',run,r1source,r2source)
reserved=reservations(c,dict(gpu=395,cpu=178),jobs);footprint(c,run,jobs,r)
argv=[I['control_python'],'-B','-m','dtv_success_cost_r3.campaign','--submit','--approval',str(control/'EXECUTION-APPROVAL.json')]
write(control/'LAUNCH-INTENT.json',dict(unix=time.time(),argv=argv,automatic_retry=False))
out=(control/'controller.out').open('xb');err=(control/'controller.err').open('xb')
env=dict(os.environ,PYTHONPATH=str(source)+':'+str(r2source)+':'+str(r1source)+':'+str(science),PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4')
started=time.time();process=subprocess.Popen(argv,cwd=source,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
identity=process_identity(process.pid)
if not identity:raise RuntimeError('R3 spawned identity ambiguous; never repeat')
record=dict(status='R3_launched_once',launch_unix=started,pid=process.pid,process=identity,argv=argv,
 recovery_manifest_sha256=I['recovery_manifest_sha256'],approval_sha256=I['recovery_approval_sha256'],authorization_sha256=I['recovery_authorization_sha256'],
 gpu_carried_seconds=395,cpu_carried_seconds=178,full_reservations=reserved,automatic_retry=False,roles=roles)
write(control/'CONTROLLER-PROCESS.json',record);write(target/'CONTROLLER-PROCESS.json',record)
with (target/'LAUNCH-INTENT.json').open('xb') as f:f.write((control/'LAUNCH-INTENT.json').read_bytes())
os.link(control/'controller.out',target/'controller.out');os.link(control/'controller.err',target/'controller.err')
out.close();err.close();print(json.dumps(record))
'''
OBSERVE=r'''
target=run/'recovery-r3';launch=json.loads((control/'CONTROLLER-PROCESS.json').read_text());current=process_identity(launch['pid']);expected=launch['process']
alive=bool(current and current['start_ticks']==expected['start_ticks'] and current['state']!='Z')
records=[json.loads(x) for x in (target/'DISPATCH-R3.jsonl').read_text().splitlines()] if (target/'DISPATCH-R3.jsonl').exists() else []
submitted=[x for x in records if x['event']=='submitted'];terminal=[x for x in records if x['event']=='terminal'];accepted=[x for x in records if x['event']=='accepted']
ids=['312920','312921','312922','312923','312924','312925','312926','312927','312928']+[x['allocation_id'] for x in submitted]
scheduler=command(['sacct','-n','-P','-X','-j',','.join(ids),'--format=JobIDRaw,JobName%200,State,ExitCode,ElapsedRaw,AllocTRES,NodeList'])
render=[]
for x in accepted:
 p=target/'workers'/x['task']/'RENDER-BACKEND.json'
 if p.exists():render.append(dict(task=x['task'],evidence=json.loads(p.read_text()),sha256=sha(p)))
receipt=dict(observed_unix=time.time(),exact_controller_alive=alive,current_process=current,expected_process=expected,
 stderr_bytes=(control/'controller.err').stat().st_size,submitted=submitted,terminal=terminal,accepted=accepted,
 carried=[x for x in records if x['event']=='carried_history_accepted'],gate=[x for x in records if x['event']=='technical_tranche_passed'],
 render_backend=render,stop=json.loads((target/'STOP-R3.json').read_text()) if (target/'STOP-R3.json').exists() else None,
 complete=(run/'COMPUTE-COMPLETE.json').exists(),scheduler=scheduler,
 run_bytes=sum(p.stat().st_size for p in run.rglob('*') if p.is_file()),scientific_results_opened=False)
print(json.dumps(receipt))
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
  data=Path(I['recovery_archive']).read_bytes();manifest=(HERE/'PACKAGE-MANIFEST.json').read_bytes()
  ops={p.name:base64.b64encode(p.read_bytes()).decode() for p in HERE.iterdir() if p.is_file() and p.name!='PACKAGE-MANIFEST.json'}
  body='data=base64.b64decode('+repr(base64.b64encode(data).decode())+')\nmanifest_bytes=base64.b64decode('+repr(base64.b64encode(manifest).decode())+')\nops='+repr(ops)+'\n'+STAGE
 elif a.mode=='launch':body=LAUNCH
 else:body=OBSERVE
 call(base+'\n'+body,a.label,timeout=300 if a.mode=='stage' else 180)
if __name__=='__main__':main()
