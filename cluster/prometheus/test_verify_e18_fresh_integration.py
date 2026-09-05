from copy import deepcopy
import json
from pathlib import Path
import pytest
from verify_e18_fresh_integration import check, verify

ROOT=Path(__file__).with_name('e18-fresh-integration-evidence')

def payload():return json.loads((ROOT/'vad_continuation/INTEGRATION.json').read_text())

def test_complete_actual_package():
    result=verify(ROOT)
    assert sum(x['planner_calls'] for x in result['rows'])==128
    assert sum(x['primitive_actions'] for x in result['rows'])==1363
    assert not result['efficacy_claim'] and not result['holdout_authorized']

@pytest.mark.parametrize('mutate',[
    lambda p:p.update(holdout_read=True),
    lambda p:p['coefficient_gate']['action_mean'].__setitem__(0,0),
    lambda p:p['dependency_gate'].update(encoder_mapping_reads=['pixels','state']),
    lambda p:p['campaigns'][2]['rows'][0].update(initial='0'*64),
    lambda p:p['campaigns'][3]['rows'][0]['plans'][0].update(at=1),
    lambda p:p.update(initializer_sha256='0'*64),
    lambda p:p.update(native_vector_batch_size=3),
    lambda p:p.update(actual_planner_calls=25),
])
def test_reject_invalid_evidence(mutate):
    p=payload();mutate(p)
    with pytest.raises(AssertionError):check(p,'vad_continuation')
