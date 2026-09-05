"""Collector invariants; no learned planner or benchmark outcomes."""
import numpy as np
from independent_pusht_collect import seed_for, weak_action, make_reference

def test_separate_streams():
    assert seed_for('pilot',0,'collector')==seed_for('pilot',0,'collector')
    assert len({seed_for(n,i,p) for n in ('pilot','final') for i in range(20) for p in ('collector','initial')})==80

def test_action_native_formula_and_bounds():
    state=np.array([123,400,210,320,1.2,0,0.],float)
    r=np.random.default_rng(2);q=np.random.default_rng(2)
    for _ in range(100):
        a=weak_action(state,r)
        b=np.clip((np.clip(q.uniform(-1,1,2)*100+state[:2],state[2:4]-100,state[2:4]+100)-state[:2])/100,-1,1).astype(np.float32)
        np.testing.assert_array_equal(a,b);assert np.isfinite(a).all() and (abs(a)<=1).all()

def test_reference_repeat_and_witness():
    from stable_worldmodel.envs.pusht.env import PushT
    from pusht_fresh_initialization import fresh_type, OPTION
    for i in range(30):
        a,why=make_reference(i,'collector-unit',steps=150)
        if a is not None: break
    else: raise AssertionError('no valid synthetic start')
    b,why2=make_reference(i,'collector-unit',steps=150)
    assert why2 is None
    for key in a: np.testing.assert_array_equal(a[key],b[key])
    for h in (75,150):
        env=fresh_type(PushT)(correct_velocity_space=True)
        try:
            env.reset(options={OPTION:{'state':a['initial_request'], 'goal_state':a['states'][h]}})
            for t,action in enumerate(a['actions'][:h]):
                obs,*_=env.step(action)
                np.testing.assert_allclose(obs['state'],a['states'][t+1],rtol=0,atol=1e-10)
            assert env.eval_state(a['states'][h],env._get_obs())[0]
        finally: env.close()


def test_collection_validator_uses_exact_request(tmp_path):
    from independent_pusht_collect import collect
    from validate_independent_pusht_collection import validate
    path=tmp_path/'collection'
    collect(path,'pilot-validation-test',3,100)
    result=validate(path,expected=3,witnesses=3,expected_namespace='pilot-validation-test')
    assert result['all_passed'] and result['witness_goal_replays']==6
