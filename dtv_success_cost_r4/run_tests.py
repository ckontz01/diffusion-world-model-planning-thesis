"""One bounded artificial CPU suite; no scheduler, physics or research payload."""
import os
for k in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS'):os.environ[k]='4'
import ctypes
import json
import sys
import threading
import time
import unittest
from ctypes import wintypes
from pathlib import Path

started=time.monotonic();cpu=time.process_time()
k=ctypes.WinDLL('kernel32',use_last_error=True);k.GetCurrentProcess.restype=wintypes.HANDLE
k.GetProcessAffinityMask.argtypes=[wintypes.HANDLE,ctypes.POINTER(ctypes.c_size_t),ctypes.POINTER(ctypes.c_size_t)]
k.SetProcessAffinityMask.argtypes=[wintypes.HANDLE,ctypes.c_size_t]
handle=k.GetCurrentProcess();mask=ctypes.c_size_t();system=ctypes.c_size_t()
if not k.GetProcessAffinityMask(handle,ctypes.byref(mask),ctypes.byref(system)):raise ctypes.WinError(ctypes.get_last_error())
bits=[1<<i for i in range(ctypes.sizeof(mask)*8) if mask.value&(1<<i)][:4]
if not k.SetProcessAffinityMask(handle,ctypes.c_size_t(sum(bits))):raise ctypes.WinError(ctypes.get_last_error())
class Basic(ctypes.Structure):
    _fields_=[('process_time',ctypes.c_int64),('job_time',ctypes.c_int64),('flags',wintypes.DWORD),
              ('min_working',ctypes.c_size_t),('max_working',ctypes.c_size_t),('process_count',wintypes.DWORD),
              ('affinity',ctypes.c_size_t),('priority',wintypes.DWORD),('scheduling',wintypes.DWORD)]
class IO(ctypes.Structure):_fields_=[(x,ctypes.c_uint64) for x in ('readops','writeops','otherops','readbytes','writebytes','otherbytes')]
class Limits(ctypes.Structure):
    _fields_=[('basic',Basic),('io',IO),('process_memory',ctypes.c_size_t),('job_memory',ctypes.c_size_t),
              ('peak_process',ctypes.c_size_t),('peak_job',ctypes.c_size_t)]
k.CreateJobObjectW.restype=wintypes.HANDLE;k.CreateJobObjectW.argtypes=[ctypes.c_void_p,wintypes.LPCWSTR]
k.SetInformationJobObject.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
k.AssignProcessToJobObject.argtypes=[wintypes.HANDLE,wintypes.HANDLE]
job=k.CreateJobObjectW(None,None);limits=Limits();limits.basic.flags=0x200;limits.job_memory=8*1024**3
if not job or not k.SetInformationJobObject(job,9,ctypes.byref(limits),ctypes.sizeof(limits)) or not k.AssignProcessToJobObject(job,handle):
    raise ctypes.WinError(ctypes.get_last_error())
timer=threading.Timer(900,lambda:os._exit(124));timer.start()
from dtv_success_cost.common import write
from dtv_success_cost_r1 import test_recovery
from dtv_success_cost_r2 import test_recovery as r2_tests
from dtv_success_cost_r3 import test_recovery as r3_tests
from dtv_success_cost_r4 import test_recovery as r4_tests
classes=(test_recovery.Authentication,test_recovery.ClosedLoop,test_recovery.Control,test_recovery.Recovery,r2_tests.Recovery,r3_tests.Recovery,r4_tests.Recovery)
suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(c) for c in classes)
result=unittest.TextTestRunner(verbosity=2).run(suite)
timer.cancel()
receipt=dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),
             wall_seconds=time.monotonic()-started,process_cpu_seconds=time.process_time()-cpu,
             affinity_cpu_count=len(bits),job_memory_limit_bytes=8*1024**3,wall_limit_seconds=900,
             artificial=True,research_payloads=False,physics=False,gpu=False,slurm=False,
             original_scientific_files_edited=False,python=sys.version)
path=Path(sys.argv[1]);write(path,receipt);print(json.dumps(receipt))
raise SystemExit(0 if result.wasSuccessful() else 1)
