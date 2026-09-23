"""Read-only scheduler/device-class metadata and exact failed-worker stderr."""
import operate as o
CODE=r'''
from pathlib import Path
import subprocess,time,hashlib
run=Path(CONFIG['run'])
commands=[['sacct','-X','-n','-P','-j','304189','--format=JobIDRaw,NodeList,ReqTRES,AllocTRES,State,ExitCode,ElapsedRaw'],
          ['scontrol','show','job','304189'],['sinfo','-p','a6000','-N','-h','-o','%N|%G|%f|%T']]
results=[]
for cmd in commands:
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
    results.append({'command':cmd,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
path=run/'collect-fit-490-stderr.log';b=path.read_bytes();assert len(b)<=65536
print(json.dumps({'unix':time.time(),'scheduler_metadata':results,'worker_stderr':{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'text':b.decode(errors='replace')},
 'allocated_device_queries':0,'new_jobs':0,'scientific_payload_reads':0}))
'''
if __name__=='__main__':o.once('GPU-FAULT-DIAGNOSTICS',CODE)
