"""Python3.6 allocation controller: exact DAG task, hard stops, no retry."""
import hashlib,json,os,selectors,signal,subprocess,sys,time
from pathlib import Path

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def write(path,row):
    with path.open('x') as f:json.dump(row,f,sort_keys=True)
def tree_bytes(root):return sum(p.stat().st_size for p in root.rglob('*') if p.is_file() and not p.is_symlink())

def main():
    root=Path(sys.argv[1]);expected=sys.argv[2];phase=sys.argv[3]
    index=int(os.environ.get('SLURM_ARRAY_TASK_ID','0'));job=os.environ['SLURM_JOB_ID'];parent=os.environ.get('SLURM_ARRAY_JOB_ID',job)
    cpath=root/'source/CONTRACT.json';c=json.loads(cpath.read_text());dag=json.loads((root/'controls/DAG-DISPATCH.json').read_text())
    if sha(cpath)!=expected or dag['contract_sha256']!=expected or dag['jobs'][phase]!=parent:raise ValueError('exact contract and dispatch')
    if phase not in ('readout','technical','grid','analysis'):raise ValueError('bounded frozen phase')
    if (phase in ('readout','technical') and not 0<=index<4) or (phase=='grid' and not 0<=index<124):raise ValueError('fixed array index')
    key=phase+'-'+str(index);task=root/'tasks'/key;task.mkdir(exist_ok=False)
    for n in ('controls','logs','tmp'):(task/n).mkdir()
    began=time.monotonic();result={'status':'FAILED','returncode':125};proc=None
    allocation=300 if phase=='readout' else 3600
    work=allocation-60
    output_bound=140000000 if phase=='readout' else 40000000 if phase=='analysis' else 10000000 if (index if phase=='technical' else index//31)%2==0 else 60000000
    try:
        write(task/'controls/STARTED.json',{'job_id':job,'array_job_id':parent,'phase':phase,'index':index,'contract_sha256':expected,'hostname':os.uname().nodename,'time':time.time()})
        if (root/'controls/STOP.json').exists():raise RuntimeError('existing campaign STOP')
        if int(os.environ.get('SLURM_CPUS_PER_TASK','0'))!=4:raise ValueError('four CPU allocation')
        if phase!='analysis' and os.uname().nodename not in ('gpu09','gpu09.cluster'):raise ValueError('exact GPU node')
        os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:4])
        for name,row in c['staged_members'].items():
            p=root/'source'/name
            if p.is_symlink() or p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise ValueError('staged source identity')
        if sha(Path(c['sif']))!=c['sif_sha256']:raise ValueError('SIF identity')
        for name,row in c['renderer']['members'].items():
            p=Path(c['renderer_path'])/name
            if p.is_symlink() or p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise ValueError('renderer identity')
        for name,target in c['renderer']['aliases'].items():
            if os.readlink(str(Path(c['renderer_path'])/name))!=target:raise ValueError('renderer alias')
        env=dict(os.environ)
        for k in list(env):
            if k.startswith(('APPTAINERENV_','SINGULARITYENV_')):del env[k]
        settings={'PYTHONPATH':str(root/'source'),'PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1',
                  'LD_LIBRARY_PATH':'/renderer:/opt/conda/lib:/.singularity.d/libs','MUJOCO_GL':'osmesa','PYOPENGL_PLATFORM':'osmesa',
                  'LIBGL_ALWAYS_SOFTWARE':'1','GALLIUM_DRIVER':'llvmpipe','LP_NUM_THREADS':'4','MESA_SHADER_CACHE_DISABLE':'true',
                  'OMP_NUM_THREADS':'4','OPENBLAS_NUM_THREADS':'4','MKL_NUM_THREADS':'4','NUMEXPR_NUM_THREADS':'4',
                  'SDL_VIDEODRIVER':'dummy','PYGAME_HIDE_SUPPORT_PROMPT':'1','MPLCONFIGDIR':'/tmp/mpl','XDG_CACHE_HOME':'/tmp/cache',
                  'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','XFORMERS_DISABLED':'1','STABLEWM_HOME':'/tmp/stablewm'}
        settings['CUDA_VISIBLE_DEVICES']='' if phase=='analysis' else os.environ.get('CUDA_VISIBLE_DEVICES','')
        for k,v in settings.items():env['APPTAINERENV_'+k]=v
        binds=[str(root/'source')+':'+str(root/'source')+':ro',str(root/'controls')+':'+str(root/'controls')+':ro',
               str(root/'tasks')+':'+str(root/'tasks')+':ro',str(task)+':'+str(task)+':rw',str(task/'tmp')+':/tmp:rw',
               c['source_run']+':'+c['source_run']+':ro',c['prior_source']+':'+c['prior_source']+':ro',
               c['renderer_path']+':/renderer:ro',c['venv']+':'+c['venv']+':ro']
        for row in c['lewm'].values():binds.append(row['path']+':'+row['path']+':ro')
        prefix=['apptainer','exec','--containall','--cleanenv','--no-home','--pwd',str(root/'source')]
        if phase!='analysis':prefix.append('--nv')
        for bind in binds:prefix+=['--bind',bind]
        prefix+=[c['sif'],c['venv']+'/bin/python','-B']
        command=prefix+(['-m','wm_diag0_campaign_v4.analysis',str(cpath),expected,str(task)] if phase=='analysis' else
                        ['-m','wm_diag0_campaign_v4.worker',str(cpath),expected,phase,str(index),str(task)])
        def run(command,deadline,logpath):
            nonlocal proc
            proc=subprocess.Popen(command,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
            sel=selectors.DefaultSelector();sel.register(proc.stdout,selectors.EVENT_READ);count=0
            log_remaining=(80000 if phase=='analysis' else 900000)-tree_bytes(task/'logs')
            with logpath.open('xb') as f:
                while True:
                    reason=None
                    for k,mask in sel.select(.2):
                        raw=os.read(k.fd,8192)
                        if not raw:sel.unregister(k.fileobj);continue
                        keep=raw[:max(0,log_remaining-count)];f.write(keep);count+=len(keep)
                        if len(keep)!=len(raw):reason='worker log cap'
                    if time.monotonic()-began>deadline:reason='finite task wall bound'
                    # Combined output+retained temporary files fit the declared
                    # per-task artifact reservation, rather than extra slack.
                    if tree_bytes(task/'output')+tree_bytes(task/'tmp')>output_bound:reason='combined task artifact/temporary cap'
                    if reason:
                        os.killpg(proc.pid,signal.SIGKILL);proc.wait();raise RuntimeError(reason)
                    if proc.poll() is not None and not sel.get_map():break
            if proc.returncode:raise RuntimeError('subprocess exited '+str(proc.returncode))
        run(command,work,task/'logs/worker.log')
        if phase!='analysis':
            run(prefix+['-m','wm_diag0_campaign_v4.validate_task',str(cpath),phase,str(index),str(task)],allocation-5,task/'logs/accept.log')
        if not (task/'controls/ACCEPTED.json').exists():raise ValueError('independent acceptance missing')
        result.update(status='ACCEPTED',returncode=0,acceptance_sha256=sha(task/'controls/ACCEPTED.json'))
    except BaseException as exc:
        result['error']=repr(exc)
        if proc is not None and proc.poll() is None:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
    finally:
        result.update(job_id=job,array_job_id=parent,phase=phase,index=index,elapsed_seconds=time.monotonic()-began,output_bytes=tree_bytes(task/'output'),temporary_bytes=tree_bytes(task/'tmp'))
        write(task/'controls/RESULT.json',result)
        if result['status']!='ACCEPTED':
            try:write(root/'controls/STOP.json',{'phase':phase,'index':index,'job_id':job,'error':result.get('error'),'failed_task':key})
            except FileExistsError:pass
            for target in dag['jobs'].values():
                p=subprocess.run(['scancel','--state=PENDING',target],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=5)
                write(task/'controls'/('CANCEL-PENDING-'+target+'.json'),{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
        print(json.dumps(result))
    return result['returncode']

if __name__=='__main__':sys.exit(main())
