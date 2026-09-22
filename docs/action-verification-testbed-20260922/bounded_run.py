"""AV0 Windows-only bounded stdlib runner. All attempts retained, no auto retry."""
import ctypes as C
from ctypes import wintypes as W
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parent
LOG=ROOT/'EXECUTION-LOG.json'


def limits():
    if os.name!='nt':raise RuntimeError('Recorded runner requires Windows job limits')
    class BASIC(C.Structure):
        _fields_=[('process_time',C.c_int64),('job_time',C.c_int64),('flags',W.DWORD),
                  ('min_ws',C.c_size_t),('max_ws',C.c_size_t),('processes',W.DWORD),
                  ('affinity',C.c_size_t),('priority',W.DWORD),('scheduling',W.DWORD)]
    class IO(C.Structure):
        _fields_=[(n,C.c_uint64) for n in ('read_ops','write_ops','other_ops','read','write','other')]
    class EXT(C.Structure):
        _fields_=[('basic',BASIC),('io',IO),('process_memory',C.c_size_t),('job_memory',C.c_size_t),
                  ('peak_process',C.c_size_t),('peak_job',C.c_size_t)]
    k=C.WinDLL('kernel32',use_last_error=True)
    k.CreateJobObjectW.restype=W.HANDLE;k.CreateJobObjectW.argtypes=[C.c_void_p,W.LPCWSTR]
    k.GetCurrentProcess.restype=W.HANDLE
    k.SetInformationJobObject.argtypes=[W.HANDLE,C.c_int,C.c_void_p,W.DWORD]
    k.QueryInformationJobObject.argtypes=[W.HANDLE,C.c_int,C.c_void_p,W.DWORD,C.c_void_p]
    k.AssignProcessToJobObject.argtypes=[W.HANDLE,W.HANDLE]
    k.GetProcessAffinityMask.argtypes=[W.HANDLE,C.POINTER(C.c_size_t),C.POINTER(C.c_size_t)]
    h=k.CreateJobObjectW(None,None)
    pm,sm=C.c_size_t(),C.c_size_t()
    if not k.GetProcessAffinityMask(k.GetCurrentProcess(),C.byref(pm),C.byref(sm)):raise C.WinError()
    x=EXT();x.basic.flags=0x10|0x200
    x.basic.affinity=sum(1<<i for i in [i for i in range(64) if pm.value & (1<<i)][:4])
    x.job_memory=8*1024**3
    if not h or not k.SetInformationJobObject(h,9,C.byref(x),C.sizeof(x)):raise C.WinError()
    if not k.AssignProcessToJobObject(h,k.GetCurrentProcess()):raise C.WinError()
    return k,h,x


if __name__=='__main__':
    entries=json.loads(LOG.read_text()) if LOG.exists() else []
    if any(e.get('state')=='running' for e in entries):raise RuntimeError('Unreconciled prior attempt')
    remaining=14400-sum(e['wall_seconds'] for e in entries)
    if remaining<=0:raise RuntimeError('Cumulative ceiling exhausted')
    label,command=sys.argv[1],sys.argv[2:]
    k,h,usage=limits()
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
             NUMEXPR_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES='')
    start=time.monotonic()
    entry=dict(label=label,command=command,started_unix=time.time(),state='running',wall_seconds=0)
    entries.append(entry);LOG.write_text(json.dumps(entries,indent=2)+'\n')
    failure=None
    try:
        result=subprocess.run(command,cwd=ROOT,env=env,timeout=min(remaining,600),capture_output=True,
                              text=True,encoding='utf8',errors='replace')
        entry.update(returncode=result.returncode,stdout=result.stdout,stderr=result.stderr,state='finished')
    except subprocess.TimeoutExpired as e:
        entry.update(returncode=124,state='timeout',stdout=str(e.stdout),stderr=str(e.stderr))
    except Exception as e:
        entry.update(returncode=125,state='failed',stderr=repr(e))
    finally:
        k.QueryInformationJobObject(h,9,C.byref(usage),C.sizeof(usage),None)
        entry.update(wall_seconds=time.monotonic()-start,peak_job_memory_bytes=usage.peak_job,
                     affinity_mask=usage.basic.affinity,gpu_allocations=0,
                     package_bytes=sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file()))
        if entry['package_bytes']>1_000_000_000:entry.update(returncode=126,state='byte-cap-exceeded')
        LOG.write_text(json.dumps(entries,indent=2)+'\n')
    print(json.dumps(entry,indent=2));sys.exit(entry['returncode'])
