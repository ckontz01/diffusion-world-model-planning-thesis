"""Exact failed-allocation technical evidence; never retries or reads outcomes."""
import operate as o

CODE=r'''
from pathlib import Path
import hashlib,subprocess,time
run=Path(CONFIG['run']);control=Path(CONFIG['control'])
rows=[json.loads(line) for line in (run/'DISPATCH.jsonl').read_text().splitlines()]
submitted=[r for r in rows if r['event']=='submitted'];terminal=[r for r in rows if r['event']=='terminal']
assert len(submitted)==len(terminal)==1 and submitted[0]['job']=='304189'
assert terminal[0]['state']=='FAILED' and terminal[0]['gpu_seconds']==23
q=subprocess.run(['squeue','-h','-j','304189','-o','%i|%j|%T'],capture_output=True,text=True,timeout=30)
a=subprocess.run(['sacct','-n','-P','-j','304189','--format=JobIDRaw,State,ExitCode,ElapsedRaw,AllocCPUS,AllocTRES,TotalCPU,MaxRSS'],capture_output=True,text=True,timeout=30)
assert q.returncode==a.returncode==0
paths=[control/'controller.err',run/'collect-fit-490-304189.err',run/'collect-fit-490-304189.out',
       run/'collect-fit-490'/'FAILURE.json',run/'collect-fit-490'/'worker.stderr',run/'collect-fit-490'/'worker.stdout']
logs={}
for path in paths:
    if path.exists():
        b=path.read_bytes();assert len(b)<100000
        logs[str(path)]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'text':b.decode(errors='replace')}
members=[{'path':str(p.relative_to(run)),'bytes':p.stat().st_size} for p in sorted(run.rglob('*')) if p.is_file()]
print(json.dumps({'unix':time.time(),'queue':q.stdout,'accounting':a.stdout,'rows':rows,'technical_failure_logs':logs,
 'members_metadata_only':members,'research_retry_count':0,'scientific_outputs_read':False}))
'''
if __name__=='__main__':o.once('FAULT-RECONCILIATION',CODE)
