"""Read-only R2 baseline: hashes/technical metadata, never decode outcomes."""
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'execution-r1'))
import operate as o
o.HERE=HERE
CODE=r'''
from pathlib import Path
import sys,subprocess,os,time,hashlib
source=Path(CONFIG['source']);control=Path(CONFIG['control']);run=Path(CONFIG['run'])
sys.path.insert(0,str(source/CONFIG['rel']))
import common as c,recovery
auth=c.Authorization(control/'EXECUTION-APPROVAL.json',run)
assert auth.approval_sha=='e1e4b6f6d0e0d1fbb83e89d165be793128f02130647e21a1c12c5892d7d90460'
assert c.sha(run/'STOP.json')=='298615b25325a74d113cbda540528bc4b64508a0273b8dd1f1428b1c733f38fe'
expected={'SEAL.json':'c280ffb2e71288e8ea40fc5db34ff42fb464a928f42ab388e8e9b14abb8b3b6a',
 'HARDWARE.json':'44729aa05006bead67008711e31c6448678f2181076b0040c8fde3bb25cdec07',
 'TECHNICAL.json':'6eb9997d681fa98953f6e0917ad89933b30cc9ef3c28934ba65db01be4ad6a7b'}
for n,h in expected.items():assert c.sha(run/'collect-fit-490'/n)==h
c.verify_seal(run/'collect-fit-490',c.grid()[0]);recovery.authenticate_prior_files();recovery.verify_prior_copy(run)
old=c.read(control/'CONTROLLER-PROCESS.json');assert old['pid']==684587 and old['start_ticks']=='893012584'
stat=Path('/proc/684587/stat')
if stat.exists():
 f=stat.read_text().rsplit(')',1)[1].split();assert f[19]!='893012584' or f[0]=='Z'
fields='JobIDRaw,JobName%100,State,ExitCode,ElapsedRaw,AllocCPUS,AllocTRES,NodeList,Partition,QOS,Account,TimelimitRaw'
a=subprocess.run(['sacct','-X','-n','-P','--starttime=2026-09-23','--user='+os.environ['USER'],'--format='+fields],capture_output=True,text=True,timeout=30)
q=subprocess.run(['squeue','-h','-u',os.environ['USER'],'-o','%i|%j|%T'],capture_output=True,text=True,timeout=30)
assert a.returncode==q.returncode==0,(a.stderr,q.stderr)
rows=[s.split('|') for s in a.stdout.splitlines() if 'acv0' in s.lower() or s.split('|')[0] in ('304189','304193')]
assert [r[0] for r in rows]==['304189','304193'],rows
assert rows[0][2:5]==['FAILED','1:0','23'] and rows[1][2:5]==['COMPLETED','0:0','80'],rows
assert not any('acv0' in s.lower() or s.split('|')[0] in ('304189','304193') for s in q.stdout.splitlines())
assert not (run/'TECHNICAL-TRANCHE-PASSED.json').exists() and not (run/'COMPUTE-COMPLETE.json').exists()
inventory={}
for label,root in [('source',source),('control',control),('run',run)]:
 for f in sorted(root.rglob('*')):
  if f.is_file():
   assert not f.is_symlink()
   inventory[label+'/'+f.relative_to(root).as_posix()]={'bytes':f.stat().st_size,'sha256':c.sha(f)}
namespaces={}
for label in ('source','control'):
 parent=Path(CONFIG[label]).parent
 namespaces[label]=sorted(str(p) for p in parent.iterdir() if 'active-counterfactual' in p.name.lower() or 'acv0' in p.name.lower())
 assert set(namespaces[label])=={CONFIG[label],CONFIG['prior']['paths'][label]},namespaces
assert set(str(p) for p in run.parent.iterdir())=={str(run),CONFIG['prior']['paths']['run']}
dispatch=[json.loads(s) for s in (run/'DISPATCH.jsonl').read_text().splitlines()]
terminal=[r for r in dispatch if r['event']=='terminal'];assert len(terminal)==1 and terminal[0]['job']=='304193'
assert not any('unresolved' in r['event'] for r in dispatch)
print(json.dumps({'unix':time.time(),'paths':{'source':str(source),'control':str(control),'run':str(run)},
 'inventory':inventory,'scheduler_rows':rows,'scheduler_fields':fields,'original_controller':old,
 'existing_terminal':terminal[0],'failed_terminal':recovery.prior()['terminal'],
 'hardware':c.read(run/'collect-fit-490/HARDWARE.json'),'technical':c.read(run/'collect-fit-490/TECHNICAL.json'),
 'namespaces':namespaces,'unknown_or_live_attempts':0,'scientific_payloads_decoded':0,'old_controller_active':False}))
'''
if __name__=='__main__':o.once('BASELINE-CAPTURE',CODE)
