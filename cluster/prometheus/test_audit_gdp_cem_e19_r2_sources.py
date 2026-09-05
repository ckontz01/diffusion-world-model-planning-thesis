from audit_gdp_cem_e19_r2_sources import audit_observation

def record(x): return {'values':x,'dtype':'float64','shape':[len(x)]}
def test_signed_velocity_explains_only_bound_violation():
    obs={'proprio':record([10,20,-3,4]),'state':record([10,20,30,40,1,-3,4])}
    result=audit_observation(obs,'e18')
    assert result['proprio']['below']==[2] and result['state']['below']==[5]
    assert all(x['signed_velocity_bounds_contains'] for x in result.values())
    assert all(x['native_contains'] for x in audit_observation(obs,'sage').values())

def test_bad_position_not_excused_by_velocity_bounds():
    obs={'proprio':record([-10,20,-3,4]),'state':record([-10,20,30,40,1,-3,4])}
    assert not any(x['signed_velocity_bounds_contains'] for x in audit_observation(obs,'e18').values())
