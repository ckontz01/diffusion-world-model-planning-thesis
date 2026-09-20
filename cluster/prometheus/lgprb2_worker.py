"""Approved evaluation/compatibility/analysis only. No training dispatch path."""
import argparse,os,resource,signal,time,traceback
from pathlib import Path
import lgprb2_contract as c

def main():
    began=time.monotonic();cpu=time.process_time()
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--approval',type=Path,required=True)
    p.add_argument('--run',type=Path,required=True);p.add_argument('--task',required=True);a=p.parse_args()
    approval,specs=c.authorize(a.source,a.approval);spec=next(s for s in specs if s['name']==a.task)
    c.require(os.environ.get('SLURM_JOB_ID') and os.environ.get('SLURM_CPUS_PER_TASK')=='4','Actual allocation required')
    c.require(a.run.resolve().parent==c.ROOT/'experiments'/c.NAME and a.run.name=='run-'+approval['source_sha256'][:16],'New exclusive namespace')
    out=a.run/a.task;out.mkdir(exist_ok=False)
    existing=c.old.size(a.run);soft=spec['seconds']-(60)
    def guard():
        c.require(time.monotonic()-began<soft,'Worker preservation margin')
        current=c.old.size(out)
        c.require(current< (c.CAPS['main_job_bytes'] if spec['kind']!='analysis' else c.CAPS['analysis_bytes']),'Worker output cap')
        c.require(existing+current<c.CAPS['worker_bytes'],'New payload cap')
    def timeout(*_):raise TimeoutError('Preservation margin before allocation timeout')
    signal.signal(signal.SIGALRM,timeout);signal.alarm(soft)
    try:
        c.authenticate_inputs(a.source);guard()
        if spec['gpu']:
            import torch
            torch.set_num_threads(4);c.require(torch.cuda.is_available(),'GPU unavailable; no substitute')
            torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
            torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
            torch.use_deterministic_algorithms(True);torch.cuda.reset_peak_memory_stats()
            from lgprb2_evaluate import evaluate
            result=evaluate(a.source,out,spec,guard)
        else:
            c.require(not os.environ.get('CUDA_VISIBLE_DEVICES'),'CPU-only final analysis')
            from lgprb2_analysis import aggregate
            result=aggregate(a.source,a.run,specs)
        guard();c.write(out/'REPORT.json',result);guard()
        technical=dict(task=spec,complete=True,gpu_used=spec['gpu'],source_sha256=c.sha(a.source/c.MANIFEST),
            approval_sha256=c.sha(a.approval),wall_seconds=time.monotonic()-began,process_cpu_seconds=time.process_time()-cpu,
            peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        for key in ['episodes','models_unchanged','first_decisions','physical_actions','passed','setup_seconds','technical_checks']:
            if key in result:technical[key]=result[key]
        if spec['gpu']:technical['peak_gpu_bytes']=torch.cuda.max_memory_allocated()
        c.write(out/'TECHNICAL.json',technical);c.old.seal(out)
    except BaseException as e:
        signal.alarm(0);c.write(out/'FAILURE.json',dict(type=type(e).__name__,message=str(e),traceback=traceback.format_exc(),
            wall_seconds=time.monotonic()-began,process_cpu_seconds=time.process_time()-cpu,retry_authorized=False))
        c.old.seal(out);raise
    finally:signal.alarm(0)

if __name__=='__main__':main()
