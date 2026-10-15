"""One finite allocation; numerical failure is retained, never auto-retried."""
import json,os,selectors,signal,subprocess,sys,time
from pathlib import Path
from .common import identity,write_new

def main():
    root=Path(sys.argv[1]);expected=sys.argv[2];cp=root/'source/VALIDATION-CONTRACT.json';c=json.loads(cp.read_text())
    dispatch=json.loads((root/'controls/DISPATCH.json').read_text());job=os.environ['SLURM_JOB_ID']
    if identity(cp)['sha256']!=expected or dispatch['job_id']!=job or not c['numerical_validation_authorized'] or c['gpu_stages_authorized']:raise ValueError('exact validation allocation')
    task=root/'tasks/numerical-validation';task.mkdir(exist_ok=False)
    for n in ('output','controls','logs','tmp'):(task/n).mkdir()
    began=time.monotonic();proc=None;result={'status':'FAILED','job_id':job,'campaign_resumed':False}
    try:
        if int(os.environ.get('SLURM_CPUS_PER_TASK','0'))!=4 or os.uname().nodename not in ('gpu09','gpu09.cluster'):raise ValueError('exact allocated node/CPU')
        os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:4])
        for n,x in c['staged_members'].items():
            if identity(root/'source'/n)!=x:raise ValueError('frozen source identity')
        if identity(Path(c['sif']))['sha256']!=c['sif_sha256']:raise ValueError('existing runtime SIF')
        env={k:v for k,v in os.environ.items() if not k.startswith(('APPTAINERENV_','SINGULARITYENV_'))}
        settings={'PYTHONPATH':str(root/'source'),'PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1','XFORMERS_DISABLED':'1',
            'OMP_NUM_THREADS':'4','OPENBLAS_NUM_THREADS':'4','MKL_NUM_THREADS':'4','NUMEXPR_NUM_THREADS':'4',
            'HOME':'/tmp','XDG_CACHE_HOME':'/tmp/cache','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1',
            'CUDA_VISIBLE_DEVICES':os.environ.get('CUDA_VISIBLE_DEVICES','')}
        for k,v in settings.items():env['APPTAINERENV_'+k]=v
        paths={str(root/'source'),c['recovery']['old_run'],c['source_run'],c['prior_source'],c['venv'],*c['source_runs'].values()}
        command=['apptainer','exec','--nv','--containall','--cleanenv','--no-home','--pwd',str(root/'source')]
        for p in sorted(paths):command+=['--bind',p+':'+p+':ro']
        command+=['--bind',str(task)+':'+str(task)+':rw','--bind',str(task/'tmp')+':/tmp:rw',c['sif'],c['venv']+'/bin/python','-B','-m']
        size=0
        with (task/'logs/worker.log').open('xb') as log:
            for module in ('wm_diag0_numerical_v3.worker','wm_diag0_numerical_v3.validate'):
                proc=subprocess.Popen(command+[module,str(root),expected],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
                sel=selectors.DefaultSelector();sel.register(proc.stdout,selectors.EVENT_READ)
                while True:
                    for key,mask in sel.select(.2):
                        raw=os.read(key.fd,8192)
                        if not raw:sel.unregister(key.fileobj);continue
                        if size+len(raw)>100000:raise RuntimeError('validation log limit')
                        log.write(raw);log.flush();size+=len(raw)
                    total=sum(p.stat().st_size for p in task.rglob('*') if p.is_file())
                    if total>26_100_000 or time.monotonic()-began>120:raise RuntimeError('validation work time/storage limit')
                    if proc.poll() is not None and not sel.get_map():break
                if proc.returncode:raise RuntimeError(module+' exited '+str(proc.returncode))
        result.update(json.loads((task/'controls/VALIDATED.json').read_text()))
        if not result['all_numerical_checks_passed']:
            write_new(root/'controls/STOP.json',{'reason':'NUMERICAL_GATE_FAILED','job_id':job,'campaign_resumed':False})
    except BaseException as exc:
        result['error']=repr(exc)
        write_new(root/'controls/STOP.json',{'reason':'TECHNICAL_VALIDATION_FAILURE','job_id':job,'error':repr(exc),'campaign_resumed':False})
    finally:
        if proc is not None and proc.poll() is None:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
        result['elapsed_seconds']=time.monotonic()-began;write_new(task/'controls/RESULT.json',result);print(json.dumps(result))
    # A completed measurement with failed numerical checks is not a Slurm technical failure.
    return 125 if result['status']=='FAILED' else 0

if __name__=='__main__':sys.exit(main())
