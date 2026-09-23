"""Read-only fault reconciliation; scientific payloads are hash-only."""
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[2]/'docs/active-counterfactual-verification-20260923/control-r2'))
import transport as t
t.HERE=HERE
# R2 configuration still refers to its original, immutable authorization.
def configuration():
    original=HERE.parent/'continuation-r2'
    b=t.r.binding(t.r.sha(t.r.ROOT/'SOURCE-MANIFEST.json'))
    return dict(binding=b,rel=t.REL,transport=t.r.read(t.r.ROOT/'SOURCE-TRANSPORT.json'),baseline=t.r.read(t.r.ROOT/'BASELINE.json'),
                approval_sha256=t.r.sha(original/'EXECUTION-APPROVAL.json'))
t.configuration=configuration
CODE=r'''
from pathlib import Path
import sys,subprocess,os,time
b=CONFIG['binding'];root=Path(b['control_source'])/CONFIG['rel'];control=Path(b['control']);run=Path(b['run'])
sys.path.insert(0,str(root));import r2_core as r
ctx=r.Context(control/'EXECUTION-APPROVAL.json');r.verify_baseline(ctx)
assert r.read(control/'STOP-R2.json')['error']=="ValueError('Unambiguous scheduler columns')"
identity=r.read(control/'CONTROLLER-PROCESS.json');assert identity['pid']==788617 and identity['start_ticks']=='893946619'
for ident in (identity,ctx.baseline['original_controller']):
 stat=Path('/proc',str(ident['pid']),'stat')
 if stat.exists():
  fields=stat.read_text().rsplit(')',1)[1].split();assert fields[19]!=str(ident['start_ticks']) or fields[0]=='Z'
ledger=r.lines(control/'CAMPAIGN-R2.jsonl');submitted=[v for v in ledger if v['event']=='submitted']
assert len(submitted)==23 and [v['spec'] for v in submitted]==ctx.jobs[1:24]
known={'304189','304193'}|{v['job'] for v in submitted}
p=subprocess.run(['sacct','-X','-n','-P','--starttime=2026-09-23','--user='+os.environ['USER'],'--format='+r.FIELDS],capture_output=True,text=True,timeout=45)
q=subprocess.run(['squeue','-h','-u',os.environ['USER'],'-o','%i|%j|%T'],capture_output=True,text=True,timeout=30)
assert p.returncode==q.returncode==0,(p.stderr,q.stderr)
raw=[s for s in p.stdout.splitlines() if 'acv0' in s.lower() or s.split('|')[0] in known];alloc=[r.parse_row(s) for s in raw]
assert len(alloc)==25 and {v['job'] for v in alloc}==known
assert not any('acv0' in s.lower() or s.split('|')[0] in known for s in q.stdout.splitlines())
byid={v['job']:v for v in alloc};assert byid['304189']['state']=='FAILED' and byid['304189']['seconds']==23
existing,receipt=r.accept_existing(ctx);rows=[existing];checks=[receipt]
terminal=[v for v in ledger if v['event']=='terminal'];assert len(terminal)==22
for i,entry in enumerate(submitted):
 row=byid[entry['job']];check=r.verify_worker(ctx,entry['spec'],row);checks.append(check)
 if i<22:
  old=terminal[i];assert old['job']==row['job'] and all(old[k]==v for k,v in row.items());rows.append(old)
 else:
  assert row['job']=='304220' and row['seconds']==160
  rows.append(dict(row,spec=entry['spec'],attempt=1,event='existing_completed_supplier',campaign_gpu_seconds=3015,campaign_cpu_stage_seconds=0))
assert len(rows)==24 and [v['spec'] for v in rows]==ctx.jobs[:24]
assert sum(v['seconds']*v['gpus'] for v in alloc)==3015
assert not any((run/j['key']).exists() for j in ctx.jobs[24:])
assert not any((run/n).exists() for n in ('MODEL-FREEZE.json','PRE-ANALYSIS-ACCOUNTING.json','COMPUTE-COMPLETE.json','final-preservation'))
paths=dict(ctx.baseline['paths'],r2_source=b['control_source'],r2_control=b['control'])
inventory={}
for label,path in paths.items():
 for f in sorted(Path(path).rglob('*')):
  if f.is_file():
   assert not f.is_symlink();inventory[label+'/'+f.relative_to(path).as_posix()]={'bytes':f.stat().st_size,'sha256':r.sha(f)}
namespaces={}
for label,path in [('source',b['control_source']),('control',b['control'])]:
 namespaces[label]=sorted(str(v) for v in Path(path).parent.iterdir() if 'active-counterfactual' in v.name.lower() or 'acv0' in v.name.lower())
 assert set(namespaces[label])==set(ctx.baseline['namespaces'][label])|{path}
print(json.dumps({'unix':time.time(),'paths':paths,'inventory':inventory,'r2_binding':b,'r2_controller':identity,'namespaces':namespaces,
 'allocations':alloc,'scheduler_raw':raw,'successful_rows':rows,'successful_checks':checks,'r2_ledger':ledger,
 'r2_suppliers':r.lines(control/'SCIENTIFIC-TASKS-R2.jsonl'),'r2_stop':r.read(control/'STOP-R2.json'),'r2_stop_sha256':r.sha(control/'STOP-R2.json'),
 'controller_stderr':(control/'controller.err').read_text(),'gate':r.read(run/'TECHNICAL-TRANCHE-PASSED.json'),
 'tranche':r.read(control/'TECHNICAL-TRANCHE-R2.json'),'gpu_seconds':3015,'cpu_stage_seconds':0,'successful_tasks':24,
 'unsubmitted_tasks':315,'next_spec':ctx.jobs[24],'source_manifest':r.SCIENCE_MANIFEST,'worker_approval':r.WORKER_APPROVAL,
 'original_baseline_unchanged':True,'live_or_unknown_jobs':0,'scientific_payloads_decoded':0}))
'''
if __name__=='__main__':t.once('BASELINE-CAPTURE',CODE)
