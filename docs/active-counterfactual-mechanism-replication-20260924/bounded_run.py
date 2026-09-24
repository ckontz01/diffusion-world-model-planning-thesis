"""Append-only local preparation receipts; one hour/four CPUs/8GiB/250MB."""
import base
import ctypes, importlib.util, os, subprocess, sys, time

if __name__=='__main__':
    log=base.HERE/'ATTEMPTS.jsonl'
    entries=[base.json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
    starts={e['label'] for e in entries if e['state']=='started'}
    assert starts=={e['label'] for e in entries if e['state']=='finished'}, 'Unreconciled attempt'
    label=sys.argv[1]; assert label not in starts
    remaining=3600-sum(e.get('wall_seconds',0) for e in entries); assert remaining>0
    script=base.REPO/'docs/action-verification-testbed-20260922/bounded_run.py'
    spec=importlib.util.spec_from_file_location('accepted_limits',script)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    kernel,handle,usage=mod.limits()
    def append(row):
        with log.open('ab') as f:
            f.write((base.json.dumps(row,sort_keys=True,allow_nan=False)+'\n').encode()); f.flush(); os.fsync(f.fileno())
    append(dict(label=label,state='started',unix=time.time(),command=sys.argv[2:]))
    start=time.monotonic()
    try:
        p=subprocess.run(sys.argv[2:],cwd=base.HERE,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),
                         timeout=min(remaining,1800),capture_output=True,text=True,encoding='utf8',errors='replace')
        result=dict(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
    except Exception as e: result=dict(returncode=125,error=repr(e))
    kernel.QueryInformationJobObject(handle,9,ctypes.byref(usage),ctypes.sizeof(usage),None)
    result.update(label=label,state='finished',wall_seconds=time.monotonic()-start,
                  peak_job_memory_bytes=usage.peak_job,cpu_affinity_mask=usage.basic.affinity,
                  bytes=sum(p.stat().st_size for p in base.HERE.rglob('*') if p.is_file()),gpu_allocations=0)
    if result['bytes']>250_000_000: result['returncode']=126
    append(result); print(base.json.dumps(result,indent=2)); sys.exit(result['returncode'])
