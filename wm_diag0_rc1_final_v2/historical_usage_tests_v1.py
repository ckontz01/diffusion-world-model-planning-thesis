"""Small inert accounting/provenance program checks; no historical data read."""
import ast,copy,json
from pathlib import Path
from .historical_usage_v1 import arithmetic,program,KEYS,EXPECTED_DINO,EXPECTED_LEWM
from wm_diag0_rc1_completion_v1.common import ROOT,identity,write_new


def reject(fn):
    try:fn()
    except ValueError:return
    raise AssertionError('missing exact historical usage rejection')


def main():
    r1=dict(zip(KEYS,(2,17,2,6,0,0)));r1['cost_calls']=r1.pop('cost_api_calls')
    v3=dict(zip(KEYS,(34,78,37,7,15,3)));v3['cost_reforecast_API_operations']=v3.pop('cost_api_calls')
    gate=dict(zip(KEYS,(88,88,88,5,5,1)));gate['cost_reforecast_API_operations']=gate.pop('cost_api_calls')
    head=dict(visual_encoder_calls=352,encoded_frames=352,proprio_encoder_calls=352,action_encoder_calls=0,predictor_calls=0)
    got=arithmetic(r1,v3,gate,[head,head])
    assert got['DINO_baseline']==EXPECTED_DINO and got['LeWM_baseline']==EXPECTED_LEWM
    assert got['baseline_encoded_frames_all_six_fits_and_failed_diagnostics']==2317
    assert got['DINO_components']['failed_DINO_source_arithmetic']==dict(zip(KEYS,(7,22,99,97,465,33)))
    reject(lambda:arithmetic(dict(r1,predictor_calls=True),v3,gate,[head,head]))
    reject(lambda:arithmetic(r1,dict(v3,encoded_frames=77),gate,[head,head]))
    reject(lambda:arithmetic(r1,v3,gate,[head]))
    reject(lambda:arithmetic(r1,v3,gate,[dict(head,encoded_frames=351),head]))
    code=program();ast.parse(code,feature_version=(3,6))
    assert 'sacct' not in code and 'squeue' not in code and 'torch' not in code
    result={'status':'ARTIFICIAL_HISTORICAL_USAGE_ARITHMETIC_PROGRAM_PASSED',
            'source':{n:identity(Path(__file__).parent/n) for n in ('historical_usage_v1.py','historical_usage_tests_v1.py')},
            'baseline_encoded_frames':2317,'failed_DINO_arithmetic':[7,22,99,97,465,33],
            'actual_remote_authentication_executed':False,'research_values_read':False,
            'model_fit_simulator_or_scheduler_calls':0,'final_gate_ready':False}
    write_new(ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016/ARTIFICIAL-HISTORICAL-USAGE-001.json',result)
    print(json.dumps(result))


if __name__=='__main__':main()
