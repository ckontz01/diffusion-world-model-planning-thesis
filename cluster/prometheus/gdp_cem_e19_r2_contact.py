"""Isolated native setter contact reconstruction from preserved R1 geometry."""
from copy import deepcopy
import argparse
import inspect
import json
from pathlib import Path
import numpy as np
import gdp_cem_e19_r1 as r1
from gdp_cem_e19_r2 import ENV_SHA

def values(x): return np.asarray(x['values'])
def reset_geometry(trace):
    e=next(e for e in trace['events'] if e['stage']=='after_reset')
    b=e['physical']['bodies']
    for body in ('agent','block'):
        for key in ('velocity','angular_velocity','force','torque'):
            assert np.all(values(b[body][key])==0),(body,key)
    return np.r_[values(b['agent']['position']),values(b['block']['position']),
                 values(b['block']['angle']),values(b['agent']['velocity'])]

def execute(out,stack,geometry,repeat):
    import pymunk
    from stable_worldmodel.envs.pusht.env import PushT
    assert r1.sha(inspect.getsourcefile(PushT))==ENV_SHA[stack]
    if stack=='sage':
        from sage.eval.pusht import set_determinism
        set_determinism(32)
    else:
        from gdp_cem_e18_specs import derived_seed
        seed=derived_seed('planner|task=pusht|h=75|replicate=1|shard=0')
        np.random.seed(seed%(2**32)); r1.torch.manual_seed(seed)
    cid=1 if stack=='sage' else 0
    old=r1.ROOT/f'experiments/gdp-cem-e19-r1/run-20260905-2c5ea97a/{stack}/case-{cid}/repeat-{geometry}/TRACE.json'
    r1.verified(old); trace=json.loads(old.read_text()); prime=reset_geometry(trace)
    target=values(next(e for e in trace['events'] if e['stage']=='after_hook:_set_state')['kwargs']['state'])
    env=PushT(render_mode='rgb_array',resolution=224)
    events=[]; phase='reset'; count=0; native=pymunk.Space.step
    def snapshot(stage,**extra):
        events.append(dict(stage=stage,phase=phase,physical=r1.encode(r1.physical(env,'pusht')),
            rng=r1.encode(r1.rngs(env)),**r1.encode(extra)))
    def step(space,dt):
        nonlocal count
        assert space is env.space
        snapshot('before_physics',physics_index=count,dt=dt)
        result=native(space,dt)
        snapshot('after_physics',physics_index=count,dt=dt)
        count+=1; return result
    pymunk.Space.step=step
    try:
        env.reset(seed=32)
        snapshot('neutral_reset')
        phase='geometry_prime'; env._set_state(prime)
        snapshot('primed',requested=prime)
        phase='dataset_restore'; env._set_state(target)
        snapshot('restored',requested=target)
        assert count==4
        r1.seal(out/'CONTACT.json',dict(stack=stack,case_id=cid,geometry_repeat=geometry,repeat=repeat,
            old_trace_path=str(old),old_trace_sha256=r1.sha(old),events=events,physics_steps=count,
            primitive_actions=0,reset_seed=32,source_sha256=r1.sha(__file__),env_sha256=ENV_SHA[stack],
            pymunk_version=pymunk.version,chipmunk_version=pymunk.chipmunk_version,
            goal_or_model_inference=False,production_correction=False,protected_read=False,
            historical_reset_rng_reconstructed=False))
    finally:
        pymunk.Space.step=native; env.close()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--stack',choices=['sage','e18'],required=True)
    p.add_argument('--geometry',type=int,choices=[0,1],required=True)
    p.add_argument('--repeat',type=int,choices=[0,1],required=True)
    a=p.parse_args();assert r1.ROOT/'experiments/gdp-cem-e19-r2' in a.output.resolve().parents
    execute(a.output,a.stack,a.geometry,a.repeat)
