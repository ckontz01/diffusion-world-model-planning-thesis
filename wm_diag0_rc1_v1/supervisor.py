"""One exact RC1 gate allocation, actual work120/preserve55/finalize5."""
import json,os,selectors,signal,subprocess,sys,time
from pathlib import Path
from .common import identity,write_new

def main():
    root=Path(sys.argv[1]);expected=sys.argv[2];cp=root/'source/RC1-CONTRACT.json';c=json.loads(cp.read_text())
    dispatch=json.loads((root/'controls/DISPATCH.json').read_text());job=os.environ['SLURM_JOB_ID']
    if identity(cp)['sha256']!=expected or dispatch['job_id']!=job or not c['rc1']['gate_authorized'] or c['gpu_stages_authorized']:raise ValueError('exact single gate dispatch')
    if (root/'controls/STOP.json').exists():raise ValueError('new run already stopped; no restart')
    task=root/'tasks/rc1-gate';task.mkdir(exist_ok=False)
    for n in ('output','controls','logs','tmp'):(task/n).mkdir()
    began=time.monotonic();proc=None;result={'status':'FAILED','job_id':job,'campaign_resumed':False}
    try:
        start_ticks=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]
        write_new(task/'controls/STARTED.json',{'PID':os.getpid(),'start_ticks':start_ticks,'job_id':job,'contract':expected,'time':time.time()})
        if int(os.environ.get('SLURM_CPUS_PER_TASK','0'))!=4 or os.uname().nodename not in ('gpu09','gpu09.cluster'):raise ValueError('exact node/CPU')
        os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:4])
        for n,x in c['staged_members'].items():
            if identity(root/'source'/n)!=x:raise ValueError('frozen source identity')
        if identity(Path(c['sif']))['sha256']!=c['sif_sha256']:raise ValueError('SIF identity')
        env={k:v for k,v in os.environ.items() if not k.startswith(('APPTAINERENV_','SINGULARITYENV_'))}
        settings={'PYTHONPATH':str(root/'source'),'PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1','XFORMERS_DISABLED':'1',
            'OMP_NUM_THREADS':'4','OPENBLAS_NUM_THREADS':'4','MKL_NUM_THREADS':'4','NUMEXPR_NUM_THREADS':'4',
            'XDG_CACHE_HOME':'/tmp/cache','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1',
            'CUDA_VISIBLE_DEVICES':os.environ.get('CUDA_VISIBLE_DEVICES','')}
        for k,v in settings.items():env['APPTAINERENV_'+k]=v
        paths={str(root/'source'),str(root/'controls'),c['recovery']['old_run'],c['rc1']['V3_run'],
               c['source_run'],c['prior_source'],c['venv'],*c['source_runs'].values()}
        command=['apptainer','exec','--nv','--containall','--cleanenv','--no-home','--pwd',str(root/'source')]
        for p in sorted(paths):command+=['--bind',p+':'+p+':ro']
        command+=['--bind',str(task)+':'+str(task)+':rw','--bind',str(task/'tmp')+':/tmp:rw',c['sif'],c['venv']+'/bin/python','-B','-m']
        size=0
        with (task/'logs/worker.log').open('xb') as log:
            for module,deadline in (('wm_diag0_rc1_v1.worker',120),('wm_diag0_rc1_v1.validate',175)):
                proc=subprocess.Popen(command+[module,str(root),expected],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
                sel=selectors.DefaultSelector();sel.register(proc.stdout,selectors.EVENT_READ)
                while True:
                    for key,mask in sel.select(.2):
                        raw=os.read(key.fd,8192)
                        if not raw:sel.unregister(key.fileobj);continue
                        if size+len(raw)>100000:raise RuntimeError('gate log limit')
                        log.write(raw);log.flush();size+=len(raw)
                    total=sum(p.stat().st_size for p in task.rglob('*') if p.is_file())
                    if total>26_100_000 or time.monotonic()-began>deadline:raise RuntimeError('gate time/output/tmp limit')
                    if proc.poll() is not None and not sel.get_map():break
                if proc.returncode:raise RuntimeError(module+' exited '+str(proc.returncode))
        result.update(json.loads((task/'controls/VALIDATED.json').read_text()))
        if not result['all_RC1_checks_passed']:write_new(root/'controls/STOP.json',{'reason':'RC1_GATE_FAILED','job_id':job,'campaign_resumed':False})
    except BaseException as exc:
        result['error']=repr(exc)
        try:write_new(root/'controls/STOP.json',{'reason':'TECHNICAL_RC1_FAILURE','job_id':job,'error':repr(exc),'campaign_resumed':False})
        except FileExistsError:pass
    finally:
        if proc is not None and proc.poll() is None:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
        result['elapsed_seconds']=time.monotonic()-began;write_new(task/'controls/RESULT.json',result);print(json.dumps(result))
    return 125 if result['status']=='FAILED' else 0

if __name__=='__main__':sys.exit(main())
