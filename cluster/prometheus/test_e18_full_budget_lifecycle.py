"""Full-budget driver + actual scheduled-policy regression, never an efficacy test.

The solver is deterministic and model-free. Only this test suppresses terminal
flags so every chunk is exercised. Physics, accepted initializer and driver are
not changed. The separate timing probe exercises the real delta=15 solver.
"""
from copy import deepcopy
import numpy as np
import pytest
import torch
from e18_fresh_driver import FreshEpisode, complete_slots
from gdp_cem_e18_runtime import E18ScheduledPolicy
from pusht_fresh_initialization import register


class Solver:
    device = torch.device('cpu')
    primitive_action_dim = 2

    def __init__(self):
        self.diagnostic_history=[]

    def configure(self, *, action_space, n_envs):
        assert n_envs==1 and action_space.shape==(1,2)

    def solve(self, info, *, raw_state, delta_value, tau_value):
        assert tau_value==15 and raw_state.shape==(1,7)
        assert np.isfinite(raw_state.numpy()).all()
        self.diagnostic_history.append((delta_value,tau_value))
        # Distinct chunks and within-chunk actions expose off-by-one delivery.
        base=len(self.diagnostic_history)/1000
        actions=torch.arange(30,dtype=torch.float32).reshape(1,15,2)/10000+base
        return {'actions':actions}


@pytest.mark.parametrize('horizon',[75,150])
@pytest.mark.parametrize('nslots',[1,3])
def test_complete_two_cycles_then_fresh_episode(horizon,nslots,monkeypatch):
    import stable_worldmodel as swm
    worlds=[];slots=[];deliveries=[]
    record=dict(state=np.array([120.,120.,250.,250.,.5,-1.,2.]),
                goal_state=np.array([450.,450.,400.,400.,1.,0.,0.]))
    def factory(h,seed):
        return E18ScheduledPolicy(Solver(),schedule=(15,)*(h//15),
            environment_budget=2*h,state_key='state',process={},transform={})
    try:
        for i in range(nslots):
            w=swm.World(register(),num_envs=1,image_shape=(32,32),
                max_episode_steps=1000,correct_velocity_space=True)
            worlds.append(w);received=[];deliveries.append(received)
            native=w.envs.step
            def controlled(action,native=native,received=received):
                received.append(action.copy());out=list(native(action))
                out[2]=np.zeros(1,dtype=bool);out[3]=np.zeros(1,dtype=bool)
                return tuple(out)
            monkeypatch.setattr(w.envs,'step',controlled)
            slots.append(FreshEpisode(w,factory))
        for repeat in range(2):
            for slot in slots:
                slot.start(deepcopy(record),horizon=horizon,budget=2*horizon,seed=932)
            complete_slots(slots)
            expected=[(d,15) for d in range(horizon,0,-15)]*2
            for slot in slots:
                assert slot.steps==2*horizon and slot.status=='done'
                assert slot.policy.planner.diagnostic_history==expected
                assert slot.policy._stage_index==2*horizon//15
                assert not slot.policy._action_buffer
                with pytest.raises(RuntimeError):slot.advance()
                with pytest.raises(RuntimeError,match='schedule exhausted'):
                    slot.policy.get_action(slot.world.infos)
        for received in deliveries:
            assert len(received)==4*horizon
            np.testing.assert_array_equal(received[:2*horizon],received[2*horizon:])
            for call in range(2*horizon//15):
                expected=(torch.arange(30,dtype=torch.float32).reshape(15,1,2)/10000+(call+1)/1000).numpy()
                np.testing.assert_array_equal(received[15*call:15*(call+1)],expected)
        for received in deliveries[1:]:np.testing.assert_array_equal(received,deliveries[0])
    finally:
        for w in worlds:w.close()
