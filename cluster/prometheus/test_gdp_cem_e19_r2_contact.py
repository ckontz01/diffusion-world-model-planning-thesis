import numpy as np
import pytest
from gdp_cem_e19_r2_contact import reset_geometry

def trace(velocity=0):
    b={body:{k:{'values':v} for k,v in {'position':[10,20],'angle':.5,
        'velocity':[velocity,0],'angular_velocity':0,'force':[0,0],'torque':0}.items()} for body in ('agent','block')}
    return {'events':[{'stage':'after_reset','physical':{'bodies':b}}]}
def test_geometry_uses_recorded_pose():
    np.testing.assert_equal(reset_geometry(trace()),[10,20,10,20,.5,0,0])
def test_nonzero_unrepresented_dynamics_rejected():
    with pytest.raises(AssertionError):reset_geometry(trace(2))
