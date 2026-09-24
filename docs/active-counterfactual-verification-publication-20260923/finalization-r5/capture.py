"""Read-only reconciliation of completed ACV0 scientific work after R4 stop."""
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[2]/'docs/active-counterfactual-verification-20260923/control-r4'))
import transport4 as t
config=t.configuration();t.HERE=HERE;t.configuration=lambda:config
CODE=r'''
from pathlib import Path
import sys,subprocess,os,time
b=CONFIG['binding'];root=Path(b['control_source'])/CONFIG['rel'];control=Path(b['control']);run=Path(b['run'])
sys.path.insert(0,str(root));import r4_core as r
ctx=r.Context(control/'EXECUTION-APPROVAL.json');r.verify_baseline(ctx)
stop=r.read(control/'STOP-R4.json');assert stop['error']=="ValueError('Live campaign allocation at finalization')"
identity=r.read(control/'CONTROLLER-PROCESS.json');assert identity['pid']==1041441 and identity['start_ticks']=='895662237'
stat=Path('/proc',str(identity['pid']),'stat')
if stat.exists():
 fields=stat.read_text().rsplit(')',1)[1].split();assert fields[19]!=identity['start_ticks'] or fields[0]=='Z'
ledger=r.lines(control/'CAMPAIGN-R4.jsonl');terminal=[v for v in ledger if v['event']=='terminal'];submitted=[v for v in ledger if v['event']=='submitted']
assert len(terminal)==len(submitted)==302 and [v['spec'] for v in terminal]==ctx.jobs[37:]
assert not any('unresolved' in v['event'] for v in ledger)
rows=ctx.baseline['successful_rows']+terminal;known={'304189'}|{v['job'] for v in rows}
p=subprocess.run(['sacct','-n','-P','--starttime=2026-09-23','--user='+os.environ['USER'],'--format='+r.FIELDS+',TotalCPU,MaxRSS'],capture_output=True,text=True,timeout=60)
q=subprocess.run(['squeue','-h','-u',os.environ['USER'],'-o','%i|%j|%T'],capture_output=True,text=True,timeout=30)
assert p.returncode==q.returncode==0,(p.stderr,q.stderr)
raw=[s.split('|') for s in p.stdout.splitlines() if 'acv0' in s.lower() or s.split('|')[0].split('.')[0] in known]
alloc=[r.parse_row(v[:12]) for v in raw if '.' not in v[0]]
assert len(alloc)==len(known)==340 and {v['job'] for v in alloc}==known
queue=[s for s in q.stdout.splitlines() if 'acv0' in s.lower() or s.split('|')[0] in known];assert not queue
byid={v['job']:v for v in alloc};assert byid['304189']==next(v for v in ctx.baseline['allocations'] if v['job']=='304189')
checks=[]
for j,row in zip(ctx.jobs,rows):
 assert row['spec']==j and all(row[k]==v for k,v in byid[row['job']].items())
 checks.append(r.verify_worker(ctx,j,row))
assert len(rows)==339 and len({v['job'] for v in rows})==339
assert sum(v['seconds']*v['gpus'] for v in alloc)==19365
assert sum(v['seconds'] for v in alloc if not v['gpus'])==52
assert not any((control/n).exists() for n in ('FINAL-SCHEDULER.json','COMPUTE-COMPLETE.json','COMBINED-CAMPAIGN.json'))
assert not any((run/n).exists() for n in ('COMPUTE-COMPLETE.json','final-preservation'))
paths=dict(ctx.baseline['paths'],r4_source=b['control_source'],r4_control=b['control']);inventory={}
for label,path in paths.items():
 for f in sorted(Path(path).rglob('*')):
  if f.is_file():
   assert not f.is_symlink();inventory[label+'/'+f.relative_to(path).as_posix()]={'bytes':f.stat().st_size,'sha256':r.sha(f)}
namespaces={}
for label,path in [('source',b['control_source']),('control',b['control'])]:
 namespaces[label]=sorted(str(v) for v in Path(path).parent.iterdir() if 'active-counterfactual' in v.name.lower() or 'acv0' in v.name.lower())
 assert set(namespaces[label])==set(ctx.baseline['namespaces'][label])|{path}
print(json.dumps(dict(unix=time.time(),paths=paths,inventory=inventory,r4_binding=b,r4_controller=identity,namespaces=namespaces,
 allocations=alloc,scheduler_raw_steps=raw,queue_raw=queue,successful_rows=rows,successful_checks=checks,
 r4_stop=stop,r4_stop_sha256=r.sha(control/'STOP-R4.json'),r4_controller_stderr=(control/'controller.err').read_text(),
 scientific_suppliers=r.lines(control/'SCIENTIFIC-TASKS-R4.jsonl'),gpu_seconds=19365,cpu_stage_seconds=52,
 successful_tasks=339,attempts=340,live_or_unknown_jobs=0,scientific_payloads_decoded=0,source_and_history_unchanged=True,
 model_freeze_sha256=r.sha(run/'MODEL-FREEZE.json'),analysis_seal_sha256=r.sha(run/'analysis/SEAL.json'),
 original_fault_queue_stdout_preserved=False)))
'''
if __name__=='__main__':t.once('BASELINE-CAPTURE',CODE)
