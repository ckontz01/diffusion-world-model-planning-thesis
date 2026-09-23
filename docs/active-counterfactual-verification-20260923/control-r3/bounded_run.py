"""R3 tests share the existing R2 two-hour cumulative preparation ceiling."""
import r3_core as common
import ctypes
import importlib.util
import os
import subprocess
import sys
import time

if __name__ == '__main__':
    root = common.ROOT
    path = root / 'ATTEMPTS.jsonl'
    publication = common.REPO / 'docs/active-counterfactual-verification-publication-20260923/continuation-r3'
    entries = [common.json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    starts = {e['label'] for e in entries if e['state'] == 'started'}
    finishes = {e['label'] for e in entries if e['state'] != 'started'}
    common.require(starts == finishes, 'Unreconciled scripted attempt')
    label, command = sys.argv[1], sys.argv[2:]
    common.require(label not in starts, 'Duplicate attempt label')
    prior=common.lines(root.parent/'control-r2/ATTEMPTS.jsonl')
    remaining = 7200 - sum(e.get('wall_seconds', 0) for e in entries+prior)
    common.require(remaining > 0, 'R2+R3 two-hour cumulative budget exhausted')
    def append(value):
        with path.open('ab') as f:
            f.write(common.canonical(value) + b'\n'); f.flush(); os.fsync(f.fileno())
    spec = importlib.util.spec_from_file_location('limits', common.BASE.parent / 'action-verification-testbed-20260922/bounded_run.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    kernel, handle, usage = mod.limits()
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
               NUMEXPR_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1', CUDA_VISIBLE_DEVICES='')
    append({'label': label, 'state': 'started', 'command': command, 'time': time.time()})
    start = time.monotonic()
    try:
        r = subprocess.run(command, cwd=root, env=env, timeout=min(remaining, 7200), capture_output=True, text=True, encoding='utf8', errors='replace')
        result = {'returncode': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr}
    except Exception as e:
        result = {'returncode': 125, 'error': repr(e)}
    kernel.QueryInformationJobObject(handle, 9, ctypes.byref(usage), ctypes.sizeof(usage), None)
    result.update(label=label, state='finished', wall_seconds=time.monotonic()-start,
                  peak_job_memory_bytes=usage.peak_job, affinity=usage.basic.affinity,
                  output_bytes=sum(p.stat().st_size for folder in (root,publication,root.parent/'control-r2',publication.parent/'continuation-r2') for p in folder.rglob('*') if p.is_file()), gpu_allocations=0)
    if result['output_bytes'] > 250_000_000: result['returncode'] = 126
    append(result)
    print(common.json.dumps(result, indent=2)); sys.exit(result['returncode'])
