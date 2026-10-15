"""Exclusive bounded preparation; all operations covered by one finite charge."""
import ctypes
import json
import os
import subprocess
import sys
import time
from .common import DOC, ROOT, write_new

def main():
    label, limit = sys.argv[1], int(sys.argv[2])
    if not label.isalnum() or not 1 <= limit <= 240: raise ValueError('exclusive finite operation')
    rows = [json.loads(p.read_text()) for p in DOC.glob('LOCAL-*.json') if not p.name.endswith('.started.json')]
    if sum(r['elapsed_seconds'] for r in rows) + limit > 1700:
        raise RuntimeError('leave 300 seconds for preliminary reads and publication within 2000 charge')
    target = DOC / ('LOCAL-' + label + '.json')
    start = DOC / ('LOCAL-' + label + '.started.json')
    if target.exists() or start.exists(): raise FileExistsError('never repeat ambiguous operation')
    from wm_diag0.windows_limits import limits
    kernel, handle, usage = limits()
    env = dict(os.environ, OMP_NUM_THREADS='4', OPENBLAS_NUM_THREADS='4', MKL_NUM_THREADS='4',
               NUMEXPR_NUM_THREADS='4', PYTHONDONTWRITEBYTECODE='1', CUDA_VISIBLE_DEVICES='')
    write_new(start, {'command': sys.argv[3:], 'timeout_seconds': limit})
    began = time.monotonic(); result = {'returncode': 125, 'status': 'FAILED'}
    try:
        p = subprocess.run(sys.argv[3:], cwd=ROOT, env=env, timeout=limit, capture_output=True,
                           text=True, encoding='utf8', errors='replace')
        result.update(returncode=p.returncode, status='FINISHED', stdout=p.stdout, stderr=p.stderr)
    except Exception as exc: result['error'] = repr(exc)
    finally:
        kernel.QueryInformationJobObject(handle, 9, ctypes.byref(usage), ctypes.sizeof(usage), None)
        result.update(elapsed_seconds=time.monotonic()-began, peak_job_memory_bytes=usage.peak_job,
                      affinity_mask=usage.basic.affinity, covered_by_full_2000_second_charge=True)
        write_new(target, result); print(json.dumps(result, indent=2))
    return result['returncode']

if __name__ == '__main__': sys.exit(main())
