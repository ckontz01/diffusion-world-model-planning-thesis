from copy import deepcopy
from pathlib import Path
import pytest
from verify_gdp_cem_e19_r3_result import read, validate_core, validate_arm, verify

ROOT=Path(__file__).parent/'e19-r3-evidence'

def test_complete_sealed_bundle():
    assert verify(ROOT)['arms']==10

def test_core_missing_history_rejected():
    d=read(ROOT/'core/sage/validation/VALIDATION.json')
    d['rows'][0]['history']='unregistered'
    with pytest.raises(AssertionError):validate_core(d)

def test_core_nonzero_hidden_step_rejected():
    d=read(ROOT/'core/e18/validation/VALIDATION.json')
    d['fresh_initialization_physics_steps']=1
    with pytest.raises(AssertionError):validate_core(d)

def test_arm_slot_mapping_rejected():
    d=read(ROOT/'arms/sage/base_cem/ARM-CHECK.json')
    d['rows'][-1]['case_id']=99
    with pytest.raises(AssertionError):validate_arm(d)

def test_arm_preprocessing_scope_cannot_be_promoted():
    d=read(ROOT/'arms/e18/vad_greedy_300/ARM-CHECK.json')
    d['e18_non_action_scaler_values_checked']=True
    with pytest.raises(AssertionError):validate_arm(d)

def test_arm_no_solver_gate_rejected():
    d=read(ROOT/'arms/e18/vad_greedy_300/ARM-CHECK.json')
    d['solver_invocations']=1
    with pytest.raises(AssertionError):validate_arm(d)
