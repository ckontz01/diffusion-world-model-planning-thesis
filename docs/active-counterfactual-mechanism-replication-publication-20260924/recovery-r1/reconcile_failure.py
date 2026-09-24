"""Read-only all-attempt reconciliation after the R1 import-path failure."""
import sys
from pathlib import Path
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]/'docs/active-counterfactual-mechanism-replication-20260924/control-r1'
sys.path.insert(0,str(ROOT))
import r1 as r
import transport

code=transport.prelude()+'''import acceptance_r1 as acceptance;import scheduler
state=acceptance.ledger(control,ctx.jobs,False)
assert list(state['submitted'])==['fit-pair1-joint'] and state['submitted']['fit-pair1-joint']['job']=='304591'
assert not state['accepted']
identity=r.read(control/'CONTROLLER-PROCESS.json');p=Path('/proc')/str(identity['pid'])
assert not p.exists() or p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]!=str(identity['start_ticks'])
cmd=['/usr/bin/sacct','-X','-n','-P','-j','304589,304591','--format='+scheduler.FIELDS]
p=subprocess.run(cmd,capture_output=True,text=True,timeout=60);assert p.returncode==0
rows=[scheduler.parse(x) for x in p.stdout.splitlines() if x]
assert {x['job'] for x in rows}=={'304589','304591'}
for row in rows:scheduler.allocation(ctx.jobs[0],row,successful=False)
q=subprocess.run(['/usr/bin/squeue','-h','-j','304589,304591','-o','%i|%j|%T|%N'],capture_output=True,text=True,timeout=30)
assert q.returncode==0 and not q.stdout.strip()
assert all(x['state']=='FAILED' for x in rows)
for row in rows:
 expected=ctx.baseline['failed_row'] if row['job']=='304589' else state['terminal']['fit-pair1-joint']['row']
 assert row==expected
assert not (ctx.run/'ALL-MODELS-FROZEN.json').exists()
failed=ctx.run/'fit-pair1-joint';assert {p.name for p in failed.iterdir()}=={'FAILURE.json'}
source_origins={name:str(r.c.BASE/name) for name in ('model.py','tree.py')}
assert all(r.c.sha(p)==r.read(r.c.ROOT/'SOURCE-MANIFEST.json')['files'][str(Path(p).relative_to(r.c.REPO))] for p in source_origins.values())
logs={}
for pth in (ctx.run/'logs').glob('fit-pair1-joint*'):
 logs[pth.name]=dict(bytes=pth.stat().st_size,sha256=r.sha(pth))
 if pth.suffix=='.err':logs[pth.name]['text']=pth.read_text(errors='replace')
control_records={n:dict(sha256=r.sha(control/n),text=(control/n).read_text()) for n in ('STOP.json','HISTORICAL-RESOLUTION.json','CAMPAIGN.jsonl','SCHEDULER.jsonl','fit-pair1-joint.SUBMIT.json','CONTROLLER-PROCESS.json')}
roots=dict(science_source=r.c.REPO,recovery_source=r.ROOT,original_control=ctx.old_control,recovery_control=control,run=ctx.run)
inventory={label+'/'+n:i for label,root in roots.items() for n,i in r.c.members(root).items()}
r.c.verify_seal(ctx.run/'reused')
print(json.dumps(dict(unix=time.time(),rows=rows,sacct_raw=p.stdout,squeue_raw=q.stdout,live_jobs=0,ambiguous_submissions=[],successful_tasks=0,attempts=2,gpu_seconds=0,cpu_seconds=sum(x['seconds'] for x in rows),remaining_task_count=8197,full_future_cpu_reservation=36000,combined_full_cpu_reservation=36000+sum(x['seconds'] for x in rows),approved_cpu_ceiling=36000,controller_exited=True,model_freeze=False,technical_tranche_reached=False,failed_worker=r.read(failed/'FAILURE.json'),worker_logs=logs,control_records=control_records,roots={k:str(v) for k,v in roots.items()},inventory=inventory,study_module_sources=source_origins,scientific_outcomes_read=False,research_fitting_started=False)))
'''
response=transport.remote(code)
receipt=dict(unix=time.time(),returncode=response.returncode,stdout=response.stdout.decode(errors='replace'),stderr=response.stderr.decode(errors='replace'),read_only=True)
r.write(HERE/'FAULT-RECONCILIATION.json',receipt)
r.require(response.returncode==0,'Complete failure reconciliation required')
data=r.c.json.loads(response.stdout)
print(r.c.json.dumps({k:data[k] for k in ('attempts','successful_tasks','live_jobs','ambiguous_submissions','cpu_seconds','combined_full_cpu_reservation','approved_cpu_ceiling','failed_worker')}))
