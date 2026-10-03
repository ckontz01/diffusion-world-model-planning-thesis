"""New-study-only Windows job limits, exclusive attempt receipts; never retries."""
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
DOC=ROOT/'docs/world-model-diagnostic-20261004'


def main():
    label=sys.argv[1]
    if not label.replace('-','').isalnum(): raise ValueError('Exclusive label')
    receipts=DOC/'test-receipts';receipts.mkdir(exist_ok=True)
    if list(receipts.glob(f'{label}.*')): raise RuntimeError('Attempt label already used')
    if list(receipts.glob('*.running.json')): raise RuntimeError('Unreconciled prior attempt')
    prior=[json.loads(p.read_text()) for p in receipts.glob('*.json')]
    spent=sum(r['wall_seconds'] for r in prior)
    reservation=600
    if spent+reservation>14400:raise RuntimeError('Full future reservation exceeds cumulative cap')
    from windows_limits import limits
    k,h,usage=limits()
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',
             PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES='')
    entry={'label':label,'state':'running','started_unix':time.time(),'wall_seconds':0,
           'reserved_seconds':reservation,'command':sys.argv[2:],'cpu_threads_cap':4,'memory_cap_bytes':8*1024**3,
           'prior_test_wall_seconds':spent,'domain':'artificial','research_access':False}
    pending=receipts/f'{label}.running.json'
    with pending.open('x') as f:json.dump(entry,f,indent=2)
    start=time.perf_counter()
    try:
        result=subprocess.run(sys.argv[2:],cwd=ROOT,env=env,timeout=reservation,capture_output=True,text=True,encoding='utf8',errors='replace')
        entry.update(returncode=result.returncode,stdout=result.stdout,stderr=result.stderr,state='finished')
    except subprocess.TimeoutExpired as exc:
        entry.update(returncode=124,state='timeout',stderr=repr(exc))
    except Exception as exc:
        entry.update(returncode=125,state='failed',stderr=repr(exc))
    finally:
        elapsed=time.perf_counter()-start
        k.QueryInformationJobObject(h,9,ctypes.byref(usage),ctypes.sizeof(usage),None)
        size=sum(p.stat().st_size for base in (DOC,ROOT/'wm_diag0') for p in base.rglob('*') if p.is_file())
        entry.update(wall_seconds=elapsed,cumulative_test_wall_seconds=spent+elapsed,peak_job_memory_bytes=usage.peak_job,
                     affinity_mask=usage.basic.affinity,new_package_bytes=size,gpu_allocations=0)
        if size>1_000_000_000:entry.update(returncode=126,state='output_cap_exceeded')
        with (receipts/f'{label}.json').open('x') as f:json.dump(entry,f,indent=2)
        # Preserve the original started receipt as provenance; it is completed by
        # renaming only this exact file, not deleting an audit record.
        pending.rename(receipts/f'{label}.started')
    print(json.dumps(entry,indent=2));return entry['returncode']

if __name__=='__main__':sys.exit(main())
