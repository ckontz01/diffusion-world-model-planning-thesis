"""Four-thread/8GiB, one cumulative hour/250MB recovery validation envelope."""
import r1 as r
import ctypes
import importlib.util
import os
import subprocess
import sys
import time

log=r.ROOT/'TEST-ATTEMPTS.jsonl';rows=r.c.lines(log);label=sys.argv[1]
r.require(label not in {x['label'] for x in rows},'Exclusive attempt')
r.require({x['label'] for x in rows if x['state']=='started'}=={x['label'] for x in rows if x['state']=='finished'},'Prior test reconciled')
remaining=3600-sum(x.get('wall_seconds',0) for x in rows);r.require(remaining>0,'Finite recovery test envelope')
path=r.REPO/'docs/action-verification-testbed-20260922/bounded_run.py';spec=importlib.util.spec_from_file_location('limits',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
k,handle,usage=module.limits();r.c.append(log,dict(label=label,state='started',unix=time.time()))
start=time.monotonic()
try:
    p=subprocess.run([sys.executable,'-B',str(r.ROOT/'test_recovery.py')],cwd=r.ROOT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='4',OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',CUDA_VISIBLE_DEVICES=''),capture_output=True,text=True,timeout=remaining)
    result=dict(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
except Exception as e:result=dict(returncode=125,error=repr(e))
k.QueryInformationJobObject(handle,9,ctypes.byref(usage),ctypes.sizeof(usage),None)
result.update(label=label,state='finished',wall_seconds=time.monotonic()-start,peak_job_memory_bytes=usage.peak_job,affinity=usage.basic.affinity,artifact_bytes=r.c.bytes_in(r.ROOT),research_allocations=0)
if result['artifact_bytes']>250000000:result['returncode']=126
r.c.append(log,result);print(r.c.json.dumps(result));sys.exit(result['returncode'])
