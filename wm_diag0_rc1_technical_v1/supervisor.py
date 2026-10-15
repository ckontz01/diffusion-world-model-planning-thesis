"""Three included native jobs, strictly serial3540work/55acceptance/5finalize."""
import json,os,selectors,signal,subprocess,sys,time
from pathlib import Path
from .common import identity,write_new

def size(p):return sum(x.stat().st_size for x in p.rglob('*') if x.is_file())

def main():
    root=Path(sys.argv[1]);expected=sys.argv[2];cp=root/'source/TECHNICAL-CONTRACT.json';c=json.loads(cp.read_text())
    d=json.loads((root/'controls/DISPATCH.json').read_text());parent=os.environ.get('SLURM_ARRAY_JOB_ID');job=os.environ['SLURM_JOB_ID'];setting=int(os.environ['SLURM_ARRAY_TASK_ID'])
    if identity(cp)['sha256']!=expected or d['array_job_id']!=parent or setting not in (1,2,3) or not c['rc1_technical']['three_settings_authorized'] or c['gpu_stages_authorized']:raise ValueError('exact three-setting dispatch')
    if (root/'controls/STOP.json').exists():raise ValueError('stopped; do not restart')
    task=root/'tasks'/('technical-'+str(setting));task.mkdir(exist_ok=False)
    for n in ('controls','logs','tmp'):(task/n).mkdir()
    began=time.monotonic();proc=None;result={'status':'FAILED','job_id':job,'array_job_id':parent,'setting':setting,'grid_dispatched':False}
    try:
        ticks=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]
        write_new(task/'controls/STARTED.json',{'PID':os.getpid(),'start_ticks':ticks,'job_id':job,'array_job_id':parent,'setting':setting,'contract':expected,'node':os.uname().nodename,'time':time.time()})
        if os.uname().nodename not in ('gpu09','gpu09.cluster') or int(os.environ.get('SLURM_CPUS_PER_TASK','0'))!=4:raise ValueError('exact CPU/node')
        os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:4])
        for n,x in c['staged_members'].items():
            if identity(root/'source'/n)!=x:raise ValueError('frozen staged source')
        if identity(c['sif'])['sha256']!=c['sif_sha256']:raise ValueError('SIF binding')
        for n,x in c['renderer']['members'].items():
            if identity(Path(c['renderer_path'])/n)!=x:raise ValueError('renderer binding')
        for n,target in c['renderer']['aliases'].items():
            if os.readlink(str(Path(c['renderer_path'])/n))!=target:raise ValueError('renderer alias')
        env={k:v for k,v in os.environ.items() if not k.startswith(('APPTAINERENV_','SINGULARITYENV_'))}
        settings={'PYTHONPATH':str(root/'source'),'PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1','XFORMERS_DISABLED':'1',
            'LD_LIBRARY_PATH':'/renderer:/opt/conda/lib:/.singularity.d/libs','MUJOCO_GL':'osmesa','PYOPENGL_PLATFORM':'osmesa','LIBGL_ALWAYS_SOFTWARE':'1','GALLIUM_DRIVER':'llvmpipe',
            'LP_NUM_THREADS':'4','MESA_SHADER_CACHE_DISABLE':'true','OMP_NUM_THREADS':'4','OPENBLAS_NUM_THREADS':'4','MKL_NUM_THREADS':'4','NUMEXPR_NUM_THREADS':'4',
            'SDL_VIDEODRIVER':'dummy','PYGAME_HIDE_SUPPORT_PROMPT':'1','MPLCONFIGDIR':'/tmp/mpl','XDG_CACHE_HOME':'/tmp/cache','STABLEWM_HOME':'/tmp/stablewm',
            'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','CUDA_VISIBLE_DEVICES':os.environ.get('CUDA_VISIBLE_DEVICES','')}
        for k,v in settings.items():env['APPTAINERENV_'+k]=v
        paths={str(root/'source'),str(root/'controls'),c['recovery']['old_run'],c['rc1_technical']['gate_run'],c['rc1_technical']['heads_run'],c['rc1']['V3_run'],c['source_run'],c['prior_source'],c['venv'],*c['source_runs'].values()}
        command=['apptainer','exec','--nv','--containall','--cleanenv','--no-home','--pwd',str(root/'source')]
        for p in sorted(paths):command+=['--bind',p+':'+p+':ro']
        for x in c['lewm'].values():command+=['--bind',x['path']+':'+x['path']+':ro']
        command+=['--bind',c['renderer_path']+':/renderer:ro','--bind',str(task)+':'+str(task)+':rw','--bind',str(task/'tmp')+':/tmp:rw',c['sif'],c['venv']+'/bin/python','-B','-m']
        cap=10000000 if setting==2 else 60000000;count=0
        with (task/'logs/worker.log').open('xb') as log:
            for module,deadline in (('wm_diag0_rc1_technical_v1.worker',3540),('wm_diag0_rc1_technical_v1.validate',3595)):
                proc=subprocess.Popen(command+[module,str(root),expected,str(setting)],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
                sel=selectors.DefaultSelector();sel.register(proc.stdout,selectors.EVENT_READ)
                while True:
                    for key,mask in sel.select(.2):
                        raw=os.read(key.fd,8192)
                        if not raw:sel.unregister(key.fileobj);continue
                        if count+len(raw)>1000000:raise RuntimeError('parent log bound')
                        log.write(raw);log.flush();count+=len(raw)
                    if time.monotonic()-began>deadline or size(task/'output')+size(task/'tmp')>cap:raise RuntimeError('parent hard work/output+tmp bound')
                    if proc.poll() is not None and not sel.get_map():break
                if proc.returncode:raise RuntimeError(module+' exit '+str(proc.returncode))
        a=task/'controls/ACCEPTED.json'
        if not json.loads(a.read_text())['accepted']:raise ValueError('independent acceptance absent')
        result.update(status='ACCEPTED',acceptance_identity=identity(a),output_seal=json.loads(a.read_text())['output_seal'])
    except BaseException as exc:
        result['error']=repr(exc)
        if proc is not None and proc.poll() is None:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
        try:write_new(root/'controls/STOP.json',{'reason':'RC1_NATIVE_SETTING_FAILURE','setting':setting,'job_id':job,'error':repr(exc),'no_retry':True})
        except FileExistsError:pass
        p=subprocess.run(['scancel','--state=PENDING',parent],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=5)
        write_new(task/'controls/CANCEL-PENDING.json',{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
    finally:
        if proc is not None and proc.poll() is None:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
        result['elapsed_seconds']=time.monotonic()-began;write_new(task/'controls/RESULT.json',result);print(json.dumps(result))
    return 0 if result['status']=='ACCEPTED' else 125

if __name__=='__main__':sys.exit(main())
