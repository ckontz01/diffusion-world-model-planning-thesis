"""Technical-only snapshot; no scientific aggregates or payloads."""
import sys
import operate as o
CODE=r'''
from pathlib import Path
import subprocess,time,hashlib
run=Path(CONFIG['run']);control=Path(CONFIG['control'])
identity=json.loads((control/'CONTROLLER-PROCESS.json').read_text())
stat=Path('/proc',str(identity['pid']),'stat');process={'identity':identity,'exists':stat.exists()}
if stat.exists():
 parts=stat.read_text().rsplit(')',1)[1].split();process.update(state=parts[0],same_start=parts[19]==identity['start_ticks'],start_ticks=parts[19])
rows=[json.loads(s) for s in (run/'DISPATCH.jsonl').read_text().splitlines()] if (run/'DISPATCH.jsonl').exists() else []
submitted=[r for r in rows if r['event']=='submitted'];terminal=[r for r in rows if r['event']=='terminal'];ids=[r['job'] for r in submitted]
accounting=[]
if ids:
 p=subprocess.run(['sacct','-X','-n','-P','-j',','.join(ids),'--format=JobIDRaw,State,ExitCode,ElapsedRaw,AllocCPUS,AllocTRES,NodeList,TotalCPU,MaxRSS'],capture_output=True,text=True,timeout=30)
 assert p.returncode==0,p.stderr
 accounting=[line for line in p.stdout.splitlines() if line.split('|')[0] in ids]
hardware={};technical={}
for key in ('collect-fit-490','collect-fit-545'):
 for name,target in [('HARDWARE.json',hardware),('TECHNICAL.json',technical)]:
  path=run/key/name
  if path.exists():target[key]=json.loads(path.read_text())
stop=json.loads((run/'STOP.json').read_text()) if (run/'STOP.json').exists() else None
fault_logs={}
failed_ids=[r.split('|')[0] for r in accounting if r.split('|')[1].split()[0] not in ('PENDING','RUNNING','CONFIGURING','COMPLETING','COMPLETED')]
if stop or failed_ids:
 paths=[control/'controller.err']
 for r in submitted:
  if r['job'] in failed_ids or (stop and r==submitted[-1]):
   key=r['spec']['key'];job=r['job']
   paths += [run/key/'FAILURE.json',run/(key+'-stderr.log'),run/(key+'-'+job+'.err'),run/(key+'-SUPERVISOR-FAILURE.json')]
 for p in paths:
  if p.exists():
   raw=p.read_bytes();assert len(raw)<=131072
   fault_logs[str(p)]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'text':raw.decode(errors='replace')}
print(json.dumps({'unix':time.time(),'process':process,'submitted':submitted,'terminal':terminal,
 'accounting':accounting,'hardware':hardware,'technical':technical,'stop':stop,'technical_fault_logs':fault_logs,
 'unresolved':[r for r in rows if 'unresolved' in r['event']],
 'campaign_ledger_exists':(run/'CAMPAIGN-ATTEMPTS.jsonl').exists(),
 'scientific_tasks_accepted':len((run/'SCIENTIFIC-TASKS.jsonl').read_text().splitlines()) if (run/'SCIENTIFIC-TASKS.jsonl').exists() else 0,
 'controller_stdout_bytes':(control/'controller.out').stat().st_size,'controller_stderr_bytes':(control/'controller.err').stat().st_size,
 'technical_gate':json.loads((run/'TECHNICAL-TRANCHE-PASSED.json').read_text()) if (run/'TECHNICAL-TRANCHE-PASSED.json').exists() else None,
 'compute_complete_exists':(run/'COMPUTE-COMPLETE.json').exists(),'scientific_payloads_read':False}))
'''
if __name__=='__main__':
    assert len(sys.argv)==2 and all(ch.isalnum() or ch=='-' for ch in sys.argv[1])
    o.once(sys.argv[1],CODE)
