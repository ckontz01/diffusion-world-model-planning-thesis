"""Real saved-input profiling entry point. Never run without new authorization.

The headline path delegates to authenticated historical scorers and released CEM.
Extra tracing, hashes and numerical equivalence checks are outside hot timers.
"""
import time
ENTRY_STARTED=time.monotonic()  # before auth, torch import or child startup
import argparse
import hashlib
import importlib
import json
import os
import platform
import statistics
import sys
import time
from pathlib import Path

from dtv_efficiency_r1.control import DOC, ORIGINAL_DOC, load_bindings, WORK_SECONDS
from dtv_efficiency_r1.deadline import EvidenceList, supervise
ARMS = ('plain', 'acid', 'forward', 'legacy_dtv', 'd1_sigma025')

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''): h.update(block)
    return h.hexdigest()

def gate(bindings, approval):
    if approval.get('execute') is not True or approval.get('research_execution_authorized') is not True:
        raise RuntimeError('DTV-EFF0 research execution disabled; explicit immutable execution instruction required')
    if approval.get('study') != 'DTV-EFF0' or approval.get('bindings_sha256') != sha(bindings):
        raise RuntimeError('approval/bindings mismatch')
    if not approval.get('authorization_record') or not approval.get('authorization_record_sha256') or not approval.get('package_manifest_sha256'):
        raise RuntimeError('missing explicit execution provenance/package freeze')
    authority=Path(approval['authorization_record'])
    if not authority.is_file() or sha(authority)!=approval['authorization_record_sha256']:
        raise RuntimeError('execution authority record missing/changed')
    record=json.loads(authority.read_text())
    if record.get('study')!='DTV-EFF0' or record.get('execution_authorized') is not True or record.get('bindings_sha256')!=sha(bindings) or record.get('package_manifest_sha256')!=approval['package_manifest_sha256']:
        raise RuntimeError('authority is not an explicit bound execution instruction')
    package=DOC/'PACKAGE-MANIFEST.json'
    if not package.is_file() or sha(package)!=approval['package_manifest_sha256']:
        raise RuntimeError('runtime package freeze differs')
    root=Path(__file__).resolve().parents[1]
    for row in json.loads(package.read_text())['files']:
        target=(root/row['path']).resolve()
        if not target.is_relative_to(root) or sha(target)!=row['sha256']:
            raise RuntimeError('prepared package member changed')

def order(block):
    return ARMS[block % 5:] + ARMS[:block % 5]

def quantile(xs, q):
    ys = sorted(xs); at = q * (len(ys)-1); low = int(at)
    return ys[low] + (ys[min(low+1,len(ys)-1)]-ys[low])*(at-low)

def summary(xs):
    import math
    if not xs or any(not math.isfinite(x) or x < 0 for x in xs): raise ValueError('invalid timing samples')
    return dict(n=len(xs),median=statistics.median(xs),q25=quantile(xs,.25),q75=quantile(xs,.75),p95=quantile(xs,.95),p99=quantile(xs,.99),minimum=min(xs),maximum=max(xs),units='milliseconds')

def hardware(torch):
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError('exactly one visible GPU required')
    if torch.cuda.get_device_name(0) != 'NVIDIA RTX 6000 Ada Generation':
        raise RuntimeError('wrong GPU class')
    if platform.node() not in ('gpu09', 'gpu09.cluster') or not os.environ.get('SLURM_JOB_ID'):
        raise RuntimeError('unapproved host or missing allocation identity')
    if torch.__version__ != '2.5.1+cu121' or platform.python_version() != '3.11.10':
        raise RuntimeError('runtime version differs from recovered historical runtime')

def world_prefix(checkpoint):
    """Bind the original loader to one exact file, never its newest-dir rule."""
    name=str(checkpoint)
    if not name.endswith('_object.ckpt'):raise RuntimeError('world-model loader filename binding differs')
    prefix=Path(name[:-len('_object.ckpt')])
    if prefix.exists():raise RuntimeError('world-model prefix collision; no directory/newest-checkpoint selection')
    return str(prefix)

def measured(torch, function):
    # Synchronize only at the complete-call/solve boundary, never inner kernels.
    torch.cuda.synchronize(); torch.cuda.reset_peak_memory_stats()
    start, end = torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)
    cpu = time.process_time(); wall = time.perf_counter(); start.record()
    result = function()
    end.record(); torch.cuda.synchronize()
    wall_ms=(time.perf_counter()-wall)*1000
    return result, dict(gpu_event_ms=float(start.elapsed_time(end)),synchronized_wall_ms=wall_ms,process_cpu_seconds=time.process_time()-cpu,cuda_peak_allocated_bytes=torch.cuda.max_memory_allocated(),cuda_peak_reserved_bytes=torch.cuda.max_memory_reserved())

def output_hash(torch, value):
    h=hashlib.sha256()
    def visit(v):
        if torch.is_tensor(v):
            a=v.detach().cpu().contiguous();h.update(str((str(a.dtype),tuple(a.shape))).encode());h.update(a.numpy().tobytes())
        elif isinstance(v,dict):
            for k in sorted(v):h.update(k.encode());visit(v[k])
        elif isinstance(v,(list,tuple)):
            for item in v:visit(item)
        else:h.update(repr(v).encode())
    visit(value);return h.hexdigest()

def reset(wrapper, raw_call=False):
    wrapper.call_count=1 if raw_call else 0
    if hasattr(wrapper,'diagnostic_history'):wrapper.diagnostic_history.clear()
    if hasattr(wrapper,'rollout_model'):reset(wrapper.rollout_model)

class Trace:
    """Untimed equivalence audit only; never the headline timed solver."""
    def __init__(self,base):self.base=base;self.rows=[]
    def get_cost(self,info,actions):
        costs=self.base.get_cost(info,actions)
        import torch
        self.rows.append((actions.clone(),costs.clone(),torch.topk(costs,30,dim=1,largest=False).indices.clone()))
        return costs

def equivalent(torch, first, second, rtol=1e-6, atol=1e-6):
    if torch.is_tensor(first):
        if not torch.allclose(first,second,rtol=rtol,atol=atol):raise RuntimeError('numerical equivalence failed; no tolerance relaxation')
    elif isinstance(first,dict):
        for k in first:equivalent(torch,first[k],second[k],rtol,atol)
    elif isinstance(first,(list,tuple)):
        if len(first)!=len(second):raise RuntimeError('trace length mismatch')
        for a,b in zip(first,second):equivalent(torch,a,b,rtol,atol)
    elif first!=second:raise RuntimeError('metadata equivalence failure')

def make_wrapper(core,d2,world,models,payloads,job,arm,device='cuda'):
    if arm=='d1_sigma025':
        p=payloads['diffusion']
        return core.SharedRolloutCostModel(world,arm='diffusion',scorer=models['diffusion'],latent_mean=p['latent_mean'],latent_std=p['latent_std'],noise_seed=p['seed'],diffusion_sigmas=(.25,),lambda_weight=.07,horizon=5,record_diagnostics=True).to(device)
    name={'plain':'b0','legacy_dtv':'dtv'}.get(arm,arm)
    key='diffusion' if arm=='legacy_dtv' else arm
    return d2.D2CostModel(world,arm=name,task=job['task'],planner_seed=job['planner_seed'],scorer=None if arm=='plain' else models[key],payload=None if arm=='plain' else payloads[key],horizon=5,record_diagnostics=True).to(device)

def raw(wrapper,trajectory,actions,goal):
    if hasattr(wrapper,'raw_cost'):return wrapper.raw_cost(trajectory,actions,goal)
    return wrapper._diffusion_cost(trajectory,actions)

def worker_main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--bindings',type=Path,default=DOC/'BINDINGS.json')
    parser.add_argument('--approval',type=Path,default=DOC/'EXECUTION-APPROVAL.json')
    parser.add_argument('--worker-child',action='store_true')
    parser.add_argument('--job',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    gate(args.bindings,json.loads(args.approval.read_text()))  # before imports/payload access
    if not args.worker_child or os.getppid()!=int(os.environ.get('DTVEFF_SUPERVISOR_PID','-1')):
        raise RuntimeError('owned deadline supervisor required')
    c=load_bindings(args.bindings);job=next(j for j in c['jobs'] if j['id']==args.job)
    if not args.output.is_dir() or set(p.name for p in args.output.iterdir())!={'SUPERVISOR-STARTED.json'}:
        raise RuntimeError('exclusive supervised output required')
    began=float(os.environ['DTVEFF_START_MONOTONIC'])
    records=EvidenceList(args.output/'RECORDS.jsonl');audit=EvidenceList(args.output/'EQUIVALENCE.jsonl')
    def budget():
        if time.monotonic()-began>WORK_SECONDS:raise RuntimeError('soft worker ceiling reached; preserve without retry')
        logs=sum(p.stat().st_size for p in (args.output.parent/(job['id']+'.out'),args.output.parent/(job['id']+'.err')) if p.exists())
        if logs>2000000:raise RuntimeError('operational log ceiling reached; preserve without retry')
    try:
        model_runtime=json.loads((ORIGINAL_DOC/'FINAL-RECOVERY.json').read_text())['model_runtime_sources']
        for row in c['runtime']+model_runtime:
            if sha(row['path'])!=row['sha256']:raise RuntimeError('installed runtime source changed')
        remote_root=Path('/lustreFS/data/superworld/ckontzias/thesis')
        core_root=remote_root/'snapshots/acid-alternative-core-v1-52acea39e4a1f6da'
        d2_root=remote_root/'snapshots/acid-alt-v3-d2-2c8f890c31e9f5bf'
        for root,expected in [(core_root, '52acea39e4a1f6dadfa5d5be4ec6206a9aefb46159e5def7355a8575f0062f1d'),(d2_root,'2c8f890c31e9f5bf5e8b6769ccc424d7cd565278c422405d507d1c702d3580ea')]:
            manifest=root/'SOURCE-MANIFEST.sha256'
            if sha(manifest)!=expected:raise RuntimeError('executed source manifest changed')
            for line in manifest.read_text().splitlines():
                digest,name=line.split(maxsplit=1);p=(root/name.strip()).resolve()
                if not p.is_relative_to(root) or sha(p)!=digest:raise RuntimeError('executed source member mismatch')
        sys.path[:0]=[str(core_root),str(d2_root),str(remote_root/'src/hi-lewm'),str(remote_root/'src/hi-lewm/third_party/lewm')]
        import torch
        import numpy as np
        import stable_worldmodel as swm
        from importlib.metadata import version
        from gymnasium.spaces import Box
        hardware(torch)
        if os.environ.get('SLURM_JOB_NAME')!='dtveff0-'+job['id'] or os.environ.get('SLURMD_NODENAME')!='gpu09':
            raise RuntimeError('wrong task/allocation/node identity')
        if version('stable-worldmodel')!='0.0.6':raise RuntimeError('wrong stable-worldmodel version')
        torch.set_num_threads(4);torch.set_num_interop_threads(1)
        torch.manual_seed(0);np.random.seed(0);torch.cuda.manual_seed_all(0)
        torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
        torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=True
        torch.use_deterministic_algorithms(True)
        core=importlib.import_module('acid_alternative.costs');d2=importlib.import_module('acid_alt_d2_models')
        model_module=importlib.import_module('acid_alternative.models')
        # Authenticate all bytes before any model or saved-input deserialization.
        items=[(m['checkpoint'],m['checkpoint_sha256']) for m in job['models'].values()]
        for value,key in [(job['capture'],'artifact'),(job['saved_scores'],'artifact'),(job['offline_scores'],'artifact')]:items.append((value[key],value[key+'_sha256']))
        items.append((job['capture']['world_model_checkpoint'],job['capture']['world_model_checkpoint_sha256']))
        for path,digest in items:
            if sha(path)!=digest:raise RuntimeError('input/checkpoint authentication failed')
        authentication_seconds=time.monotonic()-began;budget()
        setup_start=time.perf_counter();models={};payloads={}
        for arm,spec in job['models'].items():
            p=torch.load(spec['checkpoint'],map_location='cpu',weights_only=False)
            if p['model_config']!=spec['model_config'] or p['seed']!=job['scorer_seed'] or p['source_manifest_sha256']!=spec['source_manifest_sha256'] or p['condition']!='true':raise RuntimeError('checkpoint metadata binding mismatch')
            model=model_module.model_from_config(p['model_config']);model.load_state_dict(p['state_dict'],strict=True)
            if any(t.is_floating_point() and t.dtype!=torch.float32 for t in p['state_dict'].values()):raise RuntimeError('stored precision differs; no silent conversion')
            if sum(x.numel() for x in model.parameters())!=spec['parameter_count']:raise RuntimeError('parameter count mismatch')
            models[arm]=model.float().cuda().eval().requires_grad_(False);payloads[arm]=p
        capture=torch.load(job['capture']['artifact'],map_location='cpu',weights_only=False)
        saved=torch.load(job['saved_scores']['artifact'],map_location='cpu',weights_only=False)
        offline=torch.load(job['offline_scores']['artifact'],map_location='cpu',weights_only=False)
        if capture['kind']!='flat_b0_final_cem_candidate_pools' or saved['kind']!='flat_same_candidate_shared_rollout_scores':raise RuntimeError('wrong saved schema')
        if capture['candidates'].shape[1:3]!=(300,5) or offline['candidates'].shape[0:3]!=(50,300,5):raise RuntimeError('wrong workload')
        for i,row in zip(job['context_indices'],job['contexts']):
            for key in ('episode_id','start_step'):
                if int(capture['rows'][i][key])!=int(row[key]):raise RuntimeError('historical context identity differs')
        world=swm.policy.AutoCostModel(world_prefix(job['capture']['world_model_checkpoint']),cache_dir=remote_root/'data/stablewm').float().cuda().eval().requires_grad_(False)
        if hasattr(world,'interpolate_pos_encoding'):world.interpolate_pos_encoding=True
        torch.cuda.synchronize();setup_seconds=time.perf_counter()-setup_start;budget()
        def wrapper(arm):return make_wrapper(core,d2,world,models,payloads,job,arm)
        def solver(w):
            a=capture['candidates'].shape[-1]
            s=swm.solver.CEMSolver(model=w,batch_size=1,num_samples=300,var_scale=1,n_steps=30,topk=30,device='cuda',seed=job['planner_seed'])
            s.configure(action_space=Box(low=-np.inf,high=np.inf,shape=(1,a//5),dtype=np.float32),n_envs=1,config=swm.PlanConfig(horizon=5,receding_horizon=5,action_block=5))
            return s
        with torch.inference_mode():
            _,control=measured(torch,lambda:None);records.append(dict(level='empty_boundary_control',**control))
            for context in job['context_indices']:
                context_audit_start=time.perf_counter()
                actions=capture['candidates'][context:context+1].float().cuda()
                trajectory=saved['predicted_trajectory'][context:context+1].float().cuda()
                goal=saved['goal_embedding'][context:context+1].float().cuda()
                info={k:v[context:context+1].cuda() for k,v in capture['info_tensors'].items()}
                if 'pixels' not in info or 'goal' not in info:raise RuntimeError('image/history interface unavailable; no silent cached-latent substitution')
                if any(k in info for k in ('emb','predicted_emb','goal_emb')):raise RuntimeError('cached latent boundary differs; return for explicit review')
                expanded={k:v[:,None].expand(1,300,*v.shape[1:]) for k,v in info.items()}
                b0=wrapper('plain');recomputed,first_rollout=measured(torch,lambda:b0.get_cost(expanded,actions))
                records.append(dict(context=context,arm='plain',level='B',phase='setup_first_rollout',**first_rollout))
                equivalent(torch,recomputed,capture['b0_cost'][context:context+1].cuda())
                _,recomputed_trajectory,_,_=b0.rollout_model._rollout_once(expanded,actions)
                equivalent(torch,recomputed_trajectory,trajectory)
                for arm in ARMS:
                    budget()
                    w1,w2=wrapper(arm),wrapper(arm)
                    a1,first_cost=measured(torch,lambda:w1.get_cost(expanded,actions))
                    records.append(dict(context=context,arm=arm,level='B',phase='first_operational_cost_before_equivalence',**first_cost))
                    a2=w2.get_cost(expanded,actions)
                    equivalent(torch,a1,a2);i1=torch.topk(a1,30,dim=1,largest=False).indices;i2=torch.topk(a2,30,dim=1,largest=False).indices
                    if not torch.equal(i1,i2):raise RuntimeError('selected indices mismatch')
                    if arm!='plain':
                        reset(w1,raw_call=True)
                        verifier=raw(w1,trajectory,actions,goal)
                        expected=recomputed+w1.lambda_weight*recomputed.std(dim=1,unbiased=True)[:,None]/verifier.std(dim=1,unbiased=True).clamp_min(1e-8)[:,None]*verifier
                        equivalent(torch,a1,expected)
                    reset(w1);reset(w2);t=Trace(w2);s1,s2=solver(w1),solver(t)
                    p1,first_solve=measured(torch,lambda:s1.solve(info))
                    records.append(dict(context=context,arm=arm,level='C',phase='first_solve_before_equivalence_and_solver_warmup',**first_solve))
                    p2=s2.solve(info)
                    equivalent(torch,p1,p2)
                    if not torch.equal(s1.torch_gen.get_state(),s2.torch_gen.get_state()):raise RuntimeError('planner RNG changed')
                    if len(t.rows)!=30:raise RuntimeError('CEM rounds changed')
                    elite=t.rows[-1][0][torch.zeros_like(t.rows[-1][2]),t.rows[-1][2]].mean(dim=1).cpu()
                    equivalent(torch,elite,p2['actions'])
                    # DTV legacy raw path also independently matches v1 on same bank.
                    if arm=='legacy_dtv':
                        p=payloads['diffusion'];old=core.SharedRolloutCostModel(world,arm='diffusion',scorer=models['diffusion'],latent_mean=p['latent_mean'],latent_std=p['latent_std'],noise_seed=p['seed'],diffusion_sigmas=(.1,.25,.5),lambda_weight=.005,record_diagnostics=True).cuda()
                        equivalent(torch,old._diffusion_cost(trajectory,actions),raw(w1,trajectory,actions,goal))
                    audit.append(dict(context=context,arm=arm,scores_sha256=output_hash(torch,a1),plan_sha256=output_hash(torch,p1),planner_rng_sha256=output_hash(torch,s1.torch_gen.get_state()),index_equivalence=True,rounds=30))
                    del t,s1,s2,p1,p2,w1,w2
                    for level in ('A','B','C'):
                        if level=='A' and arm=='plain':continue # no cached "plain checker" timing
                        w=wrapper(arm)
                        def call():
                            if level=='A':return raw(w,trajectory,actions,goal)
                            if level=='B':return w.get_cost(expanded,actions)
                            return current_solver.solve(info)
                        current_solver=solver(w)
                        reset(w,raw_call=level=='A');_,m=measured(torch,call);records.append(dict(context=context,arm=arm,level=level,phase='post_equivalence_first_reset_call',**m))
                        for _ in range(c['warmup_solves'] if level=='C' else c['warmup_calls']):
                            reset(w,raw_call=level=='A');current_solver=solver(w);call()
                            budget()
                records.append(dict(context=context,level='equivalence_and_warmup_scope',wall_seconds=time.perf_counter()-context_audit_start,overlaps_first_call_records=True))
                for block in range(c['blocks']):
                    for arm in order(block):
                        w=wrapper(arm)
                        for level in ('A','B','C'):
                            if level=='A' and arm=='plain':continue
                            for repetition in range(c['repetitions']):
                                reset(w,raw_call=level=='A');s=solver(w)
                                f=(lambda:raw(w,trajectory,actions,goal)) if level=='A' else ((lambda:w.get_cost(expanded,actions)) if level=='B' else (lambda:s.solve(info)))
                                value,m=measured(torch,f)
                                audit_start=time.perf_counter();digest=output_hash(torch,value);audit_seconds=time.perf_counter()-audit_start
                                records.append(dict(context=context,arm=arm,level=level,phase='warm',block=block,repetition=repetition,output_sha256=digest,audit_hash_seconds=audit_seconds,rollouts=30 if level=='C' else int(level=='B'),scorer_calls=(30 if level=='C' else 1) if arm!='plain' else 0,network_pairs=(45000 if level=='C' else 1500)*(3 if arm=='legacy_dtv' else int(arm!='plain')),**m))
                                budget()
            # Original offline workload is an explicit reconciliation lane, NOT online latency.
            trajectory=offline['predicted_trajectory'].float().cuda();actions=offline['candidates'].float().cuda()
            for arm in ('acid','forward','legacy_dtv'):
                budget()
                p=payloads['diffusion' if arm=='legacy_dtv' else arm];bank=d2.build_legacy_dtv_noise_bank(scorer_seed=job['scorer_seed'],horizon=5,latent_dim=trajectory.shape[-1])
                def lane(warm=False):
                    tr,ac=(trajectory[:1],actions[:1]) if warm else (trajectory,actions)
                    if arm=='legacy_dtv':return d2.legacy_dtv_costs(models['diffusion'],trajectory=tr,actions=ac,latent_mean=p['latent_mean'],latent_std=p['latent_std'],noise_bank=bank,batch_size=8192)
                    if arm=='forward':return d2.forward_literal_costs(models['forward'],trajectory=tr,actions=ac,latent_mean=p['latent_mean'],latent_std=p['latent_std'],batch_size=8192)
                    gen=torch.Generator(device='cpu').manual_seed(d2.acid_noise_seed(job['task'],job['scorer_seed'],8201,0 if warm else 1))
                    return d2.acid_literal_costs(models['acid'],trajectory=tr,actions=ac,action_mean=p['acid_action_mean'],action_std=p['acid_action_std'],generator=gen,batch_size=8192)
                lane(True)
                for repetition in range(c['offline_repetitions']):
                    _,m=measured(torch,lane);records.append(dict(level='A_offline_reconciliation',arm=arm,repetition=repetition,candidate_sequences=15000,horizon_transitions=75000,transition_chunk=8192,**m))
                    budget()
        import resource
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>c['ram_bytes']:raise RuntimeError('RAM envelope exceeded')
        groups={}
        for r in records:
            if r.get('phase')=='warm':groups.setdefault(f"{r['context']}:{r['arm']}:{r['level']}",[]).append(r)
        properties=torch.cuda.get_device_properties(0)
        result=dict(status='completed',job=job['id'],authentication_seconds=authentication_seconds,setup_seconds=setup_seconds,records=records,equivalence=audit,summaries={k:{field:summary([x[field] for x in rows]) for field in ('gpu_event_ms','synchronized_wall_ms')} for k,rows in groups.items()},rss_high_water_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,python=platform.python_version(),torch=torch.__version__,gpu=torch.cuda.get_device_name(),gpu_properties=dict(uuid=str(getattr(properties,'uuid','unavailable')),total_memory_bytes=properties.total_memory,multiprocessor_count=properties.multi_processor_count,compute_capability=[properties.major,properties.minor]),hostname=platform.node(),slurm_allocation_id=os.environ['SLURM_JOB_ID'],bindings_sha256=sha(args.bindings),wall_seconds=time.monotonic()-began,science_outcomes_computed=False)
        encoded=json.dumps(result,indent=2)
        if sum(p.stat().st_size for p in args.output.iterdir() if p.is_file())+len(encoded.encode())+4096>job['output_limit_bytes']:raise RuntimeError('profile plus seal/fault reservation exceeds worker cap')
        with (args.output/'PROFILE.json').open('x') as f:f.write(encoded)
        if sum(p.stat().st_size for p in args.output.rglob('*') if p.is_file())>job['output_limit_bytes']:raise RuntimeError('worker output cap')
        with (args.output/'SEAL.json').open('x') as f:json.dump(dict(profile_sha256=sha(args.output/'PROFILE.json'),job=job['id']),f)
    except Exception as e:
        with (args.output/'FAILURE.json').open('x') as f:json.dump(dict(error=repr(e),records_journal='RECORDS.jsonl',equivalence_journal='EQUIVALENCE.jsonl',completed_records=len(records),completed_equivalence=len(audit),wall_seconds=time.monotonic()-began,automatic_retry=False),f)
        raise
def seal_output(output,job):
    names=('PROFILE.json','SEAL.json','RECORDS.jsonl','EQUIVALENCE.jsonl','SUPERVISOR-STARTED.json','SUPERVISION.json')
    if not all((output/name).is_file() for name in names):raise RuntimeError('child completed without full evidence')
    content=json.dumps(dict(job=job,files={name:sha(output/name) for name in names}),indent=2)
    if sum(p.stat().st_size for p in output.iterdir() if p.is_file())+len(content.encode())>4000000:
        raise RuntimeError('complete supervised artifact cap exceeded')
    with (output/'CONTROL-SEAL.json').open('x') as f:f.write(content)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--bindings',type=Path,default=DOC/'BINDINGS.json')
    parser.add_argument('--approval',type=Path,default=DOC/'EXECUTION-APPROVAL.json')
    parser.add_argument('--job',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--worker-child',action='store_true')
    args=parser.parse_args()
    if args.worker_child:
        worker_main();return
    approval=json.loads(args.approval.read_text())
    if approval.get('execute') is not True or approval.get('research_execution_authorized') is not True:
        raise RuntimeError('DTV-EFF0 research execution disabled; explicit immutable execution instruction required')
    if args.output.exists():raise RuntimeError('exclusive output already exists')
    args.output.mkdir(parents=True)
    with (args.output/'SUPERVISOR-STARTED.json').open('x') as f:
        json.dump(dict(job=args.job,pid=os.getpid(),start_monotonic=ENTRY_STARTED,work_seconds=WORK_SECONDS,preservation_seconds=60),f)
    command=[sys.executable,'-m','dtv_efficiency_r1.profile',*sys.argv[1:],'--worker-child']
    record=supervise(command,args.output,work_seconds=WORK_SECONDS,started=ENTRY_STARTED)
    if record['fault'] or record['child_exit_code']!=0:raise SystemExit(124 if record['fault']=='work_deadline' else 1)
    try:seal_output(args.output,args.job)
    except Exception as e:
        if not (args.output/'FAILURE.json').exists():
            with (args.output/'FAILURE.json').open('x') as f:json.dump(dict(error=repr(e),automatic_retry=False),f)
        raise

if __name__=='__main__':main()
