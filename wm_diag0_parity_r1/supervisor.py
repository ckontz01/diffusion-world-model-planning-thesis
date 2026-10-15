"""One exact 180-second diagnostic allocation, never a campaign launcher."""
import hashlib,json,os,selectors,signal,subprocess,sys,time
from pathlib import Path

def ident(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return {'bytes':p.stat().st_size,'sha256':h.hexdigest()}

def write(p,x):
    with p.open('x') as f:json.dump(x,f,sort_keys=True)

def main():
    root=Path(sys.argv[1]);expected=sys.argv[2];cp=root/'source/PROBE-CONTRACT.json';c=json.loads(cp.read_text())
    d=json.loads((root/'controls/DISPATCH.json').read_text());job=os.environ['SLURM_JOB_ID']
    if ident(cp)['sha256']!=expected or d['job_id']!=job:raise ValueError('exact exclusive probe')
    task=root/'tasks/encoding-only';task.mkdir(exist_ok=False)
    for n in ('output','controls','logs','tmp'):(task/n).mkdir()
    began=time.monotonic();proc=None;result={'status':'FAILED','job_id':job}
    try:
        if int(os.environ.get('SLURM_CPUS_PER_TASK','0'))!=4 or os.uname().nodename not in ('gpu09','gpu09.cluster'):raise ValueError('exact CPU/GPU allocation')
        os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:4])
        for n,x in c['staged_members'].items():
            if ident(root/'source'/n)!=x:raise ValueError('source identity')
        if ident(Path(c['sif']))['sha256']!=c['sif_sha256']:raise ValueError('runtime SIF')
        env={k:v for k,v in os.environ.items() if not k.startswith(('APPTAINERENV_','SINGULARITYENV_'))}
        settings={'PYTHONPATH':str(root/'source'),'PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1','XFORMERS_DISABLED':'1',
                  'OMP_NUM_THREADS':'4','OPENBLAS_NUM_THREADS':'4','MKL_NUM_THREADS':'4','NUMEXPR_NUM_THREADS':'4',
                  'HOME':'/tmp','XDG_CACHE_HOME':'/tmp/cache','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1',
                  'CUDA_VISIBLE_DEVICES':os.environ.get('CUDA_VISIBLE_DEVICES','')}
        for k,v in settings.items():env['APPTAINERENV_'+k]=v
        old=Path(c['recovery']['old_run'])
        binds=[str(root/'source')+':'+str(root/'source')+':ro',str(root/'tasks')+':'+str(root/'tasks')+':ro',str(task)+':'+str(task)+':rw',str(task/'tmp')+':/tmp:rw',
               str(old)+':'+str(old)+':ro',c['source_run']+':'+c['source_run']+':ro',c['prior_source']+':'+c['prior_source']+':ro',c['venv']+':'+c['venv']+':ro']
        for supplier in sorted(set(c['source_runs'].values())):
            if supplier!=c['source_run']:binds.append(supplier+':'+supplier+':ro')
        command=['apptainer','exec','--nv','--containall','--cleanenv','--no-home','--pwd',str(root/'source')]
        for bind in binds:command+=['--bind',bind]
        command += [c['sif'],c['venv']+'/bin/python','-B','-m','wm_diag0_parity_r1.probe',str(root),expected]
        proc=subprocess.Popen(command,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
        sel=selectors.DefaultSelector();sel.register(proc.stdout,selectors.EVENT_READ);size=0
        with (task/'logs/worker.log').open('xb') as f:
            while True:
                for key,mask in sel.select(.2):
                    raw=os.read(key.fd,8192)
                    if not raw:sel.unregister(key.fileobj);continue
                    if size+len(raw)>100000:raise RuntimeError('bounded diagnostic log')
                    f.write(raw);size+=len(raw)
                total=sum(p.stat().st_size for p in task.rglob('*') if p.is_file())
                if total>1000000 or time.monotonic()-began>120:raise RuntimeError('diagnostic storage/time guard')
                if proc.poll() is not None and not sel.get_map():break
        if proc.returncode:raise RuntimeError('encoding probe exited '+str(proc.returncode))
        report=json.loads((task/'output/DIAGNOSIS.json').read_text())
        if report['actual_usage']!={'visual_encoder_calls':2,'encoded_frames':17,'action_encoder_calls':6,'proprio_encoder_calls':2,'predictor_calls':0,'cost_calls':0,'physics_resets':0,'controller_actions':0}:raise ValueError('exact bounded diagnostic workload')
        result.update(status='DIAGNOSED_NOT_CAMPAIGN_ACCEPTED',report=report,report_identity=ident(task/'output/DIAGNOSIS.json'))
    except BaseException as exc:result['error']=repr(exc)
    finally:
        if proc is not None and proc.poll() is None:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
        result['elapsed_seconds']=time.monotonic()-began;write(task/'controls/RESULT.json',result);print(json.dumps(result))
    return 0 if result['status']=='DIAGNOSED_NOT_CAMPAIGN_ACCEPTED' else 125

if __name__=='__main__':sys.exit(main())
