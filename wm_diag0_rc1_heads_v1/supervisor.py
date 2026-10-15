"""One serial two-element held-ID dispatch;1740work/55acceptance/5finalize."""
import json,os,selectors,signal,subprocess,sys,time
from pathlib import Path
from .common import identity,write_new

def size(root):return sum(p.stat().st_size for p in root.rglob('*') if p.is_file())

def main():
    root=Path(sys.argv[1]);expected=sys.argv[2];cp=root/'source/HEADS-CONTRACT.json';c=json.loads(cp.read_text())
    d=json.loads((root/'controls/DISPATCH.json').read_text());parent=os.environ.get('SLURM_ARRAY_JOB_ID');job=os.environ['SLURM_JOB_ID'];setting=int(os.environ['SLURM_ARRAY_TASK_ID'])
    if identity(cp)['sha256']!=expected or d['array_job_id']!=parent or setting not in (1,3) or not c['rc1_heads']['exact_two_fits_authorized'] or c['gpu_stages_authorized']:
        raise ValueError('exact bounded head dispatch')
    if (root/'controls/STOP.json').exists():raise ValueError('stopped no restart')
    task=root/'tasks'/('readout-'+str(setting));task.mkdir(exist_ok=False)
    for n in ('controls','logs','tmp'):(task/n).mkdir()
    began=time.monotonic();proc=None;result={'status':'FAILED','job_id':job,'array_job_id':parent,'setting':setting,'campaign_resumed':False}
    try:
        ticks=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]
        write_new(task/'controls/STARTED.json',{'PID':os.getpid(),'start_ticks':ticks,'job_id':job,'array_job_id':parent,'setting':setting,'contract':expected,'time':time.time()})
        if os.uname().nodename not in ('gpu09','gpu09.cluster') or int(os.environ.get('SLURM_CPUS_PER_TASK','0'))!=4:raise ValueError('exact node/CPU')
        os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:4])
        for n,x in c['staged_members'].items():
            if identity(root/'source'/n)!=x:raise ValueError('frozen source changed')
        if identity(c['sif'])['sha256']!=c['sif_sha256']:raise ValueError('runtime SIF changed')
        env={k:v for k,v in os.environ.items() if not k.startswith(('APPTAINERENV_','SINGULARITYENV_'))}
        settings={'PYTHONPATH':str(root/'source'),'PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1','XFORMERS_DISABLED':'1',
            'OMP_NUM_THREADS':'4','OPENBLAS_NUM_THREADS':'4','MKL_NUM_THREADS':'4','NUMEXPR_NUM_THREADS':'4','XDG_CACHE_HOME':'/tmp/cache',
            'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','CUDA_VISIBLE_DEVICES':os.environ.get('CUDA_VISIBLE_DEVICES','')}
        for k,v in settings.items():env['APPTAINERENV_'+k]=v
        paths={str(root/'source'),str(root/'controls'),c['recovery']['old_run'],c['rc1_heads']['gate_run'],c['source_run'],c['prior_source'],c['venv'],*c['source_runs'].values()}
        command=['apptainer','exec','--nv','--containall','--cleanenv','--no-home','--pwd',str(root/'source')]
        for p in sorted(paths):command+=['--bind',p+':'+p+':ro']
        command+=['--bind',str(task)+':'+str(task)+':rw','--bind',str(task/'tmp')+':/tmp:rw',c['sif'],c['venv']+'/bin/python','-B','-m']
        count=0
        with (task/'logs/worker.log').open('xb') as log:
            for module,deadline in (('wm_diag0_rc1_heads_v1.worker',1740),('wm_diag0_rc1_heads_v1.validate',1795)):
                proc=subprocess.Popen(command+[module,str(root),expected,str(setting)],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
                sel=selectors.DefaultSelector();sel.register(proc.stdout,selectors.EVENT_READ)
                while True:
                    for key,mask in sel.select(.2):
                        raw=os.read(key.fd,8192)
                        if not raw:sel.unregister(key.fileobj);continue
                        if count+len(raw)>100000:raise RuntimeError('head log bound')
                        log.write(raw);log.flush();count+=len(raw)
                    if time.monotonic()-began>deadline or size(task/'tmp')+size(task/'output')>139000000:raise RuntimeError('head hard time/output+tmp bound')
                    if proc.poll() is not None and not sel.get_map():break
                if proc.returncode:raise RuntimeError(module+' exit '+str(proc.returncode))
        a=task/'controls/ACCEPTED.json'
        if not json.loads(a.read_text())['accepted']:raise ValueError('missing independent acceptance')
        result.update(status='ACCEPTED',acceptance_identity=identity(a),output_seal=json.loads(a.read_text())['output_seal'])
    except BaseException as exc:
        result['error']=repr(exc)
        try:write_new(root/'controls/STOP.json',{'reason':'RC1_HEAD_TECHNICAL_FAILURE','setting':setting,'job_id':job,'error':repr(exc),'no_retry':True})
        except FileExistsError:pass
        p=subprocess.run(['scancel','--state=PENDING',parent],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=5)
        write_new(task/'controls/CANCEL-PENDING.json',{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
    finally:
        if proc is not None and proc.poll() is None:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
        result['elapsed_seconds']=time.monotonic()-began;write_new(task/'controls/RESULT.json',result);print(json.dumps(result))
    return 0 if result['status']=='ACCEPTED' else 125

if __name__=='__main__':sys.exit(main())
