"""R2 passive setter localization; no production environment/model edits."""
from __future__ import annotations
import argparse
from copy import deepcopy
import inspect
import json
from pathlib import Path
import sys
import numpy as np
import gdp_cem_e19_r1 as r1

R1 = r1.ROOT / 'snapshots/gdp-cem-e19-r1-549757ef959a79ba'
PREP = r1.ROOT / 'experiments/gdp-cem-e19-r1/run-20260905-2c5ea97a/preparation/STIMULI.json'
PREP_SHA = '45ac71f23c4ff96df15a7eb2c019456c7847bec4cae3582c57dbefb8f085848a'
ENV_SHA = {'sage':'950265cb0bad2c1f14a2c959de35695a047f58a502f45d67b53749bf48364f6a',
           'e18':'d8d0de35aaab5b846db4e79b0fbfd6b17375178cce40a25df5301c8030ca6d68'}

def effective_seed(mode, received):
    if mode == 'native': return received
    if mode in ('seed32','seed33'): return int(mode[4:])
    raise ValueError(mode)

def observation_check(obs, space):
    result = {}
    for key, sub in space.spaces.items():
        value = np.asarray(obs[key])
        result[key] = dict(shape=list(value.shape), expected_shape=list(sub.shape),
            dtype=str(value.dtype), expected_dtype=str(sub.dtype), finite=bool(np.isfinite(value).all()),
            below=np.argwhere(value < sub.low).reshape(-1).tolist(),
            above=np.argwhere(value > sub.high).reshape(-1).tolist(),
            values=value.tolist(), low=sub.low.tolist(), high=sub.high.tolist(),
            contains=bool(sub.contains(value)))
    return result

def execute(out, stack, case_id, mode, repeat):
    import pymunk
    from stable_worldmodel.envs.pusht.env import PushT
    assert r1.sha(Path(r1.__file__)) == r1.sha(R1/'gdp_cem_e19_r1.py')
    assert r1.sha(PREP) == PREP_SHA
    assert r1.sha(inspect.getsourcefile(PushT)) == ENV_SHA[stack]
    assert case_id in (0,1) and repeat in (0,1)
    native_setter, native_reset, native_step = PushT._set_state, PushT.reset, pymunk.Space.step
    native_envstep = PushT.step
    lines, first = inspect.getsourcelines(native_setter)
    line_text = {first+i:line.strip() for i,line in enumerate(lines)}
    active = []
    events = []
    setter_count = 0
    reset_depth = 0
    def snapshot(env, stage, **extra):
        shapes = {}
        for name in ('agent','block'):
            shapes[name] = [dict(type=type(s).__name__, bb=list(s.bb),
                friction=s.friction, elasticity=s.elasticity, collision_type=s.collision_type,
                sensor=s.sensor) for s in getattr(env,name).shapes]
        own_rng = getattr(env,'rng',None)
        events.append(dict(stage=stage, physical=r1.encode(r1.physical(env,'pusht')),
            rng=r1.encode(r1.rngs(env)), own_rng=r1.encode(deepcopy(own_rng.bit_generator.state)) if own_rng is not None else None,
            variation=r1.encode(env.variation_space.value), shapes=r1.encode(shapes), **r1.encode(extra)))
    def traced_setter(env, state):
        nonlocal setter_count
        index=setter_count; setter_count+=1
        role='reset' if reset_depth else 'dataset'
        active.append((env,index,role))
        previous=sys.gettrace()
        snapshot(env,'setter_entry',setter=index,role=role,requested=np.asarray(state))
        previous_line=None
        def trace(frame,event,arg):
            nonlocal previous_line
            if frame.f_code is native_setter.__code__ and frame.f_locals.get('self') is env:
                if event in ('line','return'):
                    if previous_line is not None:
                        snapshot(env,'after_setter_line',setter=index,role=role,
                            line=previous_line,source=line_text.get(previous_line),
                            requested=np.asarray(frame.f_locals['state']))
                    previous_line=frame.f_lineno if event=='line' else None
                return trace
            return None
        try:
            sys.settrace(trace)
            result=native_setter(env,state)
        finally:
            sys.settrace(previous)
            active.pop()
        snapshot(env,'setter_return',setter=index,role=role,requested=np.asarray(state))
        return result
    def traced_space_step(space,dt):
        if not active: return native_step(space,dt)
        env,index,role=active[-1]
        assert space is env.space
        snapshot(env,'before_setter_physics',setter=index,role=role,dt=dt)
        result=native_step(space,dt)
        snapshot(env,'after_setter_physics',setter=index,role=role,dt=dt)
        return result
    def traced_reset(env,seed=None,options=None):
        nonlocal reset_depth
        supplied=seed; chosen=effective_seed(mode,seed)
        reset_depth+=1
        try: result=native_reset(env,seed=chosen,options=options)
        finally: reset_depth-=1
        snapshot(env,'native_reset_return',received_seed=supplied,effective_seed=chosen,
            observation_check=observation_check(result[0],env.observation_space))
        return result
    def traced_envstep(env,action):
        result=native_envstep(env,action)
        snapshot(env,'native_action_return',action=np.asarray(action),
            observation_check=observation_check(result[0],env.observation_space))
        return result
    PushT._set_state=traced_setter; PushT.reset=traced_reset
    PushT.step=traced_envstep; pymunk.Space.step=traced_space_step
    r1.STEPS=1
    try:
        r1.execute(PREP,out/'interface/TRACE.json',stack,case_id,repeat)
        interface=out/'interface/TRACE.json'; r1.verified(interface)
        payload=json.loads(interface.read_text())
        assert payload['steps']==1 and payload['fixed_return_calls']==1 and payload['stopped_at_cap']
        assert setter_count==3 and len([e for e in events if e['stage']=='before_setter_physics'])==3
        r1.seal(out/'localization/LOCALIZATION.json',dict(stack=stack,case_id=case_id,mode=mode,repeat=repeat,
            events=events,setter_calls=setter_count,post_restoration_steps=1,
            interface_path=str(interface),interface_sha256=r1.sha(interface),
            stimulus_sha256=PREP_SHA,env_source_sha256=ENV_SHA[stack],r1_source_sha256=r1.sha(r1.__file__),
            setter_source=''.join(lines),pymunk_version=pymunk.version,
            source_sha256=r1.sha(__file__),reset_seed_intervention=mode!='native',
            integration_functions_replaced=False,production_correction=False,
            planning=False,model_change=False,protected_read=False,confirmation_read=False))
    finally:
        PushT._set_state=native_setter; PushT.reset=native_reset; PushT.step=native_envstep
        pymunk.Space.step=native_step

def main():
    p=argparse.ArgumentParser(); p.add_argument('--output',type=Path,required=True)
    p.add_argument('--stack',choices=['sage','e18'],required=True)
    p.add_argument('--case',type=int,choices=[0,1],required=True)
    p.add_argument('--mode',choices=['native','seed32','seed33'],required=True)
    p.add_argument('--repeat',type=int,choices=[0,1],required=True)
    a=p.parse_args(); assert r1.ROOT/'experiments/gdp-cem-e19-r2' in a.output.resolve().parents
    r1.torch.set_num_threads(4)
    execute(a.output,a.stack,a.case,a.mode,a.repeat)
if __name__=='__main__': main()
