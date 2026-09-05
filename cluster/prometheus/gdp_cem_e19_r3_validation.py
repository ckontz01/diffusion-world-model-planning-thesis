"""R3 exposed-record engineering checks. Never compute/store benchmark metrics."""
import argparse
from copy import deepcopy
import inspect
import json
from pathlib import Path
import numpy as np
import gdp_cem_e19_r1 as r1
from pusht_fresh_initialization import fresh_type, OPTION, signed_velocity_space

R1_RUN = r1.ROOT/'experiments/gdp-cem-e19-r1/run-20260905-2c5ea97a'
PREP = R1_RUN/'preparation/STIMULI.json'
ENV_SHA = {'sage':'950265cb0bad2c1f14a2c959de35695a047f58a502f45d67b53749bf48364f6a',
           'e18':'d8d0de35aaab5b846db4e79b0fbfd6b17375178cce40a25df5301c8030ca6d68'}

def values(v): return np.asarray(v['values'], dtype=np.float64)

def inputs(stack):
    r1.verified(PREP)
    assert r1.sha(PREP) == '45ac71f23c4ff96df15a7eb2c019456c7847bec4cae3582c57dbefb8f085848a'
    prep = json.loads(PREP.read_text())
    result = []
    for cid in range(3):
        traces=[]; hashes={}
        for repeat in range(2):
            path=R1_RUN/f'{stack}/case-{cid}/repeat-{repeat}/TRACE.json'
            hashes[str(path)] = r1.verified(path)
            traces.append(json.loads(path.read_text()))
        e = next(x for x in traces[0]['events'] if x['stage']=='dataset_endpoints')
        fields=e['endpoints'][0]
        expected = {'action','pixels','proprio','state'} | ({'episode_idx','step_idx'} if stack=='e18' else set())
        assert set(e['columns']) == expected and set(fields) == expected
        record={'state':values(fields['state']['first']), 'goal_state':values(fields['state']['last']),
                'proprio':values(fields['proprio']['first'])}
        histories=[]
        for trace in traces:
            b=next(x for x in trace['events'] if x['stage']=='after_reset')['physical']['bodies']
            histories.append(np.r_[values(b['agent']['position']), values(b['block']['position']),
                                   values(b['block']['angle']), values(b['agent']['velocity'])])
        result.append(dict(case_id=cid,record=record,histories=histories,
            actions=np.asarray(prep['cases'][cid]['physical'],dtype=np.float32)[:3],
            identity={k:prep['cases'][cid][k] for k in ('episode','start','manifest_row','sentinel_id')},
            columns=sorted(expected),input_sha256=hashes,
            absent=['block_velocity','block_angular_velocity','forces','torques','contact_cache','controller_memory']))
    return result

def physical(env):
    result={}
    for name in ('agent','block'):
        body=getattr(env,name)
        result[name]={k:np.asarray(getattr(body,k)) for k in ('position','angle','velocity','angular_velocity','force','torque')}
    return result

def physics_config(env):
    shapes=[]
    for shape in env.space.shapes:
        body=shape.body
        geometry={k:np.asarray(getattr(shape,k)) for k in ('radius','offset','a','b') if hasattr(shape,k)}
        if hasattr(shape,'get_vertices'): geometry['vertices']=np.asarray(shape.get_vertices())
        shapes.append(r1.encode(dict(type=type(shape).__name__, geometry=geometry,
            friction=shape.friction,elasticity=shape.elasticity,sensor=shape.sensor,
            collision_type=shape.collision_type,filter=list(shape.filter),
            body_type=body.body_type,mass=body.mass,moment=body.moment,cog=np.asarray(body.center_of_gravity))))
    return dict(shapes=sorted(shapes,key=lambda v:json.dumps(v,sort_keys=True)),
        space={k:np.asarray(getattr(env.space,k)) for k in ('gravity','damping','iterations','collision_slop','collision_bias','collision_persistence')},
        control={k:getattr(env,k) for k in ('dt','control_hz','k_p','k_v','action_scale','relative')})

def check_start(env, record, obs):
    requested=np.asarray(record['state'])
    np.testing.assert_array_equal(env._get_obs(),requested)
    np.testing.assert_array_equal(obs['state'],requested)
    np.testing.assert_array_equal(obs['proprio'],requested[[0,1,5,6]])
    np.testing.assert_array_equal(env.goal_state,record['goal_state'])
    np.testing.assert_array_equal(env.goal_pose,record['goal_state'][2:5])
    assert env.block.velocity == (0,0) and env.block.angular_velocity == 0
    assert env.agent.angular_velocity == 0
    for name in ('agent','block'):
        body=getattr(env,name)
        assert body.force == (0,0) and body.torque == 0
        arbs=[]; body.each_arbiter(lambda a:arbs.append(1)); assert not arbs
        for shape in body.shapes:
            cached=tuple(shape.bb)
            assert tuple(shape.cache_bb()) == cached  # public cache recomputation is already current
            assert not shape.sensor
    assert env.latest_action is None and env.n_contact_points == 0

def run(stack, out):
    import pymunk
    from stable_worldmodel.envs.pusht.env import PushT
    assert r1.sha(inspect.getsourcefile(PushT)) == ENV_SHA[stack]
    cls=fresh_type(PushT)
    assert cls.step is PushT.step and cls._set_state is PushT._set_state
    records=inputs(stack)  # inventory before simulation
    r1.seal(out/'inventory/INVENTORY.json',dict(stack=stack,cases=records,only_exposed=True))
    rows=[]; native_step=pymunk.Space.step; calls=[]
    def count(space, dt): calls.append(dt); return native_step(space,dt)
    pymunk.Space.step=count
    try:
        for case in records:
            for history in ('seed32','seed33','r1r0','r1r1'):
                for repeat in (0,1):
                    env=cls()
                    env.reset(seed=int(history[4:]) if history.startswith('seed') else 32)
                    if history.startswith('r1'): env._set_state(case['histories'][int(history[-1])])
                    history_state=r1.encode(physical(env))
                    original_config=r1.digest(physics_config(env))
                    old_space=env.space
                    before=len(calls)
                    obs,_=env.reset(seed=32+repeat,options={OPTION:case['record']})
                    assert len(calls)==before and env.space is not old_space
                    check_start(env,case['record'],obs)
                    assert r1.digest(physics_config(env)) == original_config
                    initial=r1.digest(physical(env)); pixels=r1.digest(env.render()); goal=r1.digest(env._goal)
                    # Separate metadata-only intervention; pixels and native observations invariant.
                    env.observation_space=signed_velocity_space(env.observation_space)
                    obs2,_=env.reset(seed=None,options={OPTION:case['record']})
                    assert len(calls)==before
                    check_start(env,case['record'],obs2)
                    assert initial==r1.digest(physical(env)) and pixels==r1.digest(env.render())
                    assert goal==r1.digest(env._goal) and env.observation_space.contains(obs2)
                    trajectory=[]
                    for action in case['actions']:
                        observation, _, _, _, _ = env.step(action.copy())
                        assert all(np.isfinite(v).all() for v in observation.values())
                        trajectory.append(dict(physical=r1.digest(physical(env)),obs=r1.digest(observation),
                            pixels=r1.digest(env.render())))
                    assert len(calls)-before == 3*int(1/(env.dt*env.control_hz))
                    rows.append(dict(case_id=case['case_id'],history=history,repeat=repeat,
                        actual_history=history_state,initial=initial,pixels=pixels,goal=goal,
                        trajectory=trajectory,config=original_config,hidden_steps=0,
                        initialization_passed=True,metadata_value_invariant=True))
                    env.close()
    finally: pymunk.Space.step=native_step
    for cid in range(3):
        group=[r for r in rows if r['case_id']==cid]
        assert len(group)==8
        for field in ('initial','pixels','goal','trajectory','config'):
            assert len({r1.digest(r[field]) for r in group})==1, (cid,field)
    assert len(rows)==24
    r1.seal(out/'validation/VALIDATION.json',dict(stack=stack,all_passed=True,rows=rows,
        native_source_sha256=ENV_SHA[stack],scenarios=24,fresh_resets=48,primitive_actions=72,
        physics_step_calls=len(calls),fresh_initialization_physics_steps=0,
        planning=False,performance_metric_recorded=False,protected_read=False,holdout_read=False,
        historical_results_modified=False,complete_historical_state_recovery=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stack',choices=['sage','e18'],required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert r1.ROOT/'experiments/gdp-cem-e19-r3' in a.output.resolve().parents
    r1.torch.set_num_threads(4);run(a.stack,a.output)
