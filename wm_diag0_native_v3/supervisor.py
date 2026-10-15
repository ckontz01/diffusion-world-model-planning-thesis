"""Python 3.6 allocation supervisor. One exact task, bounded output, no retry."""
import hashlib,json,os,selectors,signal,subprocess,sys,time
from pathlib import Path

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()
def write(p,r):
    with p.open('x') as f: json.dump(r,f,sort_keys=True)

def main():
    root=Path(sys.argv[1]); expected=sys.argv[2]; phase=sys.argv[3]
    began=time.monotonic(); p=None; result={'status':'FAILED','returncode':125}
    c=json.loads((root/'source/CONTRACT.json').read_text())
    d=json.loads((root/'controls'/('DISPATCH-'+phase+'.json')).read_text())
    job=os.environ['SLURM_JOB_ID']; index=int(os.environ.get('SLURM_ARRAY_TASK_ID','0'))
    parent=os.environ.get('SLURM_ARRAY_JOB_ID',job)
    if str(d['job_id'])!=parent or d['contract_sha256']!=expected or sha(root/'source/CONTRACT.json')!=expected: raise ValueError('exact dispatch/contract')
    if phase!='source': raise ValueError('this source supervisor cannot authorize GPU/analysis work')
    plan=json.loads((root/'source/ROOT-PLAN.json').read_text()); row=plan['roots'][index]
    key=row['task']+'-'+str(row['root_index']).zfill(3); task=root/'tasks'/key
    task.mkdir(exist_ok=False)
    for n in ('controls','logs','tmp'): (task/n).mkdir()
    try:
        if (root/'controls/STOP.json').exists(): raise RuntimeError('existing STOP: no new native attempt')
        if int(os.environ.get('SLURM_CPUS_PER_TASK','0'))!=4: raise ValueError('four CPU allocation')
        os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:4])
        write(task/'controls/STARTED.json',{'job_id':job,'array_id':parent,'index':index,'root_id':row['root_id'],'contract_sha256':expected,'start_unix':time.time()})
        for rel,x in c['staged_members'].items():
            f=root/'source'/rel
            if f.is_symlink() or f.stat().st_size!=x['bytes'] or sha(f)!=x['sha256']: raise ValueError('staged source identity')
        if sha(Path(c['sif']))!=c['sif_sha256']: raise ValueError('pinned SIF identity')
        for name,x in c['renderer']['members'].items():
            f=Path(c['renderer_path'])/name
            if f.is_symlink() or f.stat().st_size!=x['bytes'] or sha(f)!=x['sha256']:raise ValueError('renderer library identity')
        for name,target in c['renderer']['aliases'].items():
            if os.readlink(str(Path(c['renderer_path'])/name))!=target:raise ValueError('renderer alias identity')
        env=dict(os.environ)
        for k in list(env):
            if k.startswith(('APPTAINERENV_','SINGULARITYENV_')): del env[k]
        for k,v in {'PYTHONPATH':str(root/'source'),'PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1',
                    'OMP_NUM_THREADS':'4','OPENBLAS_NUM_THREADS':'4','MKL_NUM_THREADS':'4',
                    'CUDA_VISIBLE_DEVICES':'','MUJOCO_GL':'osmesa','PYOPENGL_PLATFORM':'osmesa','SDL_VIDEODRIVER':'dummy',
                    'LD_LIBRARY_PATH':'/renderer:/opt/conda/lib:/.singularity.d/libs','LIBGL_ALWAYS_SOFTWARE':'1','GALLIUM_DRIVER':'llvmpipe','LP_NUM_THREADS':'4',
                    'HOME':'/tmp','MPLCONFIGDIR':'/tmp/mpl','XDG_CACHE_HOME':'/tmp/cache','PYGAME_HIDE_SUPPORT_PROMPT':'1',
                    'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','XFORMERS_DISABLED':'1'}.items(): env['APPTAINERENV_'+k]=v
        binds=[str(root/'source')+':'+str(root/'source')+':ro',str(root/'controls')+':'+str(root/'controls')+':ro',
               str(task)+':'+str(task)+':rw',str(task/'tmp')+':/tmp:rw',c['venv']+':'+c['venv']+':ro']
        binds.append(c['renderer_path']+':/renderer:ro')
        cmd=['apptainer','exec','--containall','--cleanenv','--no-home','--pwd',str(root/'source')]
        for bind in binds: cmd+=['--bind',bind]
        cmd+=[c['sif'],c['venv']+'/bin/python','-B','-m','wm_diag0_native_v3.entry',str(root/'source/CONTRACT.json'),str(index),str(task)]
        p=subprocess.Popen(cmd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
        sel=selectors.DefaultSelector(); sel.register(p.stdout,selectors.EVENT_READ); count=0
        with (task/'logs/worker.log').open('xb') as f:
            while True:
                reason=None
                for keyfd,mask in sel.select(.1):
                    raw=os.read(keyfd.fd,8192)
                    if not raw: sel.unregister(keyfd.fileobj); continue
                    keep=raw[:max(0,80000-count)]; f.write(keep); count+=len(keep)
                    if len(keep)!=len(raw): reason='log bound'
                if time.monotonic()-began>45: reason='45-second source work bound'
                if sum(x.stat().st_size for x in task.rglob('*') if x.is_file())>32_000_000: reason='source+temporary bound'
                if reason:
                    os.killpg(p.pid,signal.SIGKILL); p.wait(); raise RuntimeError(reason)
                if p.poll() is not None and not sel.get_map(): break
        result['returncode']=p.returncode
        if p.returncode or not (task/'output/MEMBERS.json').is_file(): raise RuntimeError('native source failed')
        from wm_diag0_native_v3.source_accept import accept,ident
        result['acceptance']=accept(task/'output',ident(task/'output/MEMBERS.json'),row)
        result['status']='ACCEPTED' if result['acceptance']['available'] else 'UNAVAILABLE_WINDOW'
    except BaseException as exc:
        result['error']=repr(exc)
        if p is not None and p.poll() is None: os.killpg(p.pid,signal.SIGKILL); p.wait()
    finally:
        result.update(job_id=job,array_id=parent,index=index,root_id=row['root_id'],elapsed_seconds=time.monotonic()-began,
                      output_bytes=sum(x.stat().st_size for x in (task/'output').rglob('*') if x.is_file()))
        write(task/'controls/RESULT.json',result)
        if result['status']!='ACCEPTED':
            try: write(root/'controls/STOP.json',{'phase':'source','job_id':job,'root_id':row['root_id'],'reason':result['status'],'error':result.get('error')})
            except FileExistsError: pass
            cancel=subprocess.run(['scancel','--state=PENDING',parent],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=5)
            write(task/'controls/CANCEL-PENDING.json',{'returncode':cancel.returncode,'stdout':cancel.stdout,'stderr':cancel.stderr})
        print(json.dumps(result))
    return 0 if result['status']=='ACCEPTED' else 1

if __name__=='__main__': sys.exit(main())
