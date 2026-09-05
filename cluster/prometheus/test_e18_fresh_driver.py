"""Technical driver contracts with a tiny deterministic policy, no benchmark."""
from copy import deepcopy
from types import SimpleNamespace
import numpy as np
import pytest
from e18_fresh_driver import FreshEpisode, complete_slots, computational_info
from pusht_fresh_initialization import register


class Policy:
    def __init__(self):
        self.planner=SimpleNamespace(diagnostic_history=[])
    def set_env(self,env):
        self.env=env;self._stage_index=0;self._action_buffer=[]
    def get_action(self,info):
        return np.zeros((1,2),dtype=np.float32)


@pytest.fixture
def record():
    return {'state':np.array([120.,120.,250.,250.,.5,-1.,2.]),
            'goal_state':np.array([450.,450.,400.,400.,1.,0.,0.])}


@pytest.fixture
def world():
    import stable_worldmodel as swm
    w=swm.World(register(),num_envs=1,image_shape=(32,32),max_episode_steps=300,
                correct_velocity_space=True)
    yield w
    w.close()


def test_explicit_reset_without_steps_and_budget(world,record,monkeypatch):
    import pymunk
    calls=[];original=pymunk.Space.step
    def step(s,dt):calls.append(dt);return original(s,dt)
    monkeypatch.setattr(pymunk.Space,'step',step)
    episode=FreshEpisode(world,lambda h,s:Policy())
    with pytest.raises(RuntimeError):episode.advance()
    episode.start(record,horizon=75,budget=2,seed=123)
    assert calls==[]
    with pytest.raises(RuntimeError):episode.start(record,horizon=75,budget=2,seed=123)
    assert not episode.advance()
    assert episode.advance()
    assert len(calls)==20
    with pytest.raises(RuntimeError):episode.advance()
    episode.start(record,horizon=75,budget=2,seed=123)
    assert len(calls)==20
    np.testing.assert_allclose(world.infos['state'][0,-1],record['state'],rtol=0,atol=1e-10)
    assert not world.terminateds.any() and not world.truncateds.any()


@pytest.mark.parametrize('flag',[2,3])
def test_natural_and_wrapper_termination(world,record,flag,monkeypatch):
    native=world.envs.step;calls=[]
    def step(action):
        calls.append(1);out=list(native(action));out[flag]=np.ones(1,dtype=bool);return tuple(out)
    monkeypatch.setattr(world.envs,'step',step)
    episode=FreshEpisode(world,lambda h,s:Policy())
    episode.start(record,horizon=75,budget=31,seed=7)
    complete_slots([episode])
    assert episode.steps==1 and len(calls)==1
    with pytest.raises(RuntimeError):episode.advance()


def test_no_silent_legacy(world,record,monkeypatch):
    episode=FreshEpisode(world,lambda h,s:Policy())
    monkeypatch.setattr(world.envs.envs[0].unwrapped,'queue_instantaneous_record',None)
    with pytest.raises(RuntimeError,match='no legacy fallback'):
        episode.start(record,horizon=75,budget=1,seed=7)


def test_reused_solver_rejected(world,record):
    p=Policy();e=FreshEpisode(world,lambda h,s:p)
    e.start(record,horizon=75,budget=1,seed=7);e.advance()
    with pytest.raises(RuntimeError,match='new policy and solver'):
        e.start(record,horizon=75,budget=1,seed=7)


def test_bad_action_failure_has_no_retry(world,record):
    p=Policy();p.get_action=lambda info:np.full((1,2),np.nan)
    e=FreshEpisode(world,lambda h,s:p)
    e.start(record,horizon=75,budget=1,seed=7)
    with pytest.raises(RuntimeError,match='invalid decoded'):e.advance()
    assert e.status=='failed' and e.steps==0
    with pytest.raises(RuntimeError):e.start(record,horizon=75,budget=1,seed=7)


def test_computational_inputs_drop_unused():
    a=dict(pixels=np.zeros((1,1,3,3,3)),goal=np.ones((1,1,3,3,3)),state=np.ones((1,1,7)),
           proprio=np.full((1,1,4),np.nan),action=np.full((1,1,2),np.nan))
    assert set(computational_info(a))=={'pixels','goal','state'}
    with pytest.raises(RuntimeError):computational_info({'state':a['state']})


def test_coordinator_heterogeneous_endings():
    class Slot:
        def __init__(self,limit):self.status='running';self.steps=0;self.limit=limit
        def advance(self):
            assert self.status=='running';self.steps+=1
            if self.steps==self.limit:self.status='done'
    slots=[Slot(1),Slot(4),Slot(2)];complete_slots(slots)
    assert [s.steps for s in slots]==[1,4,2]
    with pytest.raises(RuntimeError):complete_slots(slots)


def test_r3_initializer_unchanged():
    import hashlib
    from pathlib import Path
    path=Path(__file__).with_name('pusht_fresh_initialization.py')
    assert hashlib.sha256(path.read_bytes()).hexdigest()=='798bb6749dd30b9c6a91ac7018422edbefd356f3bb6bc322bd8ca95987506a65'
