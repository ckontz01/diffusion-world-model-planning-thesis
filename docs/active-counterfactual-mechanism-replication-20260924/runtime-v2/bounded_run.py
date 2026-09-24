"""Correction only: two cumulative wall-hours, four threads, 8GiB, 250MB."""
import common as c
import ctypes
import importlib.util
import os
import subprocess
import sys
import time
if __name__=='__main__':
    log=c.ROOT/'ATTEMPTS.jsonl';rows=c.lines(log);label=sys.argv[1]
    c.require({r['label'] for r in rows if r['state']=='started'}=={r['label'] for r in rows if r['state']=='finished'},'Unreconciled test attempt')
    c.require(label not in {r['label'] for r in rows},'Exclusive attempt label')
    remaining=7200-sum(r.get('wall_seconds',0) for r in rows);c.require(remaining>0,'Correction local wall budget')
    path=c.REPO/'docs/action-verification-testbed-20260922/bounded_run.py'
    s=importlib.util.spec_from_file_location('limits',path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
    kernel,handle,usage=m.limits()
    c.append(log,dict(label=label,state='started',unix=time.time(),command=sys.argv[2:]))
    start=time.monotonic()
    try:
        r=subprocess.run(sys.argv[2:],cwd=c.ROOT,env=dict(os.environ,OPENBLAS_NUM_THREADS='4',OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',NUMEXPR_NUM_THREADS='4',CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1'),timeout=remaining,capture_output=True,text=True,encoding='utf8',errors='replace')
        result=dict(returncode=r.returncode,stdout=r.stdout,stderr=r.stderr)
    except Exception as e: result=dict(returncode=125,error=repr(e))
    kernel.QueryInformationJobObject(handle,9,ctypes.byref(usage),ctypes.sizeof(usage),None)
    result.update(label=label,state='finished',wall_seconds=time.monotonic()-start,peak_job_memory_bytes=usage.peak_job,affinity=usage.basic.affinity,bytes=c.bytes_in(c.ROOT),research_allocations=0)
    if result['bytes']>250_000_000:result['returncode']=126
    c.append(log,result);print(c.json.dumps(result,indent=2));sys.exit(result['returncode'])
