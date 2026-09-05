import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
from copy import deepcopy
import numpy as np
import pytest
from pusht_fresh_initialization import (fresh_type, validate_record,
                                       signed_velocity_space, OPTION)

@pytest.fixture
def record():
    # Synthetic API regression fixture, not an evaluation record.
    return {'state': [397, 336, 344, 318, .59, -6.4, 20.3],
            'goal_state': [325, 344, 291, 264, 1.05, 27, -33]}

@pytest.fixture
def native():
    from stable_worldmodel.envs.pusht.env import PushT
    return PushT

def test_validation_copies_and_defaults(record):
    out = validate_record(record)
    out['state'][0] = 0
    assert record['state'][0] == 397
    assert out['block_velocity'].tolist() == [0, 0]
    assert out['block_angular_velocity'] == 0

@pytest.mark.parametrize('change', [dict(state=[0]*6), dict(state=[0]*6+[float('nan')]),
                                   dict(made_up_cache=1), dict(proprio=[0]*4)])
def test_reject_invalid(record, change):
    with pytest.raises(ValueError): validate_record({**record, **change})

def test_no_step_accuracy_idempotence(native, record, monkeypatch):
    import pymunk
    env = fresh_type(native)()
    def forbidden(*a, **k): raise AssertionError('hidden physics step')
    monkeypatch.setattr(pymunk.Space, 'step', forbidden)
    a, _ = env.reset(options={OPTION: record}, seed=32)
    space = env.space
    pixels = env.render().copy()
    b, _ = env.reset(options={OPTION: record}, seed=33)
    assert env.space is not space
    np.testing.assert_array_equal(a['state'], record['state'])
    np.testing.assert_array_equal(a['state'], b['state'])
    np.testing.assert_array_equal(env.render(), pixels)
    assert env.block.velocity == (0, 0) and env.block.angular_velocity == 0
    assert type(env).step is native.step and type(env)._set_state is native._set_state
    env.close()

def test_recorded_optional_dynamics(native, record):
    env = fresh_type(native)()
    obs, _ = env.reset(options={OPTION: {**record, 'block_velocity':[2, -3],
        'block_angular_velocity':.2, 'block_force':[1, 2], 'block_torque':3}})
    assert env.block.velocity == (2, -3)
    assert env.block.angular_velocity == .2
    assert env.block.force == (1, 2) and env.block.torque == 3
    np.testing.assert_array_equal(obs['state'], record['state'])
    env.close()

def test_constructor_physics_overrides(native, record):
    env = fresh_type(native)(block_cog=(0, 30), damping=.7)
    env.reset(options={OPTION: record})
    assert env.block.center_of_gravity == (0, 30) and env.space.damping == .7
    env.close()

def test_legacy_delegation(native):
    old = native(); new = fresh_type(native)()
    a, _ = old.reset(seed=32); b, _ = new.reset(seed=32)
    for key in a: np.testing.assert_array_equal(a[key], b[key])
    np.testing.assert_array_equal(old.render(), new.render())
    for key in a:
        np.testing.assert_array_equal(old.step(np.array([.1, -.1]))[0][key],
                                      new.step(np.array([.1, -.1]))[0][key])
    old.close(); new.close()

def test_metadata_separate_nonmutating(native, record):
    env = fresh_type(native)()
    original = deepcopy(env.observation_space)
    a, _ = env.reset(options={OPTION: record})
    pixels = env.render().copy()
    corrected = signed_velocity_space(env.observation_space)
    for k, idx in [('state', [5, 6]), ('proprio', [2, 3])]:
        np.testing.assert_array_equal(env.observation_space[k].low, original[k].low)
        np.testing.assert_array_equal(corrected[k].high, original[k].high)
        assert (corrected[k].low[idx] == -512).all()
        assert corrected[k].dtype == original[k].dtype
        np.testing.assert_array_equal(signed_velocity_space(corrected)[k].low, corrected[k].low)
    env.observation_space = corrected
    b, _ = env.reset(options={OPTION: record})
    for k in a: np.testing.assert_array_equal(a[k], b[k])
    np.testing.assert_array_equal(pixels, env.render())
    assert env.observation_space.contains(b)
    env.close()

def test_rejection_preserves_current_physics(native, record):
    env = fresh_type(native)(); env.reset(options={OPTION: record})
    space = env.space; before = env._get_obs().copy()
    with pytest.raises(ValueError): env.reset(options={OPTION:{**record,'unknown':1}})
    assert env.space is space
    np.testing.assert_array_equal(env._get_obs(), before)
    env.close()
