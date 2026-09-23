"""Read-only authentication of the sole failed attempt; no allocation."""
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'execution-v2'))
import operate as o
o.HERE=HERE
CODE=r'''
from pathlib import Path
import hashlib,subprocess,time,os
source=Path(CONFIG['source']);run=Path(CONFIG['run']);control=Path(CONFIG['control'])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
manifest=source/CONFIG['rel']/'SOURCE-MANIFEST.json'
assert sha(manifest)==CONFIG['manifest_sha']
for name,h in json.loads(manifest.read_text())['files'].items():assert sha(source/name)==h,name
assert sha(run/'APPROVAL.json')=='7ea5f67225ee1bff091e705e7515a4ed8f3589694e6093f1c2e7c607d27a6a88'
assert sha(control/'EXECUTION-APPROVAL.json')==sha(run/'APPROVAL.json')
assert sha(run/'collect-fit-490'/'FAILURE.json')=='25468460fc9082a66c363c8dd88063a16548f306e0896a51c6f358a2fa0acd4e'
assert sha(control/'controller.err')=='cdc92331bdde6686b0d422351cbf102e63e70a8410a531b5deb40511b8c3c00a'
rows=[json.loads(s) for s in (run/'DISPATCH.jsonl').read_text().splitlines()]
assert [r['job'] for r in rows if r['event']=='submitted']==['304189']
terminal=[r for r in rows if r['event']=='terminal'];assert len(terminal)==1
assert terminal[0]['state']=='FAILED' and terminal[0]['exit_code']=='1:0' and terminal[0]['seconds']==23
assert terminal[0]['spec']['key']=='collect-fit-490' and terminal[0]['gpu_seconds']==23 and terminal[0]['cpu_seconds']==0
identity=json.loads((control/'CONTROLLER-PROCESS.json').read_text());assert identity['pid']==550069 and str(identity['start_ticks'])=='892062738'
stat=Path('/proc/550069/stat');active=False
if stat.exists():
 parts=stat.read_text().rsplit(')',1)[1].split();active=parts[19]=='892062738' and parts[0]!='Z'
assert not active,'Old controller active'
fields='JobIDRaw,JobName%100,State,ExitCode,ElapsedRaw,AllocCPUS,AllocTRES,NodeList,Partition,QOS,Account'
a=subprocess.run(['sacct','-X','-n','-P','--starttime=2026-09-23','--user='+os.environ['USER'],'--format='+fields],capture_output=True,text=True,timeout=30)
q=subprocess.run(['squeue','-h','-u',os.environ['USER'],'-o','%i|%j|%T'],capture_output=True,text=True,timeout=30)
assert a.returncode==q.returncode==0,(a.stderr,q.stderr)
prior=[s.split('|') for s in a.stdout.splitlines() if 'acv0' in s.lower() or s.split('|')[0]=='304189']
assert len(prior)==1 and prior[0][:6]==['304189','acv0b1-collect-fit-490','FAILED','1:0','23','4'],prior
assert prior[0][7:11]==['gpu09','a6000','normal-a6000','superworld'],prior
assert not any('acv0' in s.lower() or s.startswith('304189|') for s in q.stdout.splitlines()),q.stdout
members={}
for label,root in [('source',source),('control',control),('run',run)]:
 for p in sorted(root.rglob('*')):
  if p.is_file():
   assert not p.is_symlink()
   members[label+'/'+p.relative_to(root).as_posix()]={'bytes':p.stat().st_size,'sha256':sha(p)}
assert sum(v['bytes'] for v in members.values())<10_000_000
print(json.dumps({'unix':time.time(),'paths':{'source':str(source),'control':str(control),'run':str(run)},'members':members,
 'source_manifest':CONFIG['manifest_sha'],'approval_sha256':sha(run/'APPROVAL.json'),'terminal':terminal[0],
 'scheduler_row':prior[0],'controller_identity':identity,'old_controller_active':False,'live_acv0_jobs':[],
 'prior_gpu_seconds':23,'prior_cpu_stage_seconds':0,'measured_device_name':None,'scientific_payload_reads':0}))
'''
if __name__=='__main__':o.once('PRIOR-RECONCILIATION',CODE)
