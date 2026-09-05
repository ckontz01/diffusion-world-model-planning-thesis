import numpy as np
import pytest
from analyze_gdp_cem_e19_r2 import event,requested_checks,center_of_mass

def test_stage_ambiguity_rejected():
    with pytest.raises(AssertionError): event({'events':[{'stage':'x'},{'stage':'x'}]},'x')

def test_role_selection():
    t={'events':[{'stage':'x','role':'reset'},{'stage':'x','role':'dataset'}]}
    assert event(t,'x','dataset')['role']=='dataset'

def test_assigned_fields_are_separate_from_block_velocity():
    e={'physical':{'bodies':{'agent':{'position':[1,2],'velocity':[6,7]},
                           'block':{'position':[3,4],'angle':5,'velocity':[99,99]}}}}
    assert all(v['exact'] for v in requested_checks(e,np.arange(1,8)).values())

def test_com_not_same_as_origin_when_rotated():
    b={'position':[1,2],'angle':np.pi/2,'center_of_gravity':[3,0]}
    np.testing.assert_allclose(center_of_mass(b),[1,5])
