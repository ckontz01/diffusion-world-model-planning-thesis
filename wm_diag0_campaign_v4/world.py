"""Exact reviewed native worlds; authoritative restoration is fresh reset/replay.

The state audit is deliberately not described as a portable contact-cache snapshot.
Pymunk caches remain owned by each fresh world and are tested through replay and
action consequences in the included diagnostic technical tranche.
"""
import itertools
_instances=itertools.count()
import hashlib
import json
import random
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from .common import canonical, identity
from wm_diag0.core import array_id

def plain(value):
    if isinstance(value, np.ndarray):
        if value.dtype.hasobject or (value.dtype.kind in 'fc' and not np.isfinite(value).all()): raise ValueError('finite numeric state')
        return {'dtype':value.dtype.str,'shape':list(value.shape),'values':value.tolist()}
    if isinstance(value,np.generic): return plain(value.item())
    if isinstance(value,dict): return {str(k):plain(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)): return [plain(v) for v in value]
    if value is None or type(value) in (bool,str,int): return value
    if type(value) is float:
        if not np.isfinite(value): raise ValueError('nonfinite scalar state')
        return value
    raise TypeError('explicit state fields only: '+str(type(value)))

def rng_state(rng):
    if isinstance(rng,np.random.Generator): return plain(rng.bit_generator.state)
    if isinstance(rng,np.random.RandomState): return plain(rng.get_state())
    raise TypeError('declared RNG type')

def variations(space):
    if hasattr(space,'spaces'):
        return {k:variations(v) for k,v in space.spaces.items()}
    row={'class':type(space).__name__,'value':plain(space.value)}
    for k in ('low','high','init_value','n','start'):
        if hasattr(space,k): row[k]=plain(getattr(space,k))
    if hasattr(space,'np_random'): row['rng']=rng_state(space.np_random)
    return row

def native_endpoint(task, state, goal):
    state,goal=np.asarray(state),np.asarray(goal)
    if task=='pusht':
        d=abs(float(state[4]-goal[4]))%(2*np.pi)
        return bool(np.linalg.norm(state[:4]-goal[:4])<20 and min(d,2*np.pi-d)<np.pi/9)
    if task=='reacher': return bool(np.all(np.abs(state-goal)<.05))
    raise ValueError('task')

class NativeWorld:
    def __init__(self,row):
        import gymnasium as gym
        self.serial=next(_instances)
        self.row=row; self.task=row['task']; self.clock=0; self.stopped=False; self.goal_installed=False
        self.base=None; self.env=None; self.physics_calls=0
        seed=row['seeds']['native_reset']; random.seed(seed); np.random.seed(seed)
        if self.task=='pusht':
            from stable_worldmodel.envs.pusht.env import PushT
            self.base=PushT(block_cog=None,damping=None,render_action=False,resolution=224,
                            with_target=False,render_mode='rgb_array',relative=True,init_value=None)
            eid='swm/PushT-v1'
        elif self.task=='reacher':
            from stable_worldmodel.envs.dmcontrol.reacher import ReacherDMControlWrapper
            self.base=ReacherDMControlWrapper(task='qpos_match',seed=seed,environment_kwargs={},render_mode='rgb_array')
            eid='swm/ReacherDMControl-v0'
        else: raise ValueError('task')
        self.base.spec=gym.envs.registration.EnvSpec(eid)
        self.env=gym.wrappers.TimeLimit(self.base,max_episode_steps=100)

    def pixels(self):
        x=np.array(self.base.render(),copy=True)
        if x.shape!=(224,224,3) or x.dtype!=np.uint8: raise ValueError('native RGB format')
        return x

    def coordinates(self):
        if self.task=='pusht': return self.base._get_obs().copy()
        return self.base.env.physics.data.qpos.copy()

    def labels(self):
        x=self.coordinates()
        if self.task=='pusht': return np.r_[x[:4],np.cos(x[4]),np.sin(x[4])]
        return x

    def configuration(self):
        import importlib.metadata
        row={'task':self.task,'constructor':{'relative':True,'with_target':False,'resolution':224,'block_cog':None,'damping':None,'render_action':False} if self.task=='pusht' else {'task':'qpos_match','environment_kwargs':{},'camera':0,'width':224,'height':224,'action_repeat':2},
             'variation':variations(self.base.variation_space),'time_limit':100,
             'native_reset':self.row['seeds']['native_reset'],'variation_render_streams':'reserved_unused_native_reset_coupled',
             'versions':{n:importlib.metadata.version(n) for n in ('numpy','gymnasium','pymunk','pygame','dm-control','mujoco')}}
        import cv2
        row['versions']['cv2']=cv2.__version__
        if self.task=='pusht':
            if int(self.base.variation_space['block']['shape'].value)!=2: raise ValueError('fixed default T block')
            row.update(dt=self.base.dt,control_hz=self.base.control_hz,kp=self.base.k_p,kv=self.base.k_v,
                       integrator_steps_per_controller_action=10,reset_integrator_steps=2,
                       original_collection_goal=plain(self.base.goal_state),original_collection_goal_pixels=array_id(self.base._goal))
        else:
            e=self.base.env; p=e.physics
            assets={str(f.relative_to(self.base._mjcf_tempdir.name)):identity(f) for f in sorted(Path(self.base._mjcf_tempdir.name).rglob('*')) if f.is_file()}
            row.update(physics_timestep=p.timestep(),dm_control_timestep=e.control_timestep(),
                       n_sub_steps=e._n_sub_steps,action_repeat=self.base.action_repeat,compiled_assets=assets,
                       legacy_step=p.legacy_step,task_random=rng_state(e.task.random),original_collection_target_qpos=plain(e.task.target_qpos))
        return row

    def audit(self):
        b=self.base
        common={'clock':self.clock,'wrapper_elapsed':self.env._elapsed_steps,
                'python_rng':plain(random.getstate()),'numpy_rng':plain(np.random.get_state()),
                'variation':variations(b.variation_space)}
        if self.task=='pusht':
            def body(x):
                return {'position':list(x.position),'velocity':list(x.velocity),'angle':x.angle,
                        'angular_velocity':x.angular_velocity,'force':list(x.force),'torque':x.torque,
                        'mass':x.mass if np.isfinite(x.mass) else 'infinite',
                        'moment':x.moment if np.isfinite(x.moment) else 'infinite',
                        'center_of_gravity':list(x.center_of_gravity),'sleeping':bool(x.is_sleeping)}
            contacts=[]
            def arbiter(a):
                cs=a.contact_point_set
                contacts.append({'normal':list(cs.normal),'points':[{'a':list(p.point_a),'b':list(p.point_b),'distance':p.distance} for p in cs.points],
                                 'total_impulse':list(a.total_impulse),'friction':a.friction,'restitution':a.restitution,
                                 'surface_velocity':list(a.surface_velocity),'first_contact':bool(a.is_first_contact)})
            b.block.each_arbiter(arbiter)
            common.update(agent=body(b.agent),block=body(b.block),contacts=sorted(contacts,key=canonical),
                          space={k:plain(getattr(b.space,k)) for k in ('damping','iterations','collision_slop','collision_bias','collision_persistence','idle_speed_threshold')},
                          gravity=list(b.space.gravity),sleep_time_threshold=b.space.sleep_time_threshold if np.isfinite(b.space.sleep_time_threshold) else 'infinite',
                          latest_action=plain(b.latest_action),n_contacts=b.n_contact_points,
                          env_rng=rng_state(b.rng),audit_is_complete_contact_snapshot=False,
                          restoration='fresh_reset_and_full_replay')
        else:
            import mujoco
            p=b.env.physics
            integration=p.get_state(sig=int(mujoco.mjtState.mjSTATE_INTEGRATION))
            common.update(integration=plain(integration),task_rng=rng_state(b.env.task.random),
                          step_count=b.env._step_count,reset_next_step=b.env._reset_next_step,
                          cumulative_reward=b._cumulative_reward,physics_time=p.time(),
                          qacc_warmstart=plain(p.data.qacc_warmstart),ctrl=plain(p.data.ctrl),
                          qpos=plain(p.data.qpos),qvel=plain(p.data.qvel),
                          xfrc_applied=plain(p.data.xfrc_applied),qfrc_applied=plain(p.data.qfrc_applied))
        return plain(common)

    def reset(self):
        self.obs,self.info=self.env.reset(seed=self.row['seeds']['native_reset'],options={})
        self.clock=0; self.env.action_space.seed(self.row['seeds']['collector'])
        if self.task=='pusht': self.success=native_endpoint(self.task,self.coordinates(),self.base.goal_state)
        else: self.success=False  # the reviewed collection task has target_qpos=None
        self.terminated=self.truncated=False; self.stopped=self.success
        return self.pixels()

    def step(self,action):
        if self.stopped: raise ValueError('no post-stop physics')
        action=np.asarray(action)
        if action.shape!=(2,) or not np.isfinite(action).all(): raise ValueError('finite native action')
        # Native CEM decoding is intentionally not clipped. Collection alone is
        # constrained by its native collector; planning semantics are preserved.
        self.obs,reward,term,trunc,self.info=self.env.step(action)
        self.clock+=1
        self.success=native_endpoint(self.task,self.coordinates(),self.goal) if self.goal_installed else bool(term)
        self.terminated=bool(term); self.truncated=bool(trunc)
        if self.goal_installed and self.success!=bool(term): raise ValueError('independent native endpoint disagreement')
        self.stopped=self.success or self.terminated or self.truncated
        return self.pixels()

    def collector(self):
        import gymnasium as gym
        if self.task=='pusht':
            from stable_worldmodel.envs.pusht.expert_policy import WeakPolicy
            policy=WeakPolicy(dist_constraint=100,seed=self.row['seeds']['collector'])
            proxy=SimpleNamespace(envs=[self.env],spec=self.base.spec,action_space=gym.spaces.Box(-1.,1.,(1,2),dtype=np.float32))
            policy.set_env(proxy)
            return lambda: np.array(policy.get_action({})[0],copy=True),policy
        from stable_worldmodel.policy import RandomPolicy
        policy=RandomPolicy(seed=self.row['seeds']['collector']); policy.set_env(self.env)
        return lambda: np.array(policy.get_action({}),copy=True),policy

    def install_goal(self,goal_coordinates,goal_rgb):
        before=self.audit(); pixels=self.pixels()
        if self.stopped: raise ValueError('goal cannot resurrect a terminated collection replay')
        self.goal=np.array(goal_coordinates,copy=True)
        if self.task=='pusht':
            self.base._set_goal_state(self.goal.copy()); self.base._goal=np.array(goal_rgb,copy=True)
        else: self.base.set_target_qpos(self.goal.copy())
        if canonical(before)!=canonical(self.audit()) or not np.array_equal(pixels,self.pixels()):
            raise ValueError('goal installation changed dynamics/RNG/time/source pixels')
        self.goal_installed=True; self.success=native_endpoint(self.task,self.coordinates(),self.goal)
        self.stopped=self.success
        return {'dynamic_before_after':canonical(before),'source_pixels':array_id(pixels),'physics_steps':0,'world_serial':self.serial}

    def close(self):
        if self.env is not None: self.env.close()

def restore(record,arrays):
    world=NativeWorld(record['root'])
    try:
        pix=world.reset()
        for i in range(21):
            if array_id(pix)!=record['frames'][i]['pixels'] or canonical(world.audit())!=record['frames'][i]['audit']:
                raise ValueError('fresh reset/replay identity at '+str(i))
            if i<20: pix=world.step(arrays['actions'][i])
        goal=world.install_goal(arrays['coordinates'][44],arrays['pixels'][44])
        return world,goal
    except BaseException:
        world.close(); raise
