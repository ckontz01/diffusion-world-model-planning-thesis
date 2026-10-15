"""Finite native-Windows preparation runner; never imports a model framework."""
import ctypes
import json
import os
import subprocess
import sys
import time
from wm_diag0_preflight_v1.common import DOC, ROOT, write_new

def main():
    label = sys.argv[1]
    if not label.isalnum(): raise ValueError('alphanumeric exclusive label')
    limit = int(sys.argv[2])
    if not 1 <= limit <= 240: raise ValueError('operation limit')
    dest = DOC / ('LOCAL-' + label + '.json')
    start_file = DOC / ('LOCAL-' + label + '.started.json')
    if dest.exists() or start_file.exists(): raise FileExistsError('no overwrite')
    used = sum(json.loads(p.read_text())['elapsed_seconds'] for p in DOC.glob('LOCAL-*.json') if not p.name.endswith('.started.json'))
    if used + limit > 1320: raise RuntimeError('local operations must leave 360s for initial reads/publication within 1680s charge')
    from wm_diag0.windows_limits import limits
    kernel, handle, usage = limits()
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
               NUMEXPR_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1', CUDA_VISIBLE_DEVICES='')
    write_new(start_file, dict(command=sys.argv[3:], timeout_seconds=limit))
    began = time.monotonic(); row = dict(status='FAILED', returncode=125)
    try:
        proc = subprocess.run(sys.argv[3:], cwd=ROOT, env=env, timeout=limit, capture_output=True, text=True, encoding='utf8', errors='replace')
        row.update(returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr, status='FINISHED')
    except Exception as exc: row['error'] = repr(exc)
    finally:
        kernel.QueryInformationJobObject(handle, 9, ctypes.byref(usage), ctypes.sizeof(usage), None)
        row.update(elapsed_seconds=time.monotonic()-began, peak_job_memory_bytes=usage.peak_job,
                   affinity_mask=usage.basic.affinity, covered_by_full_1680_second_charge=True)
        write_new(dest, row); print(json.dumps(row, indent=2))
    return row['returncode']

if __name__ == '__main__': sys.exit(main())
