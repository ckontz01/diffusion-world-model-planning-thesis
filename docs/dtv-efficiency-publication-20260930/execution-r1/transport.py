"""Operational stdin transport and technical observations; no science changes."""
import argparse,base64,hashlib,json,subprocess,time
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
DOC=ROOT/'docs/dtv-efficiency-correction-r1-20260930'
IDENTITY=json.loads((HERE/'IDENTITIES.json').read_text())
ARCHIVE=Path('D:/THESIS-BACKUPS/dtv-efficiency-20260930/correction-r1/package-8d3ebff35241a01f/package.tar')

BASE="""
import base64,hashlib,io,json,os,pathlib,subprocess,sys,tarfile,time
P=pathlib.Path
def sha(p):
 h=hashlib.sha256()
 with P(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def write(p,value):
 with P(p).open('x') as f:json.dump(value,f,indent=2)
def command(args):
 r=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=30)
 record=dict(command=args,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr)
 if r.returncode:raise RuntimeError('control command fault '+repr(record))
 return record
def process_identity(pid):
 p=P('/proc')/str(pid)/'stat'
 if not p.exists():return None
 fields=p.read_text().rsplit(')',1)[1].split()
 return dict(pid=pid,state=fields[0],start_ticks=int(fields[19]))
I=IDENTITY_PLACEHOLDER
source=P(I['source']);control=P(I['control']);run=P(I['run'])
names=','.join('dtveff0-'+t+'-'+str(s) for t in ('pusht','reacher','cube') for s in (6101,6102,6103))
def exclusive_check():
 queue=command(['squeue','-h','--name='+names,'-o','%i|%j|%T|%N'])
 history=command(['sacct','-n','-P','-X','-S','2026-09-30','--name='+names,'--format=JobIDRaw,JobName,State,ExitCode,ElapsedRaw,AllocTRES,NodeList'])
 controllers=[]
 for p in P('/proc').glob('[0-9]*'):
  try:
   if p.stat().st_uid!=os.getuid():continue
   argv=(p/'cmdline').read_bytes().split(b'\\0')
   if b'dtv_efficiency_r1.campaign' in argv:controllers.append(process_identity(int(p.name)))
  except (OSError,ValueError):pass
 conflicts=dict(queue=queue,history=history,controllers=controllers,existing_run_directories=[str(p) for p in run.parent.glob('run-*')] if run.parent.exists() else [])
 if queue['stdout'].strip() or history['stdout'].strip() or controllers or conflicts['existing_run_directories']:raise RuntimeError('existing/ambiguous DTV execution conflict '+repr(conflicts))
 return conflicts
"""

def remote(body):return BASE.replace('IDENTITY_PLACEHOLDER',repr(IDENTITY))+'\n'+body

def call(script,label,timeout=180):
    receipt=HERE/(label+'.json');started=time.monotonic()
    if receipt.exists():raise RuntimeError('exclusive operational receipt already exists')
    try:
        r=subprocess.run(['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=15','prometheus','python3.9 -'],input=script.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
        record=dict(returncode=r.returncode,stdout=r.stdout.decode(errors='replace'),stderr=r.stderr.decode(errors='replace'),local_wall_seconds=time.monotonic()-started,automatic_retry=False)
    except subprocess.TimeoutExpired as e:
        record=dict(returncode=None,stdout=(e.stdout or b'').decode(errors='replace'),stderr=(e.stderr or b'').decode(errors='replace'),local_wall_seconds=time.monotonic()-started,command_timeout=True,automatic_retry=False)
    with receipt.open('x') as f:json.dump(record,f,indent=2)
    if record['returncode']!=0:raise RuntimeError('transport fault preserved '+str(receipt)+' '+record['stderr'])
    value=json.loads(record['stdout']);print(json.dumps(value,indent=2));return value

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('prelaunch','stage','launch','observe'));p.add_argument('--label',required=True);args=p.parse_args()
    if args.mode=='prelaunch':
        body="""
state=exclusive_check()
if source.exists() or control.exists():raise RuntimeError('source/control namespace already exists; reconcile, do not overwrite')
print(json.dumps(dict(status='exclusive_prelaunch_clear',observed_unix=time.time(),host=os.uname().nodename,control_python=sys.version,checks=state,source_absent=True,control_absent=True,run_absent=True)))
"""
    elif args.mode=='stage':
        archive=ARCHIVE.read_bytes();manifest=(DOC/'PACKAGE-MANIFEST.json').read_bytes()
        ops={name:base64.b64encode((HERE/name).read_bytes()).decode() for name in ('AUTHORIZATION-INSTRUCTION.txt','DELEGATION-PROVENANCE.json','AUTHORIZATION.json','EXECUTION-APPROVAL.json','IDENTITIES.json','authorize.py','transport.py','PRELAUNCH-01.json','AUTHORIZATION-STARTUP-FAULT.json')}
        body='archive=base64.b64decode('+repr(base64.b64encode(archive).decode())+')\nmanifest_bytes=base64.b64decode('+repr(base64.b64encode(manifest).decode())+')\nops='+repr(ops)+'\n'+"""
state=exclusive_check()
if source.exists() or control.exists():raise RuntimeError('exclusive stage namespace conflict')
if hashlib.sha256(archive).hexdigest()!=I['source_export_sha256'] or len(archive)!=4413440 or hashlib.sha256(manifest_bytes).hexdigest()!=I['manifest_sha256']:raise RuntimeError('transported source identity')
rows=json.loads(manifest_bytes)['files'];expected={r['path']:r for r in rows}
with tarfile.open(fileobj=io.BytesIO(archive),mode='r:') as t:
 members=t.getmembers()
 if len(members)!=282 or len({m.name for m in members})!=282 or {m.name for m in members}!=set(expected):raise RuntimeError('archive member set')
 for m in members:
  name=P(m.name)
  if not m.isfile() or name.is_absolute() or '..' in name.parts:raise RuntimeError('unsafe archive member')
  data=t.extractfile(m).read();row=expected[m.name]
  if len(data)!=row['bytes'] or hashlib.sha256(data).hexdigest()!=row['sha256']:raise RuntimeError('archive member hash')
 source.mkdir(parents=True)
 for m in members:
  target=source/m.name;target.parent.mkdir(parents=True,exist_ok=True)
  with target.open('xb') as f:f.write(t.extractfile(m).read())
target=source/'docs/dtv-efficiency-correction-r1-20260930/PACKAGE-MANIFEST.json'
with target.open('xb') as f:f.write(manifest_bytes)
for row in rows:
 if sha(source/row['path'])!=row['sha256']:raise RuntimeError('staged source member changed')
control.mkdir(parents=True)
for name,encoded in ops.items():
 with (control/name).open('xb') as f:f.write(base64.b64decode(encoded))
 if sha(control/name)!=hashlib.sha256(base64.b64decode(encoded)).hexdigest():raise RuntimeError('operational transported bytes changed')
if sha(control/'EXECUTION-APPROVAL.json')!=I['enabled_approval_sha256'] or sha(control/'AUTHORIZATION.json')!=I['authority_sha256']:raise RuntimeError('operational hash mismatch')
if sha(control/'AUTHORIZATION-INSTRUCTION.txt')!=I['instruction_sha256'] or sha(control/'DELEGATION-PROVENANCE.json')!=json.loads((control/'AUTHORIZATION.json').read_text())['delegation_provenance_sha256']:raise RuntimeError('instruction/delegation binding changed')
sys.path.insert(0,str(source));os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.dont_write_bytecode=True
from dtv_efficiency_r1.control import load_bindings
from dtv_efficiency_r1.profile import gate
gate(source/'docs/dtv-efficiency-correction-r1-20260930/BINDINGS.json',json.loads((control/'EXECUTION-APPROVAL.json').read_text()))
c=load_bindings();inputs={}
for job in c['jobs']:
 for m in job['models'].values():inputs[m['checkpoint']]=m['checkpoint_sha256']
 for v in (job['capture'],job['saved_scores'],job['offline_scores']):inputs[v['artifact']]=v['artifact_sha256']
 inputs[job['capture']['world_model_checkpoint']]=job['capture']['world_model_checkpoint_sha256']
runtime=c['runtime']+json.loads((source/'docs/dtv-efficiency-20260930/FINAL-RECOVERY.json').read_text())['model_runtime_sources']
for r in runtime:inputs[r['path']]=r['sha256']
authenticated=[]
for path,digest in inputs.items():
 if not P(path).is_file() or sha(path)!=digest:raise RuntimeError('bound input/runtime missing or changed: '+path)
 authenticated.append(dict(path=path,sha256=digest,bytes=P(path).stat().st_size))
source_bytes=sum(p.stat().st_size for p in source.rglob('*') if p.is_file())
if source_bytes>4000000:raise RuntimeError('complete deployed source exceeds cap')
receipt=dict(status='staged_and_authenticated',observed_unix=time.time(),source_sha256=I['manifest_sha256'],enabled_approval_sha256=I['enabled_approval_sha256'],source_bytes=source_bytes,authenticated_bindings=authenticated,checkpoint_deserialization=False,research_inference=False,exclusive_checks=state)
write(control/'STAGE.json',receipt);print(json.dumps(receipt))
"""
    elif args.mode=='launch':
        body="""
state=exclusive_check()
if (control/'CONTROLLER-PROCESS.json').exists() or (control/'controller.out').exists() or (control/'controller.err').exists():raise RuntimeError('controller already started or ambiguous; no relaunch')
if sha(control/'EXECUTION-APPROVAL.json')!=I['enabled_approval_sha256'] or sha(control/'AUTHORIZATION.json')!=I['authority_sha256']:raise RuntimeError('authority changed')
sys.path.insert(0,str(source));sys.dont_write_bytecode=True
from dtv_efficiency_r1.profile import gate
gate(source/'docs/dtv-efficiency-correction-r1-20260930/BINDINGS.json',json.loads((control/'EXECUTION-APPROVAL.json').read_text()))
out=(control/'controller.out').open('xb');err=(control/'controller.err').open('xb')
env=dict(os.environ,PYTHONPATH=str(source),PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4')
argv=['/usr/bin/python3.9','-m','dtv_efficiency_r1.campaign','--submit','--run',str(run),'--approval',str(control/'EXECUTION-APPROVAL.json')]
started=time.time();process=subprocess.Popen(argv,cwd=source,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
identity=process_identity(process.pid)
record=dict(status='launched_once',launch_unix=started,process=identity,pid=process.pid,argv=argv,source_sha256=I['manifest_sha256'],enabled_approval_sha256=I['enabled_approval_sha256'],automatic_retry=False,exclusive_checks=state)
write(control/'CONTROLLER-PROCESS.json',record);out.close();err.close();print(json.dumps(record))
"""
    else:
        body="""
launch=json.loads((control/'CONTROLLER-PROCESS.json').read_text());current=process_identity(launch['pid']);expected=launch['process']
alive=bool(current and expected and current['start_ticks']==expected['start_ticks'] and current['state']!='Z')
events=[json.loads(x) for x in (run/'DISPATCH.jsonl').read_text().splitlines()] if (run/'DISPATCH.jsonl').exists() else []
submitted=[e for e in events if e['event']=='submitted'];terminal=[e for e in events if e['event']=='terminal'];ids=[e['allocation_id'] for e in submitted]
accounting=command(['sacct','-n','-P','-X','-j',','.join(ids),'--format=JobIDRaw,JobName,State,ExitCode,ElapsedRaw,AllocTRES,NodeList']) if ids else None
receipt=dict(observed_unix=time.time(),exact_controller_alive=alive,process=current,expected_process=expected,controller_stderr_bytes=(control/'controller.err').stat().st_size,controller_stdout_bytes=(control/'controller.out').stat().st_size,submitted=submitted,terminal=terminal,known_terminal_gpu_seconds=sum(e['elapsed_seconds'] for e in terminal),stop=json.loads((run/'STOP.json').read_text()) if (run/'STOP.json').exists() else None,all_complete=any(e['event']=='all_complete' for e in events),scheduler=accounting,run_bytes=sum(p.stat().st_size for p in run.rglob('*') if p.is_file()) if run.exists() else 0,control_bytes=sum(p.stat().st_size for p in control.rglob('*') if p.is_file()),sealed_workers=[p.name for p in run.iterdir() if p.is_dir() and (p/'CONTROL-SEAL.json').is_file()] if run.exists() else [])
print(json.dumps(receipt))
"""
    call(remote(body),args.label,timeout=240 if args.mode=='stage' else 90)
if __name__=='__main__':main()
