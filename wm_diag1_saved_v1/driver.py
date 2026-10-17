"""Exact one-job CPU-only native supervisor; fixed one saved-data child."""
import calendar,json,os,subprocess,sys,time,traceback,zipfile
from pathlib import Path
from .common import canonical,identity,json_bound,write_new,check_time

def allocation(dispatch):
    job=os.environ.get('SLURM_JOB_ID','')
    if job!=dispatch['job_id'] or os.environ.get('SLURM_CPUS_PER_TASK')!='4' or os.environ.get('SLURM_MEM_PER_NODE')!='8192':raise PermissionError('actual exact four-CPU/8GiB dispatch')
    if any(os.environ.get(k) for k in ('SLURM_JOB_GPUS','SLURM_STEP_GPUS','SLURM_ARRAY_JOB_ID','SLURM_ARRAY_TASK_ID','CUDA_VISIBLE_DEVICES')):raise PermissionError('no GPU/array in saved-only job')
    raw=subprocess.check_output(['scontrol','show','job','-o',job],universal_newlines=True,timeout=8,env=dict(os.environ,TZ='UTC'))
    fields=dict(x.split('=',1) for x in raw.split() if '=' in x)
    if fields.get('JobState')!='RUNNING' or fields.get('NumCPUs')!='4' or fields.get('NumTasks')!='1' or fields.get('TimeLimit')!='00:30:00' or fields.get('Partition')!='defq' or 'gpu' in fields.get('AllocTRES','').lower():raise PermissionError('independent exact CPU scheduler gate')
    affinity=os.sched_getaffinity(0)
    if not 0<len(affinity)<=4:raise PermissionError('CPU process placement')
    limits=[]
    for line in Path('/proc/self/cgroup').read_text().splitlines():
        _,controllers,path=line.split(':',2);p=None
        if 'memory' in controllers.split(','):p=Path('/sys/fs/cgroup/memory')/path.lstrip('/')/'memory.limit_in_bytes'
        elif not controllers:p=Path('/sys/fs/cgroup')/path.lstrip('/')/'memory.max'
        if p is not None and p.is_file() and p.read_text().strip().isdigit():limits.append(int(p.read_text().strip()))
    if not any(0<n<=8589934592 for n in limits):raise PermissionError('allocation-wide kernel 8GiB gate absent')
    import resource
    lo,hi=resource.getrlimit(resource.RLIMIT_AS);cap=min([8589934592]+[x for x in (lo,hi) if x!=resource.RLIM_INFINITY]);resource.setrlimit(resource.RLIMIT_AS,(cap,cap))
    start=calendar.timegm(time.strptime(fields['StartTime'],'%Y-%m-%dT%H:%M:%S'))
    return {'job_id':job,'started_epoch':start,'CPUs':sorted(affinity),'kernel_memory_limits':limits,'scheduler_record':raw}

def main():
    root=Path(sys.argv[1]);source=root/'source';expected=json.loads(sys.argv[2]);began=time.monotonic()
    dispatch=json.loads((root/'controls/DISPATCH.json').read_text());gate=allocation(dispatch)
    elapsed=time.time()-gate['started_epoch']
    if not 0<=elapsed<120:raise PermissionError('fresh single exact saved-data allocation')
    began-=elapsed;end=began+1800
    try:
        freeze=json_bound(source/'FREEZE.json',expected)
        if dispatch['freeze']!=expected or dispatch['source_commit']!=dispatch['full_remote_hash']:raise PermissionError('published frozen source before actual analysis')
        for name,want in freeze['members'].items():
            if identity(source/name)!=want:raise ValueError('frozen executed bytes '+name)
        write_new(root/'controls/ENTRY.json',{'status':'EXACT_PUBLISHED_CPU_ONLY_SAVED_DATA_ENTRY','allocation':gate,'freeze':expected})
        manifest=json_bound(source/'INPUT-MANIFEST.json',freeze['members']['INPUT-MANIFEST.json'])
        from wm_diag0_rc1_final_v1.cpu_process_v2 import run_child
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
        for name,value in {'OMP_NUM_THREADS':'4','OPENBLAS_NUM_THREADS':'4','MKL_NUM_THREADS':'4','NUMEXPR_NUM_THREADS':'4','PYTHONDONTWRITEBYTECODE':'1','CUDA_VISIBLE_DEVICES':'','NVIDIA_VISIBLE_DEVICES':'void'}.items():env['APPTAINERENV_'+name]=value
        for name in ('SLURM_JOB_ID','SLURM_CPUS_PER_TASK','SLURM_MEM_PER_NODE'):
            if name in os.environ:env['APPTAINERENV_'+name]=os.environ[name]
        args=['apptainer','exec','--containall','--cleanenv','--no-home','--pwd',str(source)]
        for p in (manifest['study_base'],manifest['venv'],str(source)):args+=['--bind',p+':'+p+':ro']
        args+=['--bind',str(root/'analysis')+':'+str(root/'analysis')+':rw','--bind',str(root/'analysis/tmp')+':/tmp:rw',manifest['sif'],manifest['venv']+'/bin/python','-B','-m','wm_diag1_saved_v1.worker_v2',str(source),canonical(expected).decode(),str(root/'analysis/output'),str(end-60)]
        child=run_child(args,env,root/'controls/analysis.log',[str(root/'analysis')],40000000,100000,end-60,end-35)
        if child['returncode']!=0:raise ValueError('single saved-data child failed; never automatically rerun')
        check_time(end-10);out=root/'analysis/output';seal=identity(out/'MEMBERS.json');members=json_bound(out/'MEMBERS.json',seal)
        for name,want in members.items():
            if name.startswith('/') or '..' in name.split('/') or identity(out/name)!=want:raise ValueError('exact closed compact output')
        resource_record=json_bound(out/'RESOURCE.json',members['RESOURCE.json'])
        if resource_record['rows']!=128 or not resource_record['no_model_or_simulator_modules_imported']:raise ValueError('complete saved-only pass receipt')
        proof={'status':'ONE_SAVED_DATA_CPU_PASS_CLOSED','job_id':dispatch['job_id'],'freeze':expected,'source_commit':dispatch['source_commit'],'actual_allocation':gate,
            'child':child,'output_seal':seal,'output_members':members,'resource':resource_record,'new_research_model_GPU_physics_calls':0,'automatic_retry':False}
        write_new(root/'controls/CPU-CLOSED.json',proof)
        paths={'output/'+name:out/name for name in members};paths['output/MEMBERS.json']=out/'MEMBERS.json'
        paths.update({'controls/'+p.name:p for p in (root/'controls').iterdir() if p.is_file()})
        package=root/'SAVED-DATA-PACKAGE.zip'
        if sum(p.stat().st_size for p in paths.values())>50000000:raise ValueError('compact closed data/control package bound')
        with package.open('xb') as stream:
            with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_STORED) as z:
                for name,p in sorted(paths.items()):z.write(str(p),name)
            stream.flush();os.fsync(stream.fileno())
        with zipfile.ZipFile(package) as z:
            if len(z.namelist())!=len(paths) or set(z.namelist())!=set(paths):raise ValueError('all compact package members')
            import hashlib
            for name,p in paths.items():
                b=z.read(name)
                if {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}!=identity(p):raise ValueError('compact package member readback')
        write_new(root/'READY.json',{'status':'ONE_SAVED_DATA_PASS_COMPLETE_CLOSED_PACKAGE_VERIFIED','job_id':dispatch['job_id'],'freeze':expected,
            'package_path':str(package),'package':identity(package),'member_map':{n:identity(p) for n,p in paths.items()},'output_seal':seal,'resource':resource_record})
        check_time(end);print(json.dumps({'status':'ONE_SAVED_DATA_PASS_COMPLETE_CLOSED_PACKAGE_VERIFIED','job_id':dispatch['job_id'],'rows':128}))
    except BaseException as e:
        if time.monotonic()<end:write_new(root/'controls/CPU-FAILED.json',{'error':repr(e),'traceback':traceback.format_exc()[-16000:],'no_automatic_retry':True})
        raise

if __name__=='__main__':main()
