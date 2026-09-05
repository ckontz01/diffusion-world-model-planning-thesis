import numpy as np
import pytest
import torch
from gdp_cem_e19_r1 import choose,encode,digest,FixedReturn,STEPS

def test_candidate_selection_is_index_only():
    candidates=torch.arange(1*3*3*10,dtype=torch.float32).reshape(1,3,3,10)
    b={'candidates':candidates,'costs':torch.tensor([[99.,0.,-99.]])}
    i,a,label,_=choose(b,0,2)
    assert i==0 and a.shape==(15,2) and label=='fixed diagnostic action stimulus'

def test_eligibility_fallback():
    a=torch.ones(1,3,3,10); a[:,0]=float('nan'); a[:,2,0,0]=2
    i,*_=choose({'candidates':a},0,2)
    assert i==2

def test_no_valid_stimulus_stops():
    with pytest.raises(ValueError): choose({'candidates':torch.zeros(1,2,3,10)},0,2)

def test_prior_top_no_fallback():
    b={'top_actions':torch.zeros(1,3,10),'candidates':torch.randn(1,2,3,10)}
    with pytest.raises(ValueError): choose(b,0,2)

def test_top_source_label_and_exact_values():
    a=torch.arange(30).reshape(1,3,10).float()
    i,v,label,_=choose({'top_actions':a},0,2)
    assert i is None and torch.equal(v,a.reshape(15,2))
    assert label=='saved historical planner output'

def test_array_identity_retains_dtype():
    assert digest(np.ones(2,dtype='float32'))!=digest(np.ones(2,dtype='float64'))
    assert encode(float('inf'))=={'nonfinite':'inf'}

def test_fixed_return_never_replans():
    x=torch.arange(30).float().reshape(1,3,10); s=FixedReturn(x)
    assert torch.equal(s.solve({})['actions'],x)
    with pytest.raises(RuntimeError): s.solve({})

def test_cap_is_fifteen(): assert STEPS==15
