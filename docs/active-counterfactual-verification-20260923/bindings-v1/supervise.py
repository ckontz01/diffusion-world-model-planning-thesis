"""Bound stdout/stderr without discarding an unrecorded overflow or retrying."""
import common as c
import argparse
import os
import signal
import subprocess
import sys
import threading

LOG_CAP=65536


def main():
    p=argparse.ArgumentParser();p.add_argument('--approval',required=True);p.add_argument('--run',required=True);p.add_argument('--task',required=True);a=p.parse_args()
    auth=c.Authorization(a.approval,a.run)
    spec=next(j for j in c.grid() if j['key']==a.task)
    failures=[];lock=threading.Lock()
    child=subprocess.Popen([sys.executable,str(c.ROOT/'worker.py'),*sys.argv[1:]],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    def capture(stream,label):
        total=0
        try:
            with (auth.run/(a.task+'-'+label+'.log')).open('xb') as f:
                while True:
                    block=stream.read(4096)
                    if not block:break
                    if total+len(block)>LOG_CAP:
                        f.write(block[:LOG_CAP-total]);f.flush()
                        with lock:
                            failures.append('log overflow '+label)
                            if child.poll() is None:child.send_signal(signal.SIGTERM)
                        break
                    f.write(block);f.flush();total+=len(block)
        except BaseException as e:
            with lock:
                failures.append(repr(e))
                if child.poll() is None:child.send_signal(signal.SIGTERM)
    threads=[threading.Thread(target=capture,args=(child.stdout,'stdout')),threading.Thread(target=capture,args=(child.stderr,'stderr'))]
    for t in threads:t.start()
    try:code=child.wait(timeout=spec['seconds']-10)
    except subprocess.TimeoutExpired:
        child.kill();code=child.wait();failures.append('supervisor hard preservation deadline')
    for t in threads:t.join(timeout=5)
    if failures:
        c.write(auth.run/(a.task+'-SUPERVISOR-FAILURE.json'),{'failures':failures,'automatic_retry':False,'log_cap_bytes_each':LOG_CAP})
        return 1
    return code


if __name__=='__main__':sys.exit(main())
