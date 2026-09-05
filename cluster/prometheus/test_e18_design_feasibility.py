"""Planning arithmetic/metadata regressions. No training or prospective data."""
import json
from pathlib import Path
import numpy as np
import pytest
from e18_design_power import historical,fit_distribution,trial,SUPPORT
from e18_design_workload import calculate

BASE=Path(__file__).with_name('e18-design-feasibility-evidence')


def test_historical_complete_episode_pairing():
    d=json.loads((BASE/'metadata-v3/historical.json').read_text())
    h=historical(d)
    assert h['n_episodes']==12 and h['outcome_rows']==360
    np.testing.assert_allclose(h['mean'],[1/9,1/9])
    np.testing.assert_allclose(h['covariance'],[[.0723905723905724,.0521885521885522],
                                             [.0521885521885522,.1026936026936027]])
    d['rows'].pop()
    with pytest.raises(AssertionError):historical(d)


def test_support_has_shared_treatment_binary_representation():
    for d1,d2 in np.round(6*SUPPORT).astype(int):
        assert any(0<=t-d1<=6 and 0<=t-d2<=6 for t in range(7))


def test_moment_fit_and_zero_difference_no_rejection():
    mean=np.array([.05,.05]);cov=np.array([[.15,.07],[.07,.2]])
    support,p,residual=fit_distribution(mean,cov)
    np.testing.assert_allclose(p@support,mean,atol=1e-7)
    np.testing.assert_allclose((support-mean).T@(p[:,None]*(support-mean)),cov,atol=1e-7)
    rejection,_=trial(82,np.array([[0.,0.]]),np.ones(1),np.random.default_rng(1),100)
    assert not rejection.any()
    # The +5pp value is NOT an observed estimate gate: a precise +1pp rejects.
    rejection,_=trial(82,np.array([[.01,.01]]),np.ones(1),np.random.default_rng(1),100)
    assert rejection.all()


def test_null_familywise_check_with_monte_carlo_slack():
    s,p,_=fit_distribution([0,0],np.diag([.1,.2]))
    rejection,_=trial(82,s,p,np.random.default_rng(13),10000)
    assert .03<rejection.any(1).mean()<.065


def test_metadata_budget_and_exposure_accounting():
    d=json.loads((BASE/'metadata-v3/availability.json').read_text())
    assert d['p2_h150_compatible_count']==453
    assert 453-sum(x['incremental_excluded'] for x in d['ordered_exclusions'])==82
    assert d['metadata_eligible_maximum']==82
    assert d['common_sage_test_reserve_maximum']==0
    assert d['sage_training_role_in_eligible']==dict(train=73,val=9,test=0)
    assert d['known_e18_component_training_overlap_in_remaining']==0
    assert all(v is False for v in d['flags'].values())


def test_workload_no_pseudoreplication():
    t=json.loads((BASE/'timing-job-300309/timing.json').read_text())
    d=calculate(t,[82])['table'][0]
    assert d['episode_runs']==2460 and d['max_planner_calls']==36900
    assert d['max_primitive_actions']==553500
    assert d['primary_arm_runs']==1476 and d['secondary_arm_runs']==984
    assert d['conservative_envelope_hours_10ms_and_2x']>d['allocated_gpu_hours_5ms_action']


def test_accepted_source_files_unchanged_from_parent_commit():
    import hashlib,subprocess
    root=Path(__file__).resolve().parents[2]
    for name in ['e18_fresh_driver.py','pusht_fresh_initialization.py','gdp_cem_e18_runtime.py',
                 'gdp_cem_e18_closed_loop.py','gdp_cem_e18_specs.py']:
        relative='cluster/prometheus/'+name
        previous=subprocess.check_output(['git','show','286088e:'+relative],cwd=root)
        assert (root/relative).read_bytes()==previous
