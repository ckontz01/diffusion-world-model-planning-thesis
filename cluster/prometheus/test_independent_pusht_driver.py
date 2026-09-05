"""Full-budget common-driver tests, using deterministic model-free actions."""
import numpy as np
import pytest
import torch
from independent_pusht_evaluate import evaluate_one
from independent_pusht_runtime import Decoder
from independent_pusht_design import LOOKS,ALPHAS

def test_alpha_budget():
    assert abs(sum(ALPHAS)*3-.05)<1e-14
    assert LOOKS==(1600,3200,6000)

def test_decoder_standard_scaler_identity():
    from sklearn.preprocessing import StandardScaler
    dec=Decoder([-.007812564379916172,.006860687229453032],[.20846744284501714,.20674862637362224])
    old=StandardScaler();old.mean_=dec.mean_.copy();old.scale_=dec.scale_.copy();old.n_features_in_=2
    x=np.random.default_rng(17).normal(size=(100,2)).astype(np.float32)
    np.testing.assert_array_equal(dec.inverse_transform(x),old.inverse_transform(x.copy()))

@pytest.mark.parametrize('horizon',[75,150])
def test_common_full_budget_and_fresh_episode(horizon,monkeypatch):
    import stable_worldmodel as swm
    from gdp_cem_e18_runtime import E18ScheduledPolicy
    from pusht_fresh_initialization import register
    for method in ('synchronize','reset_peak_memory_stats'):
        monkeypatch.setattr(torch.cuda,method,lambda:None)
    monkeypatch.setattr(torch.cuda,'max_memory_allocated',lambda:0)
    solvers=[]
    class Tiny:
        device=torch.device('cpu');primitive_action_dim=2
        def __init__(self): self.calls=[]
        def configure(self,**kw):pass
        def solve(self,info,*,raw_state,delta_value,tau_value):
            self.calls.append((delta_value,tau_value))
            return {'actions':torch.full((1,3,10),.001*len(self.calls))}
    def factory(h,seed):
        solver=Tiny();solvers.append(solver)
        return E18ScheduledPolicy(solver,schedule=tuple([15]*(h//15)),environment_budget=2*h,
                                  state_key='state',process={},transform={})
    w=swm.World(register(),num_envs=1,image_shape=(32,32),max_episode_steps=300,correct_velocity_space=True,verbose=0)
    original=w.envs.step
    def full(action):
        result=list(original(action));result[2]=np.zeros(1,bool);result[3]=np.zeros(1,bool);return tuple(result)
    monkeypatch.setattr(w.envs,'step',full)
    record={'state':np.array([120.,120.,250.,250.,.5,0.,0.]),
            'goal_state':np.array([450.,450.,400.,400.,1.,0.,0.])}
    try:
        first,trace=evaluate_one(w,factory,record,horizon,32,'vad_greedy_300')
        second,trace2=evaluate_one(w,factory,record,horizon,32,'vad_greedy_300')
        assert first['failure'] is None and first['delivered']==2*horizon
        assert second['failure'] is None and second['delivered']==2*horizon
        assert solvers[0] is not solvers[1]
        assert solvers[0].calls==[(d,15) for d in range(horizon,0,-15)]*2
        for k in trace:np.testing.assert_array_equal(trace[k],trace2[k])
    finally:w.close()
