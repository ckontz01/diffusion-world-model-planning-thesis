"""Bound this lineage's local scripted operations; full 900s charge already posted."""
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / 'docs/world-model-diagnostic-a2-cluster-native-v1-20261015'


def main():
    label = sys.argv[1]
    if not label.isalnum(): raise ValueError('Exclusive alphanumeric label')
    dest = DOC / ('LOCAL-' + label + '.json')
    started = DOC / ('LOCAL-' + label + '.started.json')
    if dest.exists() or started.exists(): raise FileExistsError('No overwrite/retry')
    previous = [json.loads(p.read_text()) for p in DOC.glob('LOCAL-*.json') if not p.name.endswith('.started.json')]
    used = sum(r['elapsed_seconds'] for r in previous)
    limit = 240
    if used + limit > 600: raise RuntimeError('600s script allowance within full 900s package charge')
    from wm_diag0.windows_limits import limits
    kernel, handle, usage = limits()
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
               NUMEXPR_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1', CUDA_VISIBLE_DEVICES='')
    started.write_text(json.dumps({'command': sys.argv[2:], 'timeout_seconds': limit}), encoding='utf8')
    start = time.monotonic()
    row = {'status': 'FAILED'}
    try:
        r = subprocess.run(sys.argv[2:], cwd=ROOT, env=env, timeout=limit, capture_output=True, text=True, encoding='utf8', errors='replace')
        row.update(returncode=r.returncode, stdout=r.stdout, stderr=r.stderr, status='FINISHED')
    except Exception as exc:
        row.update(returncode=125, error=repr(exc))
    finally:
        kernel.QueryInformationJobObject(handle, 9, ctypes.byref(usage), ctypes.sizeof(usage), None)
        row.update(elapsed_seconds=time.monotonic()-start, peak_job_memory_bytes=usage.peak_job,
                   affinity_mask=usage.basic.affinity, covered_by_full_900_second_charge=True)
        with dest.open('x', encoding='utf8') as stream: json.dump(row, stream, indent=2)
        print(json.dumps(row, indent=2))
    return row['returncode']


if __name__ == '__main__': sys.exit(main())
