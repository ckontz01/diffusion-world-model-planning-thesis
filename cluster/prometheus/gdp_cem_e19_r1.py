"""Bounded native-interface reset and fixed-stimulus engineering diagnostic."""
from __future__ import annotations
import argparse
from copy import deepcopy
import hashlib
import inspect
import json
from pathlib import Path
import random
import numpy as np
import torch

ROOT = Path('/lustreFS/data/superworld/ckontzias/thesis')
PARENT = ROOT / 'snapshots/gdp-cem-e19-discrepancy-e347bc087381ecf0'
RAW = ROOT / 'experiments/gdp-cem-e19/discrepancy-diagnostic-run-20260829-e347bc08'
E19 = ROOT / 'experiments/gdp-cem-e19/native-reproduction-run-20260828-9f549988'
E18 = ROOT / 'snapshots/gdp-cem-e18-182ed1e7d1e99946'
CASES = ((0,19),(0,0),(2,0),(3,0),(3,1))
STEPS = 15

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024), b''): h.update(block)
    return h.hexdigest()

def encode(x):
    if torch.is_tensor(x):
        a=x.detach().cpu().contiguous()
        return {'shape':list(a.shape),'dtype':str(a.dtype),
                'sha256':hashlib.sha256(a.reshape(-1).view(torch.uint8).numpy().tobytes()).hexdigest(),
                **({'values':a.float().tolist()} if a.numel()<=4096 else {})}
    if isinstance(x,np.ndarray):
        if x.dtype.hasobject: return encode(x.tolist())
        return {'shape':list(x.shape),'dtype':str(x.dtype),
                'sha256':hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest(),
                **({'values':encode(x.tolist())} if x.size<=4096 else {})}
    if isinstance(x,np.generic): return encode(x.item())
    if isinstance(x,dict): return {str(k):encode(v) for k,v in sorted(x.items())}
    if isinstance(x,(tuple,list)): return [encode(v) for v in x]
    if isinstance(x,float) and not np.isfinite(x): return {'nonfinite':str(x)}
    if isinstance(x,(str,int,float,bool)) or x is None: return x
    return {'unrecorded_type':type(x).__module__+'.'+type(x).__name__}

def digest(x): return hashlib.sha256(json.dumps(encode(x),sort_keys=True).encode()).hexdigest()

def seal(path,payload):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as f: json.dump(encode(payload),f,indent=2,sort_keys=True,allow_nan=False); f.write('\n')
    path.chmod(0o444)
    with (path.parent/'sha256.txt').open('x') as f: f.write(f'{sha(path)}  {path.name}\n')

def verified(path):
    records={}
    for line in (path.parent/'sha256.txt').read_text().splitlines():
        h,n=line.split(maxsplit=1); records[n.lstrip('*')]=h
    assert records[path.name]==sha(path), str(path)
    return sha(path)

def choose(bank,row,dim):
    if 'top_actions' in bank:
        options=[(None,bank['top_actions'][row])]
        label='saved historical planner output'
    else:
        options=enumerate(bank['candidates'][row])
        label='fixed diagnostic action stimulus'
    for index,macro in options:
        a=macro.reshape(-1,dim)[:STEPS]
        if len(a)==STEPS and torch.isfinite(a).all() and a.abs().max()>1e-8 and torch.unique(a).numel()>1:
            return index,a.clone(),label,encode(macro)
    raise ValueError('no eligible fixed sequence; no scientific fallback')

def prepare(out):
    from trace_gdp_cem_e19_discrepancy import canonical_sha256
    from gdp_cem_e19_discrepancy_specs import sentinel_by_id
    assert sha(PARENT/'SOURCE-MANIFEST.sha256')=='e347bc087381ecf0902581e8225165dbd64c887eba661b74b064c09d4e13d7fa'
    cases=[]
    for cid,(sid,row) in enumerate(CASES):
        s=sentinel_by_id(sid); task=s.benchmark; dim=2 if task=='pusht' else 5
        bp=RAW/f'sentinels/s{sid}/r0/comparison-bank.pt'; bh=verified(bp)
        b=torch.load(bp,map_location='cpu',weights_only=False)
        assert canonical_sha256({k:v for k,v in b.items() if k!='content_sha256'})==b['content_sha256']
        idx,a,label,macro=choose(b,row,dim)
        mp=PARENT/f'official-sage/data/manifests/{task}/seed32/h{s.horizon}.json'
        m=json.loads(mp.read_text()); rec=m['records'][row] if 'records' in m else {}
        ep=int(rec.get('local_episode',m.get('episodes_idx',[None]*50)[row]))
        start=int(rec.get('start_frame',m.get('start_steps',[None]*50)[row]))
        cp=E19/f'checkpoints/{task}_action_prior.pt'
        release=json.loads((PARENT/'official-sage/configs/checkpoints.json').read_text())
        assert sha(cp)==release[task+'_action_prior']['sha256']
        ck=torch.load(cp,map_location='cpu',weights_only=False); stats=ck['stats']
        mean=stats['action_mean'].float().numpy(); std=np.maximum(stats['action_std'].float().numpy(),1e-6)
        physical=a.float().numpy()*std+mean
        assert np.isfinite(physical).all()
        args=ck.get('run_manifest',{}).get('args',{})
        cases.append(dict(case_id=cid,sentinel_id=sid,manifest_row=row,task=task,episode=ep,start=start,
            horizon=s.horizon,manifest_record=rec,manifest_path=str(mp),manifest_sha256=sha(mp),
            bank_path=str(bp),bank_sha256=bh,bank_content_sha256=b['content_sha256'],
            action_source=label,candidate_index=idx,source_macro=macro,stored_record=encode(a),
            normalized=a.float().tolist(),physical=physical.tolist(),physical_record=encode(physical),
            action_mean=mean.tolist(),action_std=std.tolist(),checkpoint_path=str(cp),checkpoint_sha256=sha(cp),
            lowdim_keys=list(stats.get('lowdim_keys',args.get('lowdim_keys',['observation'])))+list(stats.get('goal_lowdim_keys',args.get('goal_lowdim_keys',[]))),
            context=int(args.get('context_len',args.get('history_len',3)))))
    seal(out/'STIMULI.json',dict(cases=cases,steps=STEPS,selection_before_simulator_execution=True,
        new_planning=False,protected_read=False))

def simple(x,depth=0):
    if isinstance(x,(str,bool,int,float,np.generic,np.ndarray)) or x is None: return True
    if depth<2 and isinstance(x,(tuple,list)): return all(simple(v,depth+1) for v in x)
    if depth<2 and isinstance(x,dict): return all(isinstance(k,str) and simple(v,depth+1) for k,v in x.items())
    return False

def rngs(env):
    def space(s):
        r=getattr(s,'__dict__',{}).get('_np_random')
        result={'rng':deepcopy(r.bit_generator.state) if r is not None else None}
        children=getattr(s,'spaces',None)
        if isinstance(children,dict): result['children']={k:space(v) for k,v in children.items()}
        return result
    r=vars(env).get('_np_random')
    return {'env':deepcopy(r.bit_generator.state) if r is not None else None,
            'env_seed':vars(env).get('_np_random_seed'),
            'numpy_global':np.random.get_state(),'python_global':random.getstate(),
            'spaces':{k:space(getattr(env,k)) for k in ('action_space','observation_space','variation_space') if hasattr(env,k)}}

def physical(env,task):
    extra={k:deepcopy(v) for k,v in vars(env).items() if simple(v) and not k.startswith(('_cur_goal','_goal'))}
    if task=='cube':
        import mujoco
        model,data=env._model,env._data
        flag=mujoco.mjtState.mjSTATE_INTEGRATION
        state=np.empty(mujoco.mj_stateSize(model,flag)); mujoco.mj_getState(model,data,state,flag)
        fields=('qpos','qvel','qacc','qacc_warmstart','act','ctrl','mocap_pos','mocap_quat','qfrc_applied','xfrc_applied','userdata','plugin_state','site_xpos','site_xmat','cfrc_ext')
        contacts=[{k:np.array(getattr(data.contact[i],k),copy=True) for k in ('dist','pos','frame','geom1','geom2','friction','solref','solimp')} for i in range(data.ncon)]
        return {'integration':state,'integration_flag':int(flag),'time':data.time,
            'data':{k:np.array(getattr(data,k),copy=True) for k in fields if hasattr(data,k)},
            'contacts':contacts,'outside':extra,
            'model':{k:encode(np.asarray(getattr(model,k))) for k in ('body_mass','body_inertia','geom_friction','dof_damping','actuator_gainprm','actuator_biasprm','geom_solref','geom_solimp')},
            'timestep':model.opt.timestep,'solver':int(model.opt.solver)}
    bodies={}
    for name in ('agent','block'):
        b=getattr(env,name)
        bodies[name]={k:np.asarray(getattr(b,k)).copy() for k in ('position','velocity','angle','angular_velocity','force','torque','mass','moment','center_of_gravity','is_sleeping')}
        arbs=[]
        def arb(a):
            pts=a.contact_point_set
            arbs.append({'normal':list(pts.normal),'points':[{'a':list(p.point_a),'b':list(p.point_b),'distance':p.distance} for p in pts.points], 'impulse':list(a.total_impulse)})
        b.each_arbiter(arb); bodies[name]['arbiters']=arbs
    return {'bodies':bodies,'outside':extra,'space':{k:getattr(env.space,k) for k in ('damping','iterations','collision_slop','collision_bias','collision_persistence','sleep_time_threshold')},
        'unavailable':'complete internal Pymunk integration/contact cache serialization not captured'}

class Finished(Exception): pass

def step_phase(phase):
    """Native reset steps never consume the post-restoration action budget."""
    return 'reset' if phase['reset'] else 'stimulus'

class FixedReturn:
    """No planner/model; emit a prespecified tensor exactly once."""
    def __init__(self,actions):
        self.actions=actions; self.calls=0; self.device=torch.device('cpu')
        self.primitive_action_dim=actions.shape[-1]//5
        self.action_dim=actions.shape[-1]; self.horizon=actions.shape[1]; self.n_envs=1
    def configure(self,**kwargs): pass
    def solve(self,info,**kwargs):
        if self.calls: raise RuntimeError('new planning/stimulus forbidden')
        self.calls+=1; self.prepared=encode(info)
        return {'actions':self.actions.clone(),'costs':[float('nan')]}
    def __call__(self,info,**kwargs): return self.solve(info,**kwargs)

def execute(prep,out,stack,cid,repeat):
    import stable_worldmodel as swm
    from sklearn.preprocessing import StandardScaler
    verified(prep); case=json.loads(prep.read_text())['cases'][cid]
    task=case['task']; dim=2 if task=='pusht' else 5
    # Capture RNG behavior, do not add an explicit environment seed.
    if stack=='sage':
        from sage.eval import pusht,cube
        pusht.set_determinism(32)
        module=pusht if task=='pusht' else cube
        scaler=(pusht.ArrayNormalizer if task=='pusht' else cube.FixedScaler)(case['action_mean'],case['action_std'])
        dataset_path=E19/'preparation/pusht_expert_train.lance' if task=='pusht' else ROOT/'data/stablewm/cube_single_expert.h5'
        dataset=swm.data.load_dataset(str(dataset_path))
        world=swm.World('swm/PushT-v1' if task=='pusht' else 'swm/OGBCube-v0',num_envs=1,image_shape=(224,224),max_episode_steps=case['horizon']*(4 if task=='pusht' else 2))
        hooks=[{'method':'_set_state','args':{'state':{'value':'state'}}},{'method':'_set_goal_state','args':{'goal_state':{'value':'goal_state'}}}] if task=='pusht' else cube.cube_callables()
        normalized=np.asarray(case['normalized'],dtype=np.float32)
        solver=FixedReturn(torch.from_numpy(normalized).reshape(1,3,5*dim))
        kwargs=dict(solver=solver,config=swm.PlanConfig(horizon=3,receding_horizon=3,action_block=5,warm_start=False),process={'action':scaler},transform={'pixels':module.image_transform(224,torch.bfloat16),'goal':module.image_transform(224,torch.bfloat16)},schedule_steps=[15],goal_offset_steps=case['horizon'],history_length=case['context'])
        policy=pusht.ScheduledPolicy(**kwargs,frameskip=5) if task=='pusht' else cube.CubeScheduledPolicy(**kwargs,history_stride=5,lowdim_keys=case['lowdim_keys'])
        seed=32
    else:
        from omegaconf import OmegaConf
        import gdp_cem_e18_specs as spec
        from gdp_cem_e18_runtime import E18ScheduledPolicy
        from evaluate_gdp_cem_e18 import image_transform
        h=75 if task=='pusht' else 150
        seed=spec.derived_seed(f'planner|task={task}|h={h}|replicate=1|shard=0')
        np.random.seed(seed%(2**32)); torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.benchmark=False; torch.backends.cudnn.deterministic=True; torch.use_deterministic_algorithms(True)
        cfg=OmegaConf.load(ROOT/f'src/hi-lewm/third_party/lewm/config/eval/{task}.yaml')
        wc=OmegaConf.to_container(cfg.world,resolve=False); wc.update(num_envs=1,max_episode_steps=case['horizon']*(4 if task=='pusht' else 2))
        world=swm.World(**wc,image_shape=(224,224))
        dataset_path=ROOT/'data/stablewm'/('pusht_expert_train.h5' if task=='pusht' else 'cube_single_expert.h5')
        name='pusht_expert_train' if task=='pusht' else 'ogbench/cube_single_expert'
        dataset=swm.data.HDF5Dataset(name,keys_to_cache=list(cfg.dataset.keys_to_cache),cache_dir=ROOT/'data/stablewm')
        assert dataset.h5_path.resolve()==dataset_path.resolve()
        process={}
        for col in cfg.dataset.keys_to_cache:
            values=dataset.get_col_data(col); values=values[~np.isnan(values).any(axis=1)]
            process[col]=StandardScaler().fit(values)
            if col!='action': process['goal_'+col]=process[col]
        scaler=process['action']
        normalized=scaler.transform(np.asarray(case['physical'],dtype=np.float32))
        solver=FixedReturn(torch.from_numpy(normalized).float().reshape(1,3,5*dim))
        policy=E18ScheduledPolicy(solver,schedule=(15,),environment_budget=15,state_key='state' if task=='pusht' else 'observation',process=process,transform={'pixels':image_transform(224),'goal':image_transform(224)})
        hooks=OmegaConf.to_container(cfg.eval.callables,resolve=True)
    world.set_policy(policy)
    envs=world.envs.envs if stack=='sage' else world.envs.unwrapped.envs
    env=envs[0].unwrapped
    events=[]; phase={'reset':False,'steps':0,'reset_steps':0,'inside_step':False}; intended={}
    oldload=dataset.load_chunk
    def load_chunk(*a,**kw):
        rows=oldload(*a,**kw)
        events.append({'stage':'dataset_endpoints','args':encode(a),'kwargs':encode(kw),
            'columns':list(dataset.column_names),
            'endpoints':[{k:{'first':encode(v[0]),'last':encode(v[-1])} for k,v in row.items() if isinstance(v,(np.ndarray,torch.Tensor)) and v.ndim>0} for row in rows]})
        return rows
    dataset.load_chunk=load_chunk
    def snapshot(stage,**extra):
        chain=[]; current=envs[0]
        while current is not env:
            chain.append({'type':type(current).__module__+'.'+type(current).__name__,
                'state':encode({k:v for k,v in vars(current).items() if simple(v)})})
            current=current.env
        events.append({'stage':stage,'physical':encode(physical(env,task)),'rng':encode(rngs(env)),
            'wrappers':chain,**encode(extra)})
    oldreset=world.reset
    def reset(*a,**kw):
        phase['reset']=True
        result=oldreset(*a,**kw); phase['reset']=False
        snapshot('after_reset',reset_args=a,reset_kwargs=kw,reset_info=world.infos)
        return result
    world.reset=reset
    for hook in hooks:
        name=hook['method']; original=getattr(env,name)
        def wrapped(*a,_original=original,_name=name,**kw):
            result=_original(*a,**kw)
            if not phase['reset']:
                if not phase['inside_step']: intended[_name]=deepcopy(kw)
                snapshot(('inside_step_hook:' if phase['inside_step'] else 'after_hook:')+_name,args=a,kwargs=kw)
            return result
        setattr(env,name,wrapped)
    rawstep=env.step
    def step(action):
        if step_phase(phase)=='reset':
            events.append({'stage':f'reset_internal_action:{phase["reset_steps"]}','action':encode(np.asarray(action))})
            result=rawstep(action); phase['reset_steps']+=1
            return result
        if phase['steps']>=STEPS: raise Finished()
        snapshot(f'before_step:{phase["steps"]}',primitive_action=np.asarray(action))
        phase['inside_step']=True
        result=rawstep(action)
        phase['inside_step']=False
        phase['steps']+=1
        snapshot(f'after_step:{phase["steps"]}',observation=result[0],info={k:v for k,v in result[4].items() if k!='success'},terminated=bool(result[2]),truncated=bool(result[3]))
        return result
    env.step=step
    oldaction=policy.get_action
    def action(info,**kw):
        if phase['steps']>=STEPS: raise Finished()
        if phase['steps']==0:
            before=digest((physical(env,task),rngs(env)))
            obs=env._get_obs() if task=='pusht' else env.compute_observation()
            fresh_info=env._get_info() if task=='pusht' else env.compute_ob_info()
            frame=env.render()
            after=digest((physical(env,task),rngs(env)))
            snapshot('before_first_action',supplied=info,fresh_observation=obs,fresh_info=fresh_info,fresh_render=frame,observation_probe_captured_state_unchanged=before==after,intended=intended)
        result=oldaction(info,**kw)
        events.append({'stage':f'policy_action:{phase["steps"]}','world_action':encode(result),'supplied':encode(info)})
        return result
    policy.get_action=action
    stopped=False
    try:
        common=dict(dataset=dataset,episodes_idx=[case['episode']],start_steps=[case['start']],eval_budget=STEPS+1,callables=hooks)
        if stack=='sage': world.evaluate(**common,goal_offset=case['horizon'],seed=32)
        else: world.evaluate_from_dataset(**common,goal_offset_steps=case['horizon'],save_video=False,video_path=out.parent/'video-disabled')
    except Finished: stopped=True
    except Exception as exc:
        seal(out.parent/'TECHNICAL-FAILURE.json',dict(case=case,stack=stack,repeat=repeat,
            error_type=type(exc).__name__,error=str(exc),events=events,steps=phase['steps']))
        raise
    finally: world.close()
    source_paths={swm.__file__,inspect.getsourcefile(type(world)),inspect.getsourcefile(type(env)),inspect.getsourcefile(type(policy))}
    payload=dict(case=case,stack=stack,repeat=repeat,global_seed=seed,events=events,steps=phase['steps'],stopped_at_cap=stopped,
        fixed_return_calls=solver.calls,prepared=solver.prepared if solver.calls else None,
        action_scaler={k:encode(getattr(scaler,k)) for k in ('mean','std','mean_','scale_') if hasattr(scaler,k)},
        reencoded_actions=encode(normalized),source_hashes={str(p):sha(p) for p in source_paths if p},
        reset_internal_step_count=phase['reset_steps'],
        new_planning=False,benchmark_result_emitted=False,protected_read=False,
        limitation='one-env fixed-stimulus engineering check; no historical CEM plan reconstruction or cross-stack performance claim')
    seal(out,payload)

def main():
    p=argparse.ArgumentParser(); p.add_argument('mode',choices=['prepare','execute']); p.add_argument('--output',type=Path,required=True)
    p.add_argument('--prepared',type=Path); p.add_argument('--stack',choices=['sage','e18']); p.add_argument('--case',type=int); p.add_argument('--repeat',type=int,choices=[0,1]); a=p.parse_args()
    assert ROOT/'experiments/gdp-cem-e19-r1' in a.output.resolve().parents
    torch.set_num_threads(4)
    if a.mode=='prepare': prepare(a.output)
    else:
        assert a.case in range(len(CASES))
        execute(a.prepared,a.output,a.stack,a.case,a.repeat)
if __name__=='__main__': main()
