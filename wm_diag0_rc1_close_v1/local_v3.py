"""Approved finite closure ledger; timeout cleanup only of a newly owned job."""
import base64,ctypes,json,msvcrt,os,queue,subprocess,sys,threading,time
from pathlib import Path
from .budget import ROOT,DOC,CAPS,raw_json,write_new,identity,reserve,owned_bytes,charge,AUTH
from wm_diag0_rc1_completion_v1.job import child_job

def main():
    began=time.monotonic();label,component= sys.argv[1:3];seconds=int(sys.argv[3]);command=sys.argv[4:]
    if not label.isalnum() or not command:raise ValueError('exclusive label and reviewed argv')
    # An OS advisory lock is released on process death. Its persistent byte is
    # not a receipt and is never deleted or treated as authority to retry.
    with (DOC/'operation.lock').open('a+b') as lock:
        if lock.tell()==0:lock.write(b'0');lock.flush()
        lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        started=DOC/('LOCAL-'+label+'.started.json');target=DOC/('LOCAL-'+label+'.json')
        if started.exists() or target.exists():raise FileExistsError('never repeat a started/ambiguous operation')
        a,v,old=reserve(component,seconds,time.time());before=owned_bytes()
        from wm_diag0.windows_limits import limits
        parent_kernel,parent_handle,parent_usage=limits()
        source={str(p.relative_to(ROOT)).replace('\\','/'):identity(p) for p in (ROOT/'wm_diag0_rc1_completion_v1').glob('*.py')}
        start_record={'component':component,'reserved_seconds':seconds,'command':command,'source':source,
                  'activation':identity(DOC/'ACTIVATION.json'),'authority':identity(DOC/'AUTHORITY.json'),'current_finalization_authority':identity(AUTH),'shared_component_envelope_not_additive_grants':True,
                  'full_future_component_remaining_before':{k:CAPS[k]-sum(charge(z) for z in old if z['component']==k) for k in CAPS},'UTC_epoch':time.time()}
        if component!='monitoring':
            start_record['executed_source_base64']={n:base64.b64encode((ROOT/n).read_bytes()).decode() for n in source}
        write_new(started,start_record)
        work_deadline=began+seconds-3;overall_deadline=began+seconds
        # Conservative full-reservation debit prevents receipt/cleanup time or
        # an ambiguous interrupted operation being reused as extra funding.
        result={'component':component,'reserved_seconds':seconds,'charged_seconds':seconds,'status':'FAILED','returncode':125,'automatic_retry':False}
        watchdog=threading.Timer(max(.001,overall_deadline-time.monotonic()),lambda:os._exit(125));watchdog.daemon=True;watchdog.start()
        k=h=usage=proc=None;stop=threading.Event();q=queue.Queue(maxsize=2);parts=[];n=0
        cap=16384 if component=='monitoring' else 262144
        def pump():
            try:
                while not stop.is_set():
                    b=proc.stdout.read(4096)
                    if not b:kind='EOF';b=b''
                    else:kind='DATA'
                    while not stop.is_set():
                        try:q.put((kind,b),timeout=.05);break
                        except queue.Full:pass
                    if kind=='EOF':return
            except BaseException:
                while not stop.is_set():
                    try:q.put(('ERROR',b''),timeout=.05);return
                    except queue.Full:pass
        try:
            if time.monotonic()>=work_deadline:raise TimeoutError('preflight consumes full reserved work window')
            k,h,usage=child_job()
            env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',MKL_NUM_THREADS='4',NUMEXPR_NUM_THREADS='4')
            proc=subprocess.Popen([sys.executable,'-B','-m','wm_diag0_rc1_completion_v1.worker']+command,cwd=ROOT,env=env,
                                  stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
            if not k.AssignProcessToJobObject(h,int(proc._handle)):raise ctypes.WinError()
            proc.stdin.write(b'GO\n');proc.stdin.close()
            thread=threading.Thread(target=pump,daemon=True);thread.start()
            while True:
                if time.monotonic()>=work_deadline:raise TimeoutError('owned operation work deadline; not proof of cluster failure')
                try:kind,b=q.get(timeout=min(.05,max(.001,work_deadline-time.monotonic())))
                except queue.Empty:continue
                if kind=='EOF':break
                if kind!='DATA':raise IOError('owned worker output pipe')
                if n+len(b)>cap:raise ValueError('hard captured-output cap; partial retained')
                parts.append(b);n+=len(b)
            rc=proc.wait(timeout=max(.001,work_deadline-time.monotonic()))
            result.update(returncode=rc,status='FINISHED' if rc==0 else 'CHILD_NONZERO')
        except Exception as exc:result['error']=repr(exc)
        finally:
            stop.set()
            if h is not None:
                # Contains only this operation's worker and descendants, never
                # a pre-existing WSL/SSH/research process. Close also kills it.
                k.TerminateJobObject(h,125)
                k.QueryInformationJobObject(h,9,ctypes.byref(usage),ctypes.sizeof(usage),None)
                result['peak_child_job_memory_bytes']=usage.peak_job;k.CloseHandle(h)
            if proc is not None:
                if proc.poll() is None:proc.kill()
                try:proc.wait(timeout=min(1,max(.001,overall_deadline-time.monotonic())))
                except subprocess.TimeoutExpired:result['owned_worker_cleanup_incomplete']=True
            result['stdout']=b''.join(parts).decode('utf8',errors='replace')
            result['elapsed_seconds']=time.monotonic()-began
            result['measured_elapsed_scope']='entry through owned-child cleanup, before receipt serialization; receipt finalization included in full reserved charge'
            if result['elapsed_seconds']>seconds:result['status']='RESERVATION_OVERRUN_STOP'
            if owned_bytes()-before+len(raw_json(result))> (65536 if component=='monitoring' else 1048576):
                result['status']='OPERATION_AUX_BOUND_OVERRUN_STOP'
            write_new(target,result,limit=1048576)
            print(json.dumps({k:v for k,v in result.items() if k!='stdout'},indent=2))
            watchdog.cancel()
        return result['returncode'] if result['status']=='FINISHED' else 125

if __name__=='__main__':sys.exit(main())
