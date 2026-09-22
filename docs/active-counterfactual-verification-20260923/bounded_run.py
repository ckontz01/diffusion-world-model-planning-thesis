"""Bounded ACV0 preparation only. Every numerical attempt retained."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('accepted_limits', ROOT.parent/'action-verification-testbed-20260922/bounded_run.py')
limits_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(limits_module)

if __name__ == '__main__':
    log = ROOT/'EXECUTION-LOG.json'
    entries = json.loads(log.read_text()) if log.exists() else []
    if any(e['state'] == 'running' for e in entries): raise RuntimeError('Unreconciled attempt')
    remaining = 14400-sum(e['wall_seconds'] for e in entries)
    if remaining <= 0: raise RuntimeError('Cumulative cap')
    label, command = sys.argv[1], sys.argv[2:]
    if any(e['label'] == label for e in entries): raise RuntimeError('Duplicate attempt label')
    k, handle, usage = limits_module.limits()
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
               NUMEXPR_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1', CUDA_VISIBLE_DEVICES='')
    entry = dict(label=label, command=command, state='running', started_unix=time.time(), wall_seconds=0)
    entries.append(entry); log.write_text(json.dumps(entries, indent=2)+'\n')
    start = time.monotonic()
    try:
        run = subprocess.run(command, cwd=ROOT, env=env, timeout=min(remaining,1800), capture_output=True,
                             text=True, encoding='utf8', errors='replace')
        entry.update(returncode=run.returncode, stdout=run.stdout, stderr=run.stderr, state='finished')
    except subprocess.TimeoutExpired as exc:
        entry.update(returncode=124, stderr=str(exc), state='timeout')
    except Exception as exc:
        entry.update(returncode=125, stderr=repr(exc), state='failed')
    finally:
        import ctypes
        k.QueryInformationJobObject(handle,9,ctypes.byref(usage),ctypes.sizeof(usage),None)
        entry.update(wall_seconds=time.monotonic()-start, peak_job_memory_bytes=usage.peak_job,
                     affinity_mask=usage.basic.affinity, gpu_allocations=0,
                     package_bytes=sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file()))
        if entry['package_bytes'] > 1_000_000_000: entry.update(returncode=126, state='byte-cap-exceeded')
        log.write_text(json.dumps(entries,indent=2)+'\n')
    print(json.dumps(entry,indent=2)); sys.exit(entry['returncode'])
