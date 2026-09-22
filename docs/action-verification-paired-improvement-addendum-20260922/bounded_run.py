"""Addendum-only one-hour log; reuse AV0's read-only Windows job limiter."""
import ctypes as C
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parent
AV0=ROOT.parent/'action-verification-testbed-20260922'
LOG=ROOT/'EXECUTION-LOG.json'


if __name__=='__main__':
    sys.dont_write_bytecode=True
    spec=importlib.util.spec_from_file_location('av0_limit_readonly',AV0/'bounded_run.py')
    inherited=importlib.util.module_from_spec(spec);spec.loader.exec_module(inherited)
    entries=json.loads(LOG.read_text()) if LOG.exists() else []
    if any(e['state']=='running' for e in entries):raise RuntimeError('Unreconciled prior attempt')
    remaining=3600-sum(e['wall_seconds'] for e in entries)
    if remaining<=0:raise RuntimeError('One-hour ceiling exhausted')
    label,command=sys.argv[1],sys.argv[2:]
    k,h,usage=inherited.limits()
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
             NUMEXPR_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES='')
    start=time.monotonic()
    entry=dict(label=label,command=command,state='running',started_unix=time.time(),wall_seconds=0)
    entries.append(entry);LOG.write_text(json.dumps(entries,indent=2)+'\n')
    try:
        r=subprocess.run(command,cwd=ROOT,env=env,timeout=min(remaining,600),capture_output=True,
                         text=True,encoding='utf8',errors='replace')
        entry.update(state='finished',returncode=r.returncode,stdout=r.stdout,stderr=r.stderr)
    except subprocess.TimeoutExpired as e:
        entry.update(state='timeout',returncode=124,stdout=str(e.stdout),stderr=str(e.stderr))
    except Exception as e:
        entry.update(state='failed',returncode=125,stderr=repr(e))
    finally:
        k.QueryInformationJobObject(h,9,C.byref(usage),C.sizeof(usage),None)
        entry.update(wall_seconds=time.monotonic()-start,peak_job_memory_bytes=usage.peak_job,
                     affinity_mask=usage.basic.affinity,gpu_allocations=0,
                     package_bytes=sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file()))
        if entry['package_bytes']>250_000_000:entry.update(returncode=126,state='byte-cap-exceeded')
        LOG.write_text(json.dumps(entries,indent=2)+'\n')
    print(json.dumps(entry,indent=2));sys.exit(entry['returncode'])
