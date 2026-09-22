"""Local documentation-only runner. Windows job: 8 GiB, 4 CPUs, 2 h cumulative.

Usage: python bounded_run.py LABEL COMMAND [ARGS...]
No installation, cluster access, science execution or archive operations.
"""
import ctypes as C
from ctypes import wintypes as W
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
LOG = ROOT / 'EXECUTION-LOG.json'
CAP = 250_000_000


def limits():
    if os.name != 'nt':
        raise RuntimeError('This recorded runner requires Windows job limits')
    class BASIC(C.Structure):
        _fields_ = [('process_time', C.c_int64), ('job_time', C.c_int64),
                    ('flags', W.DWORD), ('min_ws', C.c_size_t),
                    ('max_ws', C.c_size_t), ('processes', W.DWORD),
                    ('affinity', C.c_size_t), ('priority', W.DWORD),
                    ('scheduling', W.DWORD)]
    class IO(C.Structure):
        _fields_ = [(n, C.c_uint64) for n in
                    ('read_ops', 'write_ops', 'other_ops', 'read', 'write', 'other')]
    class EXTENDED(C.Structure):
        _fields_ = [('basic', BASIC), ('io', IO),
                    ('process_memory', C.c_size_t), ('job_memory', C.c_size_t),
                    ('peak_process', C.c_size_t), ('peak_job', C.c_size_t)]
    k = C.WinDLL('kernel32', use_last_error=True)
    k.CreateJobObjectW.restype = W.HANDLE
    k.CreateJobObjectW.argtypes = [C.c_void_p, W.LPCWSTR]
    k.GetCurrentProcess.restype = W.HANDLE
    k.SetInformationJobObject.argtypes = [W.HANDLE, C.c_int, C.c_void_p, W.DWORD]
    k.QueryInformationJobObject.argtypes = [W.HANDLE, C.c_int, C.c_void_p, W.DWORD, C.c_void_p]
    k.AssignProcessToJobObject.argtypes = [W.HANDLE, W.HANDLE]
    k.GetProcessAffinityMask.argtypes = [W.HANDLE, C.POINTER(C.c_size_t), C.POINTER(C.c_size_t)]
    h = k.CreateJobObjectW(None, None)
    process_mask, system_mask = C.c_size_t(), C.c_size_t()
    if not k.GetProcessAffinityMask(k.GetCurrentProcess(), C.byref(process_mask), C.byref(system_mask)):
        raise C.WinError(C.get_last_error())
    selected = [i for i in range(64) if process_mask.value & (1 << i)][:4]
    x = EXTENDED()
    x.basic.flags = 0x10 | 0x200  # affinity + aggregate job memory
    x.basic.affinity = sum(1 << i for i in selected)
    x.job_memory = 8 * 1024**3
    if not h or not k.SetInformationJobObject(h, 9, C.byref(x), C.sizeof(x)):
        raise C.WinError(C.get_last_error())
    if not k.AssignProcessToJobObject(h, k.GetCurrentProcess()):
        raise C.WinError(C.get_last_error())
    return k, h, x


if __name__ == '__main__':
    label, command = sys.argv[1], sys.argv[2:]
    entries = json.loads(LOG.read_text()) if LOG.exists() else []
    remaining = 7200 - sum(e['wall_seconds'] for e in entries)
    if remaining <= 0 or not command:
        raise RuntimeError('Local execution envelope exhausted or empty command')
    k, h, usage = limits()
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
               MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1', UV_THREADPOOL_SIZE='1',
               PYTHONDONTWRITEBYTECODE='1')
    start = time.monotonic()
    stamp = time.time()
    result = subprocess.run(command, env=env, timeout=min(remaining, 1800),
                            capture_output=True, text=True, encoding='utf-8', errors='replace')
    elapsed = time.monotonic() - start
    if not k.QueryInformationJobObject(h, 9, C.byref(usage), C.sizeof(usage), None):
        raise C.WinError(C.get_last_error())
    byte_count = sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())
    entry = dict(label=label, command=command, started_unix=stamp, wall_seconds=elapsed,
                 returncode=result.returncode, peak_job_memory_bytes=usage.peak_job,
                 affinity_mask=usage.basic.affinity, package_bytes=byte_count,
                 stdout=result.stdout, stderr=result.stderr)
    entries.append(entry)
    LOG.write_text(json.dumps(entries, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in entry.items() if k not in ('stdout','stderr')}))
    print(result.stdout)
    print(result.stderr, file=sys.stderr)
    if byte_count > CAP:
        raise RuntimeError('Documentation byte cap exceeded')
    sys.exit(result.returncode)
