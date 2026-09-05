import numpy as np
import pytest
from gdp_cem_e19_r2 import effective_seed, observation_check

@pytest.mark.parametrize('value',[None,7])
def test_native_seed_unchanged(value):
    assert effective_seed('native',value)==value

@pytest.mark.parametrize('mode,expected',[('seed32',32),('seed33',33)])
def test_explicit_intervention(mode,expected):
    assert effective_seed(mode,None)==expected

def test_unknown_seed_mode_rejected():
    with pytest.raises(ValueError): effective_seed('search',None)

def test_negative_velocity_classification():
    from gymnasium import spaces
    box=spaces.Dict({'state':spaces.Box(0,512,shape=(7,),dtype=np.float64)})
    obs={'state':np.array([1.,2.,3.,4.,.5,-2.,3.])}
    result=observation_check(obs,box)['state']
    assert result['below']==[5] and result['above']==[] and result['finite']
    assert not result['contains']
