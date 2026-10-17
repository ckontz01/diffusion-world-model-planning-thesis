"""New finite native preparation runner; does not touch old study ledgers."""
import ctypes,json,math,msvcrt,os,queue,subprocess,sys,threading,time
from .common import ROOT,DOC,canonical,identity,write_new,prep_history
from wm_diag0_rc1_completion_v1.job import child_job

def main():
    began=time.monotonic();label=sys.argv[1];seconds=int(sys.argv[2]);command=sys.argv[3:]
    if not label.isalnum() or not command or not 5<=seconds<=300:raise ValueError('new exclusive bounded preparation argv')
    with (DOC/'operation.lock').open('a+b') as lock:
        if lock.tell()==0:lock.write(b'0');lock.flush()
        lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        start=DOC/('LOCAL-'+label+'.started.json');target=DOC/('LOCAL-'+label+'.json')
        if start.exists() or target.exists():raise FileExistsError('never repeat started/ambiguous operation')
        authority=json.loads((DOC/'AUTHORITY.json').read_text());used=authority['bootstrap_readonly_conservative_charge_seconds']+sum(r['conservative_charge_seconds'] for r in prep_history())
        if used+seconds>authority['prep_cumulative_scripted_wall_seconds']:raise ValueError('prospective complete preparation operation does not fit')
        from wm_diag0.windows_limits import limits
        parent_limits=limits();k,h,usage=child_job()
        write_new(start,{'authority':identity(DOC/'AUTHORITY.json'),'source':identity(__file__),'limit_seconds':seconds,'argv':command,'already_charged_preparation_seconds':used,'UTC_epoch':time.time()})
        proc=None;stop=threading.Event();q=queue.Queue(maxsize=2);parts=[];total=0
        result={'status':'FAILED','returncode':125,'automatic_retry':False}
        overall=began+seconds;deadline=overall-3
        watchdog=threading.Timer(max(.001,overall-time.monotonic()),lambda:os._exit(125));watchdog.daemon=True;watchdog.start()
        try:
            env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES='',NVIDIA_VISIBLE_DEVICES='void',OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',MKL_NUM_THREADS='4',NUMEXPR_NUM_THREADS='4')
            proc=subprocess.Popen([sys.executable,'-B','-m','wm_diag0_rc1_completion_v1.worker']+command,cwd=ROOT,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
            if not k.AssignProcessToJobObject(h,int(proc._handle)):raise ctypes.WinError()
            proc.stdin.write(b'GO\n');proc.stdin.close()
            def pump():
                while not stop.is_set():
                    b=proc.stdout.read(4096)
                    while not stop.is_set():
                        try:q.put(b,timeout=.05);break
                        except queue.Full:pass
                    if not b:return
            threading.Thread(target=pump,daemon=True).start()
            while True:
                if time.monotonic()>=deadline:raise TimeoutError('owned preparation deadline')
                try:b=q.get(timeout=.05)
                except queue.Empty:continue
                if not b:break
                total+=len(b)
                if total>150000:raise ValueError('bounded technical output; partial retained')
                parts.append(b)
            rc=proc.wait(timeout=max(.001,deadline-time.monotonic()));result.update(returncode=rc,status='FINISHED' if rc==0 else 'CHILD_NONZERO')
        except Exception as e:result['error']=repr(e)
        finally:
            stop.set();k.TerminateJobObject(h,125);k.QueryInformationJobObject(h,9,ctypes.byref(usage),ctypes.sizeof(usage),None);k.CloseHandle(h)
            if proc is not None:
                try:proc.wait(timeout=1)
                except subprocess.TimeoutExpired:result['owned_cleanup_incomplete']=True
            result.update(stdout=b''.join(parts).decode('utf8',errors='replace'),elapsed_seconds=time.monotonic()-began,peak_child_job_memory_bytes=usage.peak_job)
            result['conservative_charge_seconds']=math.ceil(result['elapsed_seconds'])+1
            write_new(target,result);print(json.dumps({k:v for k,v in result.items() if k!='stdout'}));watchdog.cancel()
        return 0 if result['status']=='FINISHED' else 125

if __name__=='__main__':sys.exit(main())
