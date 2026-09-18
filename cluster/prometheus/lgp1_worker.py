"""Approved job entry; no execution is possible with the published template."""
import argparse,json,os,resource,signal,time,traceback
from pathlib import Path
import lgp1_contract as c

def evaluate(source,run,out,spec,guard):
    import numpy as np
    import torch
    import stable_worldmodel as swm
    from independent_pusht_runtime import tensor_hash
    from pusht_fresh_initialization import register
    from e18_fresh_driver import FreshEpisode
    from lgp1_train import load_model
    from lgp1_runtime import FrozenBackend,Policy
    lock=c.read(source/c.DOC/'INPUTS.json')
    model,stats=load_model(run/f"fit-{spec['family']}-{spec['seed']}")
    frozen=c.read(run/'PRE-EVALUATION-FREEZE.json')
    for name,digest in frozen['models'].items(): c.require(c.sha(run/name/'model.pt')==digest,'All-six-model freeze')
    backend=FrozenBackend(lock);modules=[backend.lewm,backend.generator,model];before=tensor_hash(modules)
    ref=lock['references'][str(spec['reference'])]
    c.require(c.sha(ref['file'])==ref['sha256'],'Allowed reference bytes')
    with np.load(ref['file'],allow_pickle=False) as f: initial=f['initial_request'].copy();goals={h:f['states'][h].copy() for h in (75,150)}
    world=swm.World(register(),num_envs=1,image_shape=(224,224),max_episode_steps=300,correct_velocity_space=True,verbose=0)
    rows=[]
    def factory(h,s): return Policy(backend,model,stats,h,s,spec['reference'],guard)
    episode=FreshEpisode(world,factory)
    try:
        for h in (75,150):
            guard();events=[];physics_start=[0.];physics_seconds=[0.]
            def observe(event,**kw):
                if event=='action':
                    events.append(kw['action'].copy());physics_start[0]=time.monotonic()
                if event=='after_action':physics_seconds[0]+=time.monotonic()-physics_start[0]
            episode.observe=observe
            episode.start(dict(state=initial,goal_state=goals[h],proprio=initial[[0,1,5,6]]),horizon=h,budget=2*h,seed=spec['seed'])
            while episode.status=='running': episode.advance()
            policy=episode.policy;policy.finish()
            c.require(policy.terminal and not policy.history and not policy._action_buffer,'Episode ownership teardown')
            success=int(bool(np.asarray(world.terminateds).any()))
            rows.append(dict(reference=spec['reference'],family=spec['family'],seed=spec['seed'],horizon=h,
                success=success,steps=episode.steps,truncated=bool(np.asarray(world.truncateds).any()),
                physics_delivery_seconds=physics_seconds[0],
                failure=None,stages=policy.diagnostic_history))
            np.savez_compressed(out/f'actions-h{h}.npz',actions=np.concatenate(events,0))
            c.require(c.size(out)<=2*c.CAPS['episode_bytes'],'Episode artifact cap')
            if spec['kind']=='technical':
                conservative=(max(s['seconds'] for s in policy.diagnostic_history)+15*physics_seconds[0]/episode.steps)*1.5
                c.require(conservative*30<1100,'Measured complete-stage cost exceeds pair allocation')
    finally: world.close()
    c.require(tensor_hash(modules)==before,'Frozen modules changed')
    return dict(rows=rows,models_unchanged=True,model_tensor_sha256=before,episodes=2,
                freeze_sha256=c.sha(run/'PRE-EVALUATION-FREEZE.json'))

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--approval',type=Path,required=True)
    p.add_argument('--run',type=Path,required=True);p.add_argument('--task',required=True);a=p.parse_args()
    c.authorize(a.source,a.approval)
    specs=c.grid(c.read(a.source/c.DOC/'DATA-ROLES.json')['development_reference_indices'])
    spec=next(x for x in specs if x['name']==a.task)
    c.require(os.environ.get('SLURM_JOB_ID') and os.environ.get('SLURM_CPUS_PER_TASK')=='4','Allocation required')
    c.require(a.run.resolve().parent==c.ROOT/'experiments/local-goal-proposals-20260918','Run namespace')
    out=a.run/a.task;out.mkdir(exist_ok=False)
    began=time.monotonic();cpu=time.process_time();soft=spec['seconds']-120
    def guard():
        c.require(time.monotonic()-began<soft,'Worker allocation guard')
        c.require(c.size(a.run)<=c.CAPS['worker_bytes'],'Worker payload cap')
        c.require(c.size(out)<(2*c.CAPS['episode_bytes'] if spec['kind'] in ('technical','evaluation') else 2_000_000_000),'Job byte cap')
    def timeout(*_): raise TimeoutError('Preservation margin before Slurm timeout')
    signal.signal(signal.SIGALRM,timeout);signal.alarm(soft)
    try:
        c.authenticate_inputs(a.source,payload=False);guard()
        if spec['gpu']:
            import torch
            torch.set_num_threads(4)
            c.require(torch.cuda.is_available(),'GPU allocation unavailable')
            torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
            torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
            torch.use_deterministic_algorithms(True);torch.cuda.reset_peak_memory_stats()
        else:
            c.require(not os.environ.get('CUDA_VISIBLE_DEVICES'),'Analysis must have no GPU')
        if spec['kind']=='cache':
            from lgp1_data import build_cache
            from lgp1_runtime import FrozenBackend
            from lgp1_verify import cache
            result=build_cache(a.source,out,FrozenBackend(c.read(a.source/c.DOC/'INPUTS.json')),guard)
            result['independent_check']=cache(out)
        elif spec['kind']=='fit':
            from lgp1_train import train
            result=train(a.run/'cache',out,spec['family'],spec['seed'],guard)
        elif spec['kind'] in ('technical','evaluation'): result=evaluate(a.source,a.run,out,spec,guard)
        else:
            from lgp1_aggregate import aggregate
            result=aggregate(a.run,specs)
        guard();c.write(out/'REPORT.json',result)
        technical=dict(task=spec,complete=True,gpu_used=spec['gpu'],wall_seconds=time.monotonic()-began,
            process_cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            source_sha256=c.sha(a.source/'LGP1-SOURCE-MANIFEST.sha256'),approval_sha256=c.sha(a.approval))
        for key in ('updates','row_presentations','episodes','models_unchanged'):
            if key in result: technical[key]=result[key]
        if spec['gpu']: technical['peak_gpu_bytes']=torch.cuda.max_memory_allocated()
        c.write(out/'TECHNICAL.json',technical);c.seal(out)
    except BaseException as exc:
        signal.alarm(0)
        c.write(out/'FAILURE.json',dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc(),
             wall_seconds=time.monotonic()-began,process_cpu_seconds=time.process_time()-cpu,retry_authorized=False))
        c.seal(out);raise
    finally: signal.alarm(0)

if __name__=='__main__': main()
