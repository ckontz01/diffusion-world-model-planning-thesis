"""Reused Windows resource primitive, not a historical study runner.
Derived from accepted AV0 bounded_run.py, sha256
06eb833878c9f30a0a2dc458de1c28e0dc5d5eb67b982caf9c575c42015fe4d0.
"""
import ctypes as C
from ctypes import wintypes as W
import os

def limits():
    if os.name != 'nt': raise RuntimeError('Windows job limits required')
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
    if not k.GetProcessAffinityMask(k.GetCurrentProcess(),C.byref(pm),C.byref(sm)): raise C.WinError()
    x=EXT();x.basic.flags=0x10|0x200
    x.basic.affinity=sum(1<<i for i in [i for i in range(64) if pm.value & (1<<i)][:4])
    x.job_memory=8*1024**3
    if not h or not k.SetInformationJobObject(h,9,C.byref(x),C.sizeof(x)): raise C.WinError()
    if not k.AssignProcessToJobObject(h,k.GetCurrentProcess()): raise C.WinError()
    return k,h,x
