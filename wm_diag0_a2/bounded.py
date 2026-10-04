"""Exclusive A2 attempts sharing the original cumulative preparation ledger."""
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / 'docs/world-model-diagnostic-a2-20261004'
OLD = ROOT / 'docs/world-model-diagnostic-20261004/test-receipts'

def main():
    label = sys.argv[1]
    if not label.replace('-', '').isalnum(): raise ValueError('Exclusive label')
    receipts = DOC / 'test-receipts'
    receipts.mkdir(parents=True, exist_ok=True)
    if list(receipts.glob(label + '.*')): raise FileExistsError(label)
    ledgers = (OLD, receipts)
    if any(list(d.glob('*.running.json')) for d in ledgers): raise RuntimeError('Unreconciled attempt')
    prior = [json.loads(p.read_text()) for d in ledgers for p in d.glob('*.json')]
    spent = sum(r['wall_seconds'] for r in prior)
    # Prior separately recorded native receipt-copy work, not in runner receipts.
    spent += 2.6799084
    reserve = 600
    if spent + reserve > 14400: raise RuntimeError('Cumulative full reservation')
    sys.path.insert(0, str(ROOT / 'wm_diag0'))
    from windows_limits import limits
    kernel, handle, usage = limits()
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
               MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1',
               PYTHONDONTWRITEBYTECODE='1', CUDA_VISIBLE_DEVICES='')
    entry = {'label': label, 'state': 'running', 'started_unix': time.time(),
             'wall_seconds': 0, 'reservation_seconds': reserve,
             'prior_cumulative_seconds': spent, 'command': sys.argv[2:],
             'domain': 'preparation_only', 'cpu_threads_cap': 4,
             'memory_cap_bytes': 8 * 1024**3, 'research_access': False}
    pending = receipts / (label + '.running.json')
    with pending.open('x') as f: json.dump(entry, f, indent=2)
    start = time.perf_counter()
    try:
        r = subprocess.run(sys.argv[2:], cwd=ROOT, env=env, capture_output=True,
                           text=True, encoding='utf8', errors='replace', timeout=reserve)
        entry.update(returncode=r.returncode, stdout=r.stdout, stderr=r.stderr, state='finished')
    except Exception as exc:
        entry.update(returncode=125, stderr=repr(exc), state='failed')
    finally:
        elapsed = time.perf_counter() - start
        kernel.QueryInformationJobObject(handle, 9, ctypes.byref(usage), ctypes.sizeof(usage), None)
        bases = (ROOT / 'wm_diag0', ROOT / 'wm_diag0_a2',
                 ROOT / 'docs/world-model-diagnostic-20261004', DOC)
        retained = sum(p.stat().st_size for d in bases for p in d.rglob('*') if p.is_file())
        code_metadata = sum(p.stat().st_size for d in bases for p in d.rglob('*')
                            if p.is_file() and '/artifacts/' not in p.as_posix())
        entry.update(wall_seconds=elapsed, cumulative_seconds=spent + elapsed,
                     peak_job_memory_bytes=usage.peak_job, affinity_mask=usage.basic.affinity,
                     retained_local_bytes=retained, code_metadata_bytes=code_metadata,
                     model_forward_passes=0, physics_steps=0, scheduler_allocations=0)
        if code_metadata > 1_000_000_000 or retained > 5 * 1024**3:
            entry.update(returncode=126, state='storage_cap_exceeded')
        with (receipts / (label + '.json')).open('x') as f: json.dump(entry, f, indent=2)
        pending.rename(receipts / (label + '.started'))
    print(json.dumps(entry, indent=2))
    return entry['returncode']

if __name__ == '__main__': sys.exit(main())
