"""Real runtime bindings. Called only after new-study byte/capability gates.

Initializers reuse native physics, never the historical PushT integration-step
setter. No evaluation payload is decoded on import or during preparation.
"""
from dtv_success_cost.common import *

def read_source(c, job):
    import h5py
    spec=c['models'][f'{job["task"]}-{job["scorer_seed"]}'];row=c['cohort'][job['task']][job['source_index']]
    if row['parent_id']!=int(job['id'].split('-')[1]) or row['partition']!='P2':raise RuntimeError('source role mismatch')
    keys={'pusht':('state','proprio'), 'reacher':('qpos','qvel'), 'cube':('qpos','qvel','privileged_block_0_pos','privileged_block_0_quat')}[job['task']]
    # Whole-file authentication is byte-only; only these two allowlisted frames are decoded.
    with h5py.File(spec['dataset'],'r') as f:
        if int(f['ep_len'][row['parent_id']])!=row['parent_length'] or int(f['ep_offset'][row['parent_id']])+row['start_step']!=row['source_row']:raise RuntimeError('canonical parent offset mismatch')
        group=f['data'] if 'data' in f and hasattr(f['data'],'keys') else f
        data={k:group[k][row['source_row']] for k in keys}
        goal={k:group[k][row['goal_row']] for k in keys}
        pixels=group['pixels'][row['goal_row']]
    import numpy as np
    if pixels.dtype!=np.uint8 or pixels.ndim!=3 or pixels.shape[-1]!=3 or pixels.nbytes>200000:raise RuntimeError('declared RGB target-frame interface/footprint changed')
    from dtv_success_cost.worker import file_identity
    record=load(run_namespace(c)/'preflight/INPUT-AUTHENTICATION.json')['datasets'][spec['dataset']]
    if record['identity']!=file_identity(spec['dataset']):raise RuntimeError('input changed during allowlisted read')
    return data,goal,pixels

def environment(task, data, target, seed):
    import gymnasium as gym
    import numpy as np
    import stable_worldmodel as swm
    if task=='pusht':
        import pusht_fresh_initialization as fresh
        fresh.register()
        world=swm.World(env_name=fresh.ENV_ID,num_envs=1,image_shape=(224,224),max_episode_steps=100,verbose=0,correct_velocity_space=True)
        return world,lambda: fresh.reset_world(world,[dict(state=data['state'],goal_state=target['state'],proprio=data['proprio'])],seed=seed)
    if task=='reacher':
        env_id='dtveff1/Reacher-v0'
        if env_id not in gym.registry:
            from stable_worldmodel.envs.dmcontrol.reacher import ReacherDMControlWrapper
            gym.register(env_id,entry_point=ReacherDMControlWrapper)
        world=swm.World(env_name=env_id,num_envs=1,image_shape=(224,224),max_episode_steps=100,verbose=0,task='qpos_match')
        options=dict(state=np.concatenate((data['qpos'],data['qvel'])),target_qpos=target['qpos'])
        return world,lambda:world.reset(seed=seed,options=options)
    env_id='dtveff1/Cube-v0'
    if env_id not in gym.registry:
        from stable_worldmodel.envs.ogbench.cube_env import CubeEnv
        class FreshCube(CubeEnv):
            def reset(self,seed=None,options=None):
                base_result=super().reset(seed=seed,options=options)
                if options is None:return base_result  # native lazy observation-space bootstrap, not an evaluation reset
                # ManipSpaceEnv consumes options rather than forwarding `state`.
                # Apply the declared qpos/qvel before outer wrappers render/store.
                state=options['state'];self.set_state(state[:self._model.nq],state[self._model.nq:]);self.pre_step()
                self.set_target_pos(0,options['target_pos'],options['target_quat']);self.post_step()
                return self.compute_observation(),self.get_reset_info()
        gym.register(env_id,entry_point=FreshCube)
    world=swm.World(env_name=env_id,num_envs=1,image_shape=(224,224),max_episode_steps=100,verbose=0,env_type='single',ob_type='states',multiview=False,width=224,height=224,visualize_info=False,terminate_at_goal=True)
    options=dict(state=np.concatenate((data['qpos'],data['qvel'])),target_pos=target['privileged_block_0_pos'],target_quat=target['privileged_block_0_quat'])
    return world,lambda:world.reset(seed=seed,options=options)

class Decoder:
    def __init__(self,mean,scale):self.mean_=mean;self.scale_=scale
    def inverse_transform(self,a):
        # sklearn's historical StandardScaler inverse uses two in-place
        # operations, retaining the solver's float32 array dtype/rounding.
        result=a.copy();result*=self.scale_;result+=self.mean_;return result

class Adapter:
    def __init__(self,job,config,world_model,models,payloads,spec,data,goal,pixels):
        import torch,numpy as np,stable_worldmodel as swm
        import importlib,time
        from torchvision.transforms import v2 as transforms
        from dtv_efficiency.profile import make_wrapper
        self.task=job['task'];self.target=goal;self.torch=torch;self.np=np;self.plans=[];self.solve_cursor=0
        np.random.seed(job['environment_seed']) # native legacy global sampling, episode-owned reset
        self.source_data=data
        self.world,self._reset=environment(self.task,data,goal,job['environment_seed'])
        p=payloads['diffusion'];actual=np.array(p['planner_primitive_action_mean'],dtype=np.float64);std=np.array(p['planner_primitive_action_std'],dtype=np.float64)
        expected=spec['decoder']['diffusion']
        if not np.allclose(actual,expected['expected_mean'],rtol=0,atol=4*np.finfo(np.float32).eps) or not np.allclose(std,expected['expected_scale'],rtol=0,atol=4*np.finfo(np.float32).eps):raise RuntimeError('frozen decoder changed')
        # Use recovered full-source-dtype statistics, not a refit or rounded checkpoint reconstruction.
        self.decode=Decoder(np.array(expected['actual_mean']),np.array(expected['actual_scale']))
        for other in spec['decoder'].values():
            if other['actual_mean']!=expected['actual_mean'] or other['actual_scale']!=expected['actual_scale']:raise RuntimeError('decoder not shared')
        method=config[:-2];arm='d1_sigma025' if method=='dtv' else method
        core=importlib.import_module('acid_alternative.costs');d2=importlib.import_module('acid_alt_d2_models')
        w=make_wrapper(core,d2,world_model,models,payloads,job,arm)
        class Count:
            def __init__(self,w):self.w=w;self.calls=0
            def get_cost(self,info,actions):self.calls+=1;return self.w.get_cost(info,actions)
        counted=Count(w);self.wrapper=w
        solver=swm.solver.CEMSolver(counted,num_samples=300,topk=30,n_steps=int(config[-2:]),var_scale=1,batch_size=1,device='cuda',seed=job['planner_seed'])
        original=solver.solve
        def solve(info,init_action=None):
            before=counted.calls;self.sync();began=time.perf_counter();outputs=original(info,init_action=init_action);self.sync();wall=time.perf_counter()-began
            self.plans.append(dict(solve_seconds=wall,populations=counted.calls-before,candidates=(counted.calls-before)*300,return_rule='final_elite_mean',normalized_actions=outputs['actions'].reshape(25,-1)))
            return outputs
        solver.solve=solve
        image=transforms.Compose([transforms.ToImage(),transforms.ToDtype(torch.float32,scale=True),transforms.Normalize(mean=[.485,.456,.406],std=[.229,.224,.225]),transforms.Resize(size=224)])
        self.policy=swm.policy.WorldModelPolicy(solver,swm.PlanConfig(horizon=5,receding_horizon=5,action_block=5),process={'action':self.decode},transform={'pixels':image,'goal':image})
        self.world.set_policy(self.policy)
        self.pixels=np.asarray(pixels)
    def sync(self):self.torch.cuda.synchronize()
    def reset(self):
        self._reset();n=self.native
        if self.task=='pusht':
            if not self.np.array_equal(n._get_obs(),self.source_data['state']):raise RuntimeError('instantaneous PushT source initialization changed')
        else:
            data=n.env.physics.data if self.task=='reacher' else n._data
            if not self.np.allclose(data.qpos,self.source_data['qpos'],rtol=0,atol=1e-12) or not self.np.allclose(data.qvel,self.source_data['qvel'],rtol=0,atol=1e-12):raise RuntimeError('source physical initialization changed')
        self.torch.cuda.reset_peak_memory_stats()
    @property
    def native(self):return self.world.envs.unwrapped.envs[0].unwrapped
    def evidence(self):
        n=self.native
        if self.task=='pusht':current=n._get_obs();target=n.goal_state
        elif self.task=='reacher':current=n.env.physics.data.qpos.copy();target=n.env.task.target_qpos.copy()
        else:current=n._data.joint('object_joint_0').qpos[:3].copy();target=n._data.mocap_pos[n._cube_target_mocap_ids[0]].copy()
        return dict(current=self.np.asarray(current).tolist(),target=self.np.asarray(target).tolist())
    def native_success(self):
        n=self.native
        if self.task=='pusht':
            e=self.evidence();return bool(n.eval_state(self.np.array(e['target']),self.np.array(e['current']))[0])
        if self.task=='reacher':return n.env.task.get_termination(n.env.physics) is not None
        return bool(n._success)
    def action(self):
        # Actual fresh observations, never saved start pixels. Goal is the exact saved target frame.
        info={'pixels':self.world.infos['pixels'], 'goal':self.pixels[None,None]}
        action=self.policy.get_action(info);new=None
        if len(self.plans)>self.solve_cursor:new=self.plans[-1];self.solve_cursor+=1
        return action,new
    def step(self,action):
        self.world.states,self.world.rewards,t,u,self.world.infos=self.world.envs.step(action)
        return bool(t[0]),bool(u[0])
    def action_list(self,action):return self.np.asarray(action)[0].tolist()
    def plan_list(self,plan):return dict(plan,normalized_actions=plan['normalized_actions'].tolist())
    def decoder(self):return dict(mean=self.decode.mean_.tolist(),scale=self.decode.scale_.tolist(),precision='float32_inplace_multiply_then_add')
    def resources(self):
        import resource
        return dict(rss_process_high_water_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                    cuda_peak_allocated_bytes=self.torch.cuda.max_memory_allocated(),cuda_peak_reserved_bytes=self.torch.cuda.max_memory_reserved())
    def close(self):self.world.close()
