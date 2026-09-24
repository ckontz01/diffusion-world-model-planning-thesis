"""Host supervisor bounds the entire container's output, not only Python output."""
import common as c
import argparse
import os
import signal
import subprocess
import sys
import threading
import time
from storage import LOG_PER_STREAM

def main():
    p=argparse.ArgumentParser();p.add_argument('--approval',required=True);p.add_argument('--run',required=True);p.add_argument('--task',required=True);a=p.parse_args()
    auth=c.Authorization(a.approval,a.run);spec=next(j for j in c.grid() if j['key']==a.task)
    b=auth.inputs;c.require(c.sha(b['container']['path'])==b['container']['sha256'],'Pinned container')
    runtime=b['runtime'];runtime=runtime['path'] if isinstance(runtime,dict) else runtime
    env=dict(PATH=runtime+'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1',PYTHONHASHSEED='0',
             SLURM_JOB_ID=os.environ['SLURM_JOB_ID'],SLURM_CPUS_PER_TASK='4',SLURM_JOB_NODELIST=os.environ.get('SLURM_JOB_NODELIST',''),
             CUDA_VISIBLE_DEVICES=os.environ.get('CUDA_VISIBLE_DEVICES','') if spec['gpu'] else '',CUBLAS_WORKSPACE_CONFIG=':4096:8',
             MUJOCO_GL='egl',SDL_VIDEODRIVER='dummy',OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',MKL_NUM_THREADS='4',NUMEXPR_NUM_THREADS='4',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
    cmd=['apptainer','exec','--cleanenv']+(['--nv'] if spec['gpu'] else [])+['--bind',c.RESEARCH+':'+c.RESEARCH+':ro','--bind',str(auth.run)+':'+str(auth.run)+':rw',b['container']['path'],'env']
    cmd += [k+'='+v for k,v in env.items()]+[runtime+'/bin/python','-B',str(c.ROOT/'worker.py'),'--approval',a.approval,'--run',a.run,'--task',a.task]
    failures=[];child=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    def stop():
        if child.poll() is None:os.killpg(child.pid,signal.SIGTERM)
    def capture(stream,label):
        total=0
        try:
            with (auth.run/'logs'/(a.task+'.'+label)).open('xb') as f:
                while True:
                    block=stream.read(4096)
                    if not block:break
                    remaining=max(0,LOG_PER_STREAM-total);f.write(block[:remaining]);f.flush();total+=len(block)
                    if total>LOG_PER_STREAM:
                        failures.append('recorded log overflow '+label);stop();break
        except BaseException as e:
            failures.append('log preservation failure '+label+': '+repr(e));stop()
    threads=[threading.Thread(target=capture,args=(child.stdout,'out')),threading.Thread(target=capture,args=(child.stderr,'err'))]
    for t in threads:t.start()
    try: code=child.wait(timeout=spec['seconds']-10)
    except subprocess.TimeoutExpired:
        os.killpg(child.pid,signal.SIGKILL);code=child.wait();failures.append('hard supervisor deadline')
    for t in threads:t.join(timeout=2)
    if any(t.is_alive() for t in threads):failures.append('stream drain timeout')
    if failures:c.write(auth.run/'logs'/(a.task+'.SUPERVISOR-FAILURE.json'),dict(errors=failures,no_retry=True));return 1
    return code
if __name__=='__main__':
    try:sys.exit(main())
    except Exception as e:sys.stderr.write(str(e)[:512]);sys.exit(1)
