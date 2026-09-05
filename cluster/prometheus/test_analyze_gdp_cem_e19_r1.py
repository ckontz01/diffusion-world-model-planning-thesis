import numpy as np
from analyze_gdp_cem_e19_r1 import delta,differences,stages,core,coverage

def test_numeric_delta():
    assert delta({'values':[1,2]},[1,3])=={'exact':False,'max_abs':1.,'mean_abs':.5}
def test_hash_and_numeric_difference():
    d=differences({'sha256':'a','values':[1.]},{'sha256':'b','values':[2.]},'state')
    assert d[0]['path']=='state' and d[0]['delta']['max_abs']==1
def test_repeated_stage_alignment():
    assert list(stages({'events':[{'stage':'x'},{'stage':'x'}]}))==['x#0','x#1']
def test_core_keeps_integration_and_separates_extra_state():
    assert core({'integration':[1],'outside':{'seed':2},'unavailable':'cache'})=={'integration':[1]}
def test_shape_mismatch_not_broadcast():
    assert delta(np.ones((1,2)),np.ones((2,)))['exact'] is False

def test_count_alone_does_not_pass_coverage():
    t={'steps':15,'fixed_return_calls':1,'stopped_at_cap':True,'events':[]}
    assert not coverage(t)
    t['events']=[{'stage':'before_first_action'}]
    for i in range(15): t['events'] += [{'stage':f'before_step:{i}'},{'stage':f'after_step:{i+1}'}]
    assert coverage(t)
