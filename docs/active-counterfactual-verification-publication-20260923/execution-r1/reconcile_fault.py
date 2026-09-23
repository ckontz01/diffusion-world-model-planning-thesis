"""One metadata-only reconciliation of the R1 hostname acceptance fault."""
import operate as o
CODE=r'''
from pathlib import Path
import hashlib,subprocess,sys,time,os
run=Path(CONFIG['run']);control=Path(CONFIG['control']);source=Path(CONFIG['source'])
sys.path.insert(0,str(source/CONFIG['rel']))
import common as c,recovery,dispatch
auth=c.Authorization(control/'EXECUTION-APPROVAL.json',run)
assert (run/'STOP.json').exists(),'No terminal controller fault yet; do not presume'
identity=c.read(control/'CONTROLLER-PROCESS.json');stat=Path('/proc',str(identity['pid']),'stat');active=False
if stat.exists():
 fields=stat.read_text().rsplit(')',1)[1].split();active=fields[19]==str(identity['start_ticks']) and fields[0]!='Z'
assert not active,'Controller still finishing; preserve state'
rows=[json.loads(s) for s in (run/'DISPATCH.jsonl').read_text().splitlines()]
submitted=[r for r in rows if r['event']=='submitted'];terminal=[r for r in rows if r['event']=='terminal']
assert len(submitted)==len(terminal)==1 and submitted[0]['job']=='304193'
assert terminal[0]['state']=='COMPLETED' and terminal[0]['exit_code']=='0:0'
assert terminal[0]['gpu_seconds']==23+terminal[0]['seconds']
q=subprocess.run(['squeue','-h','-u',os.environ['USER'],'-o','%i|%j|%T'],capture_output=True,text=True,timeout=30)
fields='JobIDRaw,JobName%100,State,ExitCode,ElapsedRaw,AllocCPUS,AllocTRES,NodeList,Partition,QOS,Account,TotalCPU,MaxRSS'
a=subprocess.run(['sacct','-n','-P','--starttime=2026-09-23','--user='+os.environ['USER'],'--format='+fields],capture_output=True,text=True,timeout=30)
assert a.returncode==q.returncode==0
allocations=[line for line in a.stdout.splitlines() if 'acv0' in line.lower() or line.split('|')[0].split('.')[0] in ('304189','304193')]
top=[line.split('|') for line in allocations if '.' not in line.split('|')[0]]
assert {r[0] for r in top}=={'304189','304193'},allocations
assert not any('acv0' in line.lower() or line.split('|')[0] in ('304189','304193') for line in q.stdout.splitlines()),q.stdout
assert not any('unresolved' in row['event'] for row in rows)
seal=c.verify_seal(run/'collect-fit-490',c.grid()[0])
tech=c.read(run/'collect-fit-490/TECHNICAL.json');hardware=c.read(run/'collect-fit-490/HARDWARE.json')
assert tech['passed'] and tech['models_unchanged'] and hardware['accepted']
recovery.authenticate_prior_files();recovery.verify_prior_copy(run)
logs={}
for path in (control/'controller.err',run/'STOP.json',run/'collect-fit-490-stderr.log',run/'collect-fit-490-304193.err'):
 if path.exists():
  raw=path.read_bytes();assert len(raw)<131072
  logs[str(path)]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'text':raw.decode(errors='replace')}
metadata={}
for name in ('APPROVAL.json','CONTROLLER.json','DISPATCH.jsonl','CAMPAIGN-ATTEMPTS.jsonl','STOP.json','collect-fit-490/SEAL.json','collect-fit-490/HARDWARE.json','collect-fit-490/TECHNICAL.json'):
 path=run/name;metadata[name]={'bytes':path.stat().st_size,'sha256':c.sha(path)}
print(json.dumps({'unix':time.time(),'controller_identity':identity,'controller_active':active,
 'submitted':submitted,'terminal':terminal,'allocation_rows':allocations,'no_live_acv0_jobs':True,'unresolved':[],
 'campaign_attempts':2,'prior_failed_attempts':1,'successful_scheduler_allocations':1,
 'campaign_gpu_seconds':terminal[0]['gpu_seconds'],'cpu_stage_seconds':0,'authorized_replacement_count':1,'automatic_retry_count':0,
 'hardware':hardware,'worker_technical_passed':True,'worker_technical':tech,'worker_seal_verified':True,
 'worker_member_count':len(seal['files']),'worker_member_bytes':sum(v['bytes'] for v in seal['files'].values()),
 'metadata_hashes':metadata,'technical_fault_logs':logs,'storage':dispatch.storage(c.ROOT,run,c.grid()),
 'scientific_tasks_accepted':0,'task545_submitted':False,'tranche_passed':False,'compute_complete':False,
 'scientific_payloads_or_effects_opened':False,'old_originals_and_prior_copies_authenticated':True}))
'''
if __name__=='__main__':o.once('FAULT-RECONCILIATION',CODE)
