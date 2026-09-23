"""Read-only R3 fault reconciliation; scientific payloads remain hash-only."""
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[2]/'docs/active-counterfactual-verification-20260923/control-r3'))
import transport3 as t
original_configuration=t.configuration
config=original_configuration()
t.HERE=HERE
t.configuration=lambda: config
CODE=r'''
from pathlib import Path
import sys,subprocess,os,time
b=CONFIG['binding'];root=Path(b['control_source'])/CONFIG['rel'];control=Path(b['control']);run=Path(b['run'])
sys.path.insert(0,str(root));import r3_core as r
ctx=r.Context(control/'EXECUTION-APPROVAL.json');r.verify_baseline(ctx)
assert r.read(control/'STOP-R3.json')['error']=="ValueError('Wrong scheduler task identity')"
identity=r.read(control/'CONTROLLER-PROCESS.json');assert identity['pid']==940709 and str(identity['start_ticks'])=='894795578'
for ident in (identity,ctx.baseline['r2_controller'],{'pid':684587,'start_ticks':'893012584'}):
 stat=Path('/proc',str(ident['pid']),'stat')
 if stat.exists():
  fields=stat.read_text().rsplit(')',1)[1].split();assert fields[19]!=str(ident['start_ticks']) or fields[0]=='Z'
ledger=r.lines(control/'CAMPAIGN-R3.jsonl');submitted=[v for v in ledger if v['event']=='submitted']
assert len(submitted)==13 and [v['spec'] for v in submitted]==ctx.jobs[24:37]
known={v['job'] for v in ctx.baseline['allocations']}|{v['job'] for v in submitted}
p=subprocess.run(['sacct','-X','-n','-P','--starttime=2026-09-23','--user='+os.environ['USER'],'--format='+r.FIELDS],capture_output=True,text=True,timeout=45)
q=subprocess.run(['squeue','-h','-u',os.environ['USER'],'-o','%i|%j|%T'],capture_output=True,text=True,timeout=30)
assert p.returncode==q.returncode==0,(p.stderr,q.stderr)
raw=[s for s in p.stdout.splitlines() if 'acv0' in s.lower() or s.split('|')[0] in known];alloc=[r.parse_row(s) for s in raw]
assert len(alloc)==38 and {v['job'] for v in alloc}==known
assert not any('acv0' in s.lower() or s.split('|')[0] in known for s in q.stdout.splitlines())
byid={v['job']:v for v in alloc}
assert all(byid[v['job']]==v for v in ctx.baseline['allocations'])
rows,checks=r.accept_existing(ctx);rows=list(rows);checks=list(checks)
terminal=[v for v in ledger if v['event']=='terminal'];assert len(terminal)==12
for i,entry in enumerate(submitted):
 row=byid[entry['job']];checks.append(r.verify_worker(ctx,entry['spec'],row))
 if i<12:
  old=terminal[i];assert old['job']==row['job'] and all(old[k]==v for k,v in row.items());rows.append(old)
 else:
  assert row['job']=='304237' and row['seconds']==157
  rows.append(dict(row,spec=entry['spec'],attempt=1,event='existing_completed_supplier',campaign_gpu_seconds=4862,campaign_cpu_stage_seconds=0))
assert len(rows)==37 and [v['spec'] for v in rows]==ctx.jobs[:37]
assert sum(v['seconds']*v['gpus'] for v in alloc)==4862
assert not any((run/j['key']).exists() for j in ctx.jobs[37:])
assert not any((run/n).exists() for n in ('MODEL-FREEZE.json','PRE-ANALYSIS-ACCOUNTING.json','COMPUTE-COMPLETE.json','final-preservation'))
paths=dict(ctx.baseline['paths'],r3_source=b['control_source'],r3_control=b['control'])
inventory={}
for label,path in paths.items():
 for f in sorted(Path(path).rglob('*')):
  if f.is_file():
   assert not f.is_symlink();inventory[label+'/'+f.relative_to(path).as_posix()]={'bytes':f.stat().st_size,'sha256':r.sha(f)}
namespaces={}
for label,path in [('source',b['control_source']),('control',b['control'])]:
 namespaces[label]=sorted(str(v) for v in Path(path).parent.iterdir() if 'active-counterfactual' in v.name.lower() or 'acv0' in v.name.lower())
 assert set(namespaces[label])==set(ctx.baseline['namespaces'][label])|{path}
result=dict(ctx.baseline)
result.update(unix=time.time(),paths=paths,inventory=inventory,r3_binding=b,r3_controller=identity,namespaces=namespaces,
 allocations=alloc,scheduler_raw=raw,successful_rows=rows,successful_checks=checks,r3_ledger=ledger,
 r3_suppliers=r.lines(control/'SCIENTIFIC-TASKS-R3.jsonl'),r3_stop=r.read(control/'STOP-R3.json'),r3_stop_sha256=r.sha(control/'STOP-R3.json'),
 r3_scheduler_observations=r.lines(control/'SCHEDULER-OBSERVATIONS.jsonl'),r3_controller_stderr=(control/'controller.err').read_text(),
 gpu_seconds=4862,cpu_stage_seconds=0,successful_tasks=37,unsubmitted_tasks=302,next_spec=ctx.jobs[37],
 original_baseline_unchanged=True,live_or_unknown_jobs=0,scientific_payloads_decoded=0)
print(json.dumps(result))
'''
if __name__=='__main__':t.once('BASELINE-CAPTURE',CODE)
