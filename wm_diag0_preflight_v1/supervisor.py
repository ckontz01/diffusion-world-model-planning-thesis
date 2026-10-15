"""Python-3.6-compatible allocated-node supervisor; finite CPU task, no retries."""
import hashlib
import json
import os
from pathlib import Path
import selectors
import resource
import signal
import subprocess
import sys
import time

def sha(path):
    h=hashlib.sha256()
    with open(str(path),'rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()

def write(path,row):
    raw=json.dumps(row,sort_keys=True,indent=2).encode()
    if len(raw)>10000: raise ValueError('control receipt bound')
    with open(str(path),'xb') as f: f.write(raw)

def main():
    began=time.monotonic(); root=Path(sys.argv[1]); expected=sys.argv[2]
    resource.setrlimit(resource.RLIMIT_FSIZE,(20000,resource.getrlimit(resource.RLIMIT_FSIZE)[1]))
    cpath=root/'source/CONTRACT.json'
    output=root/'output'; control=root/'controls'; log=root/'logs/worker.log'
    p=None; result={'status':'FAILED','returncode':125,'forwards_authorized':False}
    try:
        write(control/'ALLOCATION-STARTED.json',{'job_id':os.environ['SLURM_JOB_ID'],'hostname':os.uname().nodename,'contract_sha256':expected,'started_unix':time.time()})
        if sha(cpath)!=expected: raise ValueError('contract hash')
        c=json.loads(cpath.read_text()); d=json.loads((control/'DISPATCH.json').read_text())
        if d['job_id']!=os.environ['SLURM_JOB_ID'] or d['contract_sha256']!=expected: raise ValueError('dispatch binding')
        if int(os.environ.get('SLURM_CPUS_PER_TASK','0'))!=4: raise ValueError('four CPU allocation required')
        os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:4])
        if len(os.sched_getaffinity(0))>4: raise ValueError('CPU affinity is not enforced')
        for rel,row in c['staged_members'].items():
            path=root/'source'/rel
            if path.is_symlink() or path.stat().st_size!=row['bytes'] or sha(path)!=row['sha256']: raise ValueError('staged identity: '+rel)
        if sha(c['sif'])!=c['sif_sha256']: raise ValueError('runtime SIF identity')
        write(control/'INPUTS-VERIFIED.json',{'contract_sha256':expected,'sif_sha256':c['sif_sha256'],'members':len(c['staged_members'])})
        binds=[str(root/'source')+':'+str(root/'source')+':ro', str(control)+':'+str(control)+':ro',
               str(output)+':'+str(output)+':rw', str(root/'tmp')+':/tmp:rw',
               c['venv']+':'+c['venv']+':ro']
        for row in c['lewm'].values(): binds.append(row['path']+':'+row['path']+':ro')
        command=['apptainer','exec','--containall','--cleanenv','--no-home','--pwd',str(root/'source')]
        for b in binds: command += ['--bind',b]
        command += [c['sif'],c['venv']+'/bin/python','-B','-m','wm_diag0_preflight_v1.worker',str(cpath),expected,str(output)]
        env=dict(os.environ)
        for key in list(env):
            if key.startswith(('APPTAINERENV_','SINGULARITYENV_')): del env[key]
        for k,v in {'PYTHONPATH':str(root/'source'),'PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1',
                    'CUDA_VISIBLE_DEVICES':'','OMP_NUM_THREADS':'4','MKL_NUM_THREADS':'4','OPENBLAS_NUM_THREADS':'4',
                    'XFORMERS_DISABLED':'1','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1',
                    'SLURM_JOB_ID':d['job_id'],'HOME':'/tmp','MPLCONFIGDIR':'/tmp/mpl'}.items(): env['APPTAINERENV_'+k]=v
        p=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=env,start_new_session=True)
        sel=selectors.DefaultSelector(); sel.register(p.stdout,selectors.EVENT_READ)
        count=0; reason=None
        with open(str(log),'xb') as f:
            while True:
                for key,mask in sel.select(timeout=0.25):
                    raw=os.read(key.fd,8192)
                    if not raw: sel.unregister(key.fileobj); continue
                    keep=raw[:max(0,80000-count)]; f.write(keep); count+=len(keep)
                    if len(keep)!=len(raw): reason='log limit'
                if time.monotonic()-began>1140: reason='work wall limit'
                if sum(x.stat().st_size for x in output.rglob('*') if x.is_file())>980000: reason='output limit'
                if sum(x.stat().st_size for x in (root/'tmp').rglob('*') if x.is_file())>20000000: reason='temporary-storage limit'
                if reason:
                    os.killpg(p.pid,signal.SIGKILL); p.wait(); raise RuntimeError(reason)
                if p.poll() is not None and not sel.get_map(): break
        result['returncode']=p.returncode
        if p.returncode==0 and (output/'SUCCESS.json').is_file(): result['status']='CPU_PREFLIGHT_COMPLETED'
        else: raise RuntimeError('worker exited '+str(p.returncode))
    except BaseException as exc:
        result['error']=repr(exc)
        if p is not None and p.poll() is None: os.killpg(p.pid,signal.SIGKILL); p.wait()
    finally:
        result.update(elapsed_seconds=time.monotonic()-began,job_id=os.environ.get('SLURM_JOB_ID'),
                      output_bytes=sum(x.stat().st_size for x in output.rglob('*') if x.is_file()))
        write(control/'ALLOCATION-RESULT.json',result)
        print(json.dumps(result))
    return result['returncode'] if result['status']=='CPU_PREFLIGHT_COMPLETED' else 1

if __name__=='__main__': sys.exit(main())
