"""Read-only reconciliation and bounded setter arithmetic diagnostic; no episodes."""
import json,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'recovery-r3'
I=json.loads((OLD/'IDENTITIES.json').read_text())
SCRIPT=r'''
import json,pathlib,hashlib,subprocess,time,os
P=pathlib.Path
I=IDENTITIES
run=P(I['run']);root=run/'recovery-r3'
def sha(p):return hashlib.sha256(P(p).read_bytes()).hexdigest()
events=[json.loads(x) for x in (root/'DISPATCH-R3.jsonl').read_text().splitlines()]
ss=[x for x in events if x['event']=='submitted'];tt=[x for x in events if x['event']=='terminal'];aa=[x for x in events if x['event']=='accepted']
if len(ss)!=22 or len(tt)!=22 or len(aa)!=21 or [x['task'] for x in ss]!=[x['task'] for x in tt] or [x['task'] for x in ss[:-1]]!=[x['task'] for x in aa]:raise RuntimeError('unresolved or changed R3 work')
ids=[r[0] for r in I['terminal_rows']]+[x['allocation_id'] for x in ss]
r=subprocess.run(['sacct','-n','-P','-X','-j',','.join(ids),'--format=JobIDRaw,JobName%200,State,ExitCode,ElapsedRaw,AllocTRES,NodeList'],capture_output=True,text=True,check=True,timeout=60)
rows=[s.split('|') for s in r.stdout.splitlines() if s.strip()]
for row in rows:
 if row[-1]=='':row.pop()
if rows[:9]!=I['terminal_rows'] or len(rows)!=31:raise RuntimeError('historical attempts changed')
for row,s,t in zip(rows[9:],ss,tt):
 expected=[s['allocation_id'],'dtveff1-'+s['task'],t['state'],t['exit'],str(t['elapsed_seconds']),t['resources'],t['node']]
 if row!=expected or t['state']!=('FAILED' if s==ss[-1] else 'COMPLETED'):raise RuntimeError('terminal reconciliation differs')
q=subprocess.run(['squeue','-h','-u','ckontzias','-o','%i|%j|%T|%N'],capture_output=True,text=True,check=True,timeout=60)
if any('dtveff1-' in x for x in q.stdout.splitlines()):raise RuntimeError('live study allocation')
for p in P('/proc').glob('[0-9]*'):
 try:
  if p.stat().st_uid==os.getuid() and any(x in (p/'cmdline').read_bytes().split(b'\0') for x in [b'dtv_success_cost.campaign',b'dtv_success_cost_r1.campaign',b'dtv_success_cost_r2.campaign',b'dtv_success_cost_r3.campaign',b'dtv_success_cost_r4.campaign']):raise RuntimeError('live study controller')
 except (OSError,ValueError):pass
carried=[]
for s,t,a in zip(ss[:-1],tt[:-1],aa):
 d=root/'workers'/s['task'];seal=json.loads((d/'SEAL.json').read_text())
 if sha(d/'SEAL.json')!=a['seal_sha256']:raise RuntimeError('accepted seal differs')
 for member in seal['files']:
  p=d/member['path']
  if p.stat().st_size!=member['bytes'] or sha(p)!=member['sha256']:raise RuntimeError('sealed successful artifact changed')
 carried.append(dict(task=s['task'],allocation_id=s['allocation_id'],elapsed_seconds=t['elapsed_seconds'],seal_sha256=a['seal_sha256'],output_lineage='recovery-r3'))
failure=root/'workers'/ss[-1]['task']
if any(p.name.endswith('.trace.jsonl') or p.name=='SEAL.json' for p in failure.iterdir()):raise RuntimeError('failed attempt episode ambiguity')
value=dict(observed_unix=time.time(),all_attempts_terminal=True,terminal_rows=rows,r3_stop_sha256=sha(root/'STOP-R3.json'),r3_dispatch_sha256=sha(root/'DISPATCH-R3.jsonl'),r3_resolution_sha256=sha(root/'STOP-RESOLUTION.json'),carried=carried,
 failed_task=ss[-1]['task'],failed_allocation=ss[-1]['allocation_id'],failed_seconds=tt[-1]['elapsed_seconds'],
 failed_members=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(failure.iterdir())],
 failure=json.loads((failure/'FAILURE.json').read_text()),gpu_seconds=1622,cpu_seconds=178,completed_gpu_workers=27,completed_episodes=216,scientific_aggregates_opened=False,
 error_logs=[dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p)) for p in [P(I['recovery_control'])/'controller.err',root/'workers/pusht-3819-6101.err',root/'workers/pusht-3819-6101.out']],
 technical_gate=[x for x in events if x['event']=='technical_tranche_passed'])
# Pure setter/getter arithmetic in existing container, no Space, environment,
# rendering, physics integration, model, new reference or scheduler allocation.
code=r"""
import numpy as np,pymunk,json,time,resource
start=time.monotonic();rng=np.random.default_rng(246801);count=0;maximum=0.;same=True;ratio=0.
for i in range(10000):
 expected=rng.uniform(10,500,2).astype(np.float32).astype(np.float64)
 body=pymunk.Body(1,1);body.center_of_gravity=(0,45);body.angle=float(rng.uniform(0,2*np.pi));body.position=expected.tolist()
 actual=np.array(body.position);err=np.abs(actual-expected);bound=8*np.finfo(np.float64).eps*np.maximum(1,np.abs(expected))
 count+=int(np.any(err));maximum=max(maximum,float(err.max()));ratio=max(ratio,float((err/bound).max()));same=same and np.array_equal(actual.astype(np.float32),expected.astype(np.float32))
# Only the failed worker's already-preserved initial coordinate: emit numeric
# verification errors, never source values, targets, outcomes or scientific effects.
with np.load('FAILED_INPUT',allow_pickle=False) as data:state=data['initial_state'].astype(np.float64)
body=pymunk.Body(1,1);body.center_of_gravity=(0,45);body.angle=float(state[4]);body.position=state[2:4].tolist()
delta=np.abs(np.array(body.position)-state[2:4])
print(json.dumps(dict(artificial_fixtures=10000,nonexact_setter_roundtrips=count,max_error=maximum,all_f32_roundtrips_equal=same,max_bound_fraction=ratio,
 failed_worker_block_position_mismatch_indices=(np.flatnonzero(delta)+2).tolist(),failed_worker_max_roundtrip_error=float(delta.max()),
 failed_worker_f32_roundtrip_equal=np.array_equal(np.array(body.position).astype(np.float32),state[2:4].astype(np.float32)),
 wall_seconds=time.monotonic()-start,rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,pymunk_version=pymunk.version,
 environment_created=False,space_created=False,physics_steps=0,model_calls=0,gpu=False,slurm_allocations=0,new_references_opened=False)))
""".replace('FAILED_INPUT',str(failure/'SOURCE-INPUT.npz'))
base=P('/lustreFS/data/superworld/ckontzias/thesis')
cmd=['apptainer','exec','--cleanenv','--bind',str(base)+':'+str(base),str(base/'containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif'),'env','OMP_NUM_THREADS=4','MKL_NUM_THREADS=4','OPENBLAS_NUM_THREADS=4','PYTHONDONTWRITEBYTECODE=1',str(base/'envs/hi-lewm-artifact-py311-cu121-swm006/bin/python'),'-B','-c',code]
s=subprocess.run(cmd,capture_output=True,text=True,timeout=60)
if s.returncode:raise RuntimeError('preserved arithmetic test failure '+s.stderr)
value['setter_diagnostic']=json.loads(s.stdout);value['setter_stderr']=s.stderr
print(json.dumps(value))
'''
started=time.monotonic()
r=subprocess.run(['wsl.exe','-d','Thesis-Ubuntu','-u','chris','--','ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=15','prometheus','python3.9 -'],input=SCRIPT.replace('IDENTITIES',repr(I)).encode(),capture_output=True,timeout=180)
receipt=dict(returncode=r.returncode,stdout=r.stdout.decode(errors='replace'),stderr=r.stderr.decode(errors='replace'),wall_seconds=time.monotonic()-started,automatic_retry=False)
with (HERE/'RECONCILIATION-02.json').open('x') as f:json.dump(receipt,f,indent=2)
if r.returncode:raise RuntimeError(receipt['stderr'])
with (HERE/'DIAGNOSTIC-02.json').open('x') as f:json.dump(json.loads(receipt['stdout']),f,indent=2)
print(json.dumps(json.loads(receipt['stdout'])['setter_diagnostic']))
