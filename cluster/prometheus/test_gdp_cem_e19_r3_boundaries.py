from copy import deepcopy
import numpy as np
import pytest
from gdp_cem_e19_r3_arms import batch_row, capture_boundary
from pusht_fresh_initialization import reset_world

def test_capture_stops_before_solver_and_restores_method():
    class Policy:
        def _prepare_info(self, data): return {k:2*v for k,v in data.items()}
        def get_action(self, data):
            self._prepare_info(data)
            raise AssertionError('solver must not be reached')
    p=Policy(); original=p._prepare_info
    cap=capture_boundary(p,{'state':np.array([1,2])})
    np.testing.assert_array_equal(cap['raw']['state'],[1,2])
    np.testing.assert_array_equal(cap['prepared']['state'],[2,4])
    assert p._prepare_info==original

def test_batch_rows_keep_call_provenance_not_slot_identity():
    payload={'state':np.ones((3,1,7)), '_plan_call':np.array([0,1,2]),
             '_env_id':np.arange(3)}
    row=batch_row(payload,1,3)
    assert row['_plan_call']==1 and '_env_id' not in row
    assert row['state'].shape==(1,7)

def test_reset_world_rejects_all_records_before_queuing():
    class Env:
        unwrapped=None
        def __init__(self):self.unwrapped=self;self.queued=[]
        def queue_instantaneous_record(self,record):self.queued.append(record)
    class Pool:envs=[Env(),Env()]
    class World:envs=Pool()
    good={'state':[1,2,3,4,.5,0,0],'goal_state':[1,2,3,4,.5,0,0]}
    with pytest.raises(ValueError):reset_world(World(),[good,dict(good,unknown=1)])
    assert all(not e.queued for e in World.envs.envs)

def test_world_interface_uses_actual_wrapped_reset():
    import stable_worldmodel as swm
    from pusht_fresh_initialization import register
    world=swm.World(register(),num_envs=3,image_shape=(224,224),max_episode_steps=20,
                    correct_velocity_space=True)
    try:
        records=[{'state':[397+i,336,344,318,.59,-6.4,20.3],
                  'goal_state':[325,344,291,264,1.05,27,-33]} for i in range(3)]
        reset_world(world,records,seed=32)
        for i,r in enumerate(records):
            np.testing.assert_array_equal(world.infos['state'][i,-1],r['state'])
    finally:world.close()
