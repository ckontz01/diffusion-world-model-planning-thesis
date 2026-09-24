"""Inside-container watchdog; no compute-node host Python dependency."""
import r1 as r
import argparse
import os
import signal
import subprocess
import sys
import threading

def bounded_child(command,logs,seconds,cap=4096):
    failures=[]
    child=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    def stop():
        if child.poll() is None:
            if os.name=='nt':child.terminate()
            else:os.killpg(child.pid,signal.SIGTERM)
    def capture(stream,path):
        total=0
        try:
            with path.open('xb') as f:
                while True:
                    block=stream.read(4096)
                    if not block:break
                    f.write(block[:max(0,cap-total)]);f.flush();total+=len(block)
                    if total>cap:failures.append('recorded log overflow '+path.name);stop();break
        except BaseException as e:failures.append('log preservation failure '+repr(e));stop()
    threads=[threading.Thread(target=capture,args=(stream,path)) for stream,path in zip((child.stdout,child.stderr),logs)]
    for t in threads:t.start()
    try:code=child.wait(timeout=seconds)
    except subprocess.TimeoutExpired:
        if os.name=='nt':child.kill()
        else:os.killpg(child.pid,signal.SIGKILL)
        code=child.wait();failures.append('hard supervisor deadline')
    for t in threads:t.join(timeout=2)
    if any(t.is_alive() for t in threads):failures.append('stream drain timeout')
    return (1 if failures else code),failures

def main():
    p=argparse.ArgumentParser();p.add_argument('--approval',required=True);p.add_argument('--run',required=True);p.add_argument('--task',required=True);a=p.parse_args()
    ctx=r.Context(os.environ['ACVM_R3_APPROVAL'])
    r.require(a.approval==str(ctx.worker_approval) and a.run==str(ctx.run),'Unchanged worker invocation')
    spec=next(j for j in ctx.jobs if j['key']==a.task)
    command=[sys.executable,'-B',str(r.ROOT/'worker_r1.py'),*sys.argv[1:]]
    code,failures=bounded_child(command,[r.slurm_log(ctx.run,a.task,'.'+s) for s in ('out','err')],spec['seconds']-10)
    if failures:r.write(ctx.run/'logs'/(a.task+'.r3.SUPERVISOR-FAILURE.json'),dict(errors=failures,no_retry=True))
    return code

if __name__=='__main__':
    try:sys.exit(main())
    except Exception as e:sys.stderr.write(str(e)[:512]);sys.exit(1)
