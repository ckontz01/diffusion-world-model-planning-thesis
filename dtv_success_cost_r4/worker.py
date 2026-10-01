"""New output adapter and EGL guard; original scientific GPU body retained."""
import argparse
import importlib
import os
import sys
import time
from dtv_success_cost.common import *
from dtv_success_cost.worker import authenticate
from dtv_success_cost.episode import run_episode,verify_episode
from dtv_success_cost_r4.common import recovery_gate,location
from dtv_success_cost_r2.render import validate_environment,validate_backend

def gpu_job(c,job,output):
    started=time.monotonic(); rows=[]
    def check():
        if time.monotonic()-float(os.environ.get('DTVEFF_START_MONOTONIC',started))>240:raise RuntimeError('finite work deadline')
        if sum(p.stat().st_size for p in output.rglob('*') if p.is_file())>job['output_bytes']:raise RuntimeError('complete worker cap')
    spec,authentication=authenticate(c,job,run_namespace(c));check()
    sys.path[:0]=[r['path'] for r in c['historical_sources']]+[str(REMOTE/'src/hi-lewm'),str(REMOTE/'src/hi-lewm/third_party/lewm'),str(ROOT/'cluster/prometheus')]
    import torch,numpy as np,stable_worldmodel as swm
    if __import__('importlib.metadata',fromlist=['version']).version('stable-worldmodel')!='0.0.6':raise RuntimeError('worldmodel runtime version changed')
    from dtv_efficiency.profile import hardware,world_prefix
    from dtv_success_cost_r4.native import read_source,Adapter
    hardware(torch)
    if os.environ.get('SLURM_JOB_NAME')!='dtveff1-'+job['id'] or os.environ.get('SLURMD_NODENAME')!='gpu09':raise RuntimeError('wrong task/node allocation')
    validate_backend(output);check()
    torch.set_num_threads(4);torch.set_num_interop_threads(1)
    torch.manual_seed(0);np.random.seed(0);torch.cuda.manual_seed_all(0)
    torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=True;torch.use_deterministic_algorithms(True)
    setup=time.perf_counter();models={};payloads={};module=importlib.import_module('acid_alternative.models')
    for arm,m in spec['models'].items():
        p=torch.load(m['checkpoint'],map_location='cpu',weights_only=False)
        if p['model_config']!=m['model_config'] or p['seed']!=job['scorer_seed'] or p['condition']!='true' or p['source_manifest_sha256']!=m['source_manifest_sha256']:raise RuntimeError('model routing changed')
        if any(v.is_floating_point() and v.dtype!=torch.float32 for v in p['state_dict'].values()):raise RuntimeError('stored precision changed')
        model=module.model_from_config(p['model_config']);model.load_state_dict(p['state_dict'],strict=True)
        if sum(v.numel() for v in model.parameters())!=m['parameter_count']:raise RuntimeError('model identity')
        models[arm]=model.cuda().eval().requires_grad_(False);payloads[arm]=p
    wm=swm.policy.AutoCostModel(world_prefix(spec['world_checkpoint']),cache_dir=REMOTE/'data/stablewm').float().cuda().eval().requires_grad_(False)
    if hasattr(wm,'interpolate_pos_encoding'):wm.interpolate_pos_encoding=True
    data,goal,pixels=read_source(c,job);torch.cuda.synchronize();setup=time.perf_counter()-setup;check()
    np.savez(output/'SOURCE-INPUT.npz',goal_pixels=pixels,**{'initial_'+k:v for k,v in data.items()},**{'target_'+k:v for k,v in goal.items()})
    with torch.inference_mode():
        for config in job['configs']:
            check();begin=time.perf_counter();adapter=Adapter(job,config,wm,models,payloads,spec,data,goal,pixels);torch.cuda.synchronize();environment_setup=time.perf_counter()-begin
            try:
                def journal(row):
                    with (output/(config+'.trace.jsonl')).open('a') as f:f.write(__import__('json').dumps(row,separators=(',',':'),allow_nan=False)+'\n');f.flush()
                episode=run_episode(adapter,config,check,journal=journal);episode['environment_construction_seconds']=environment_setup
                verified=verify_episode(episode)
                if rows and episode['initial']!=rows[0]['initial']:raise RuntimeError('arms not paired at exact initial condition')
                episode.update(source=job['source_index'],parent=c['cohort'][job['task']][job['source_index']]['parent_id'],scorer_seed=job['scorer_seed'],planner_seed=job['planner_seed'],technical=verified)
                rows.append(episode);write(output/(config+'.json'),episode)
                if job['task']=='pusht':
                    write(output/(config+'.initialization.json'),adapter.initialization_roundtrip)
            finally:adapter.close()
    write(output/'WORKER.json',dict(identity=job['id'],bindings_sha256=sha(DOC/'BINDINGS.json'),authentication_seconds=authentication,setup_model_input_seconds=setup,
                                  checkpoints={a:m['checkpoint_sha256'] for a,m in spec['models'].items()},world_checkpoint=spec['world_sha256'],
                                  source_input_sha256=sha(output/'SOURCE-INPUT.npz'),
                                  hostname=__import__('platform').node(),allocation_id=os.environ['SLURM_JOB_ID'],gpu=torch.cuda.get_device_name(),
                                  wall_seconds=time.monotonic()-started,automatic_retry=False,warmup_research_episodes=0))
    check();seal(output,job['id'])

def namespace(c,a):
    allowed={j['id'] for j in c['jobs'][27:]}
    if a.job not in allowed or a.output.resolve()!=(location(run_namespace(c))/'workers'/a.job).resolve():
        raise RuntimeError('exclusive R4 remaining-worker namespace required; carried successes closed')
    if a.child and (os.environ.get('DTVEFF_SUPERVISOR_PID')!=str(os.getppid()) or not a.output.is_dir() or any(a.output.iterdir())):
        raise RuntimeError('supervised empty R4 child namespace required; no overwrite/repeat')

def main():
    started=time.monotonic()
    p=argparse.ArgumentParser();p.add_argument('--approval',type=Path,required=True);p.add_argument('--recovery-approval',type=Path,required=True)
    p.add_argument('--job',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--child',action='store_true');a=p.parse_args()
    c,r=recovery_gate(a.recovery_approval)
    if a.approval.resolve()!=Path(r['worker_approval']).resolve():raise RuntimeError('original worker approval changed')
    namespace(c,a);validate_environment()
    if not a.child:
        if a.output.exists():raise RuntimeError('R4 output already exists; never repeat live/successful/ambiguous work')
        a.output.mkdir(parents=True)
        from dtv_efficiency_r1.deadline import supervise
        command=[sys.executable,'-m','dtv_success_cost_r4.worker','--child','--approval',str(a.approval),
                 '--recovery-approval',str(a.recovery_approval),'--job',a.job,'--output',str(a.output)]
        result=supervise(command,a.output,work_seconds=240,started=started)
        if result['status']!='child_exited' or result['child_exit_code']!=0:raise SystemExit(1)
        (a.output/'SEAL.json').rename(a.output/'CHILD-SEAL.json');seal(a.output,a.job);return
    try:gpu_job(c,next(j for j in c['jobs'] if j['id']==a.job),a.output)
    except Exception as e:
        if not (a.output/'FAILURE.json').exists():write(a.output/'FAILURE.json',dict(error=repr(e),automatic_retry=False))
        raise
if __name__=='__main__':main()
