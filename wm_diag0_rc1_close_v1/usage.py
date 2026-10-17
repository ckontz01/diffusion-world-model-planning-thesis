"""Accepted complete-study usage plus one conservatively charged failed parent."""
from wm_diag0_rc1_final_v1.usage import cpu_history,HISTORICAL_DINO,HISTORICAL_LEWM
from wm_diag0_rc1_final_v1.usage import total as accepted_total
from wm_diag0_rc1_grid_v1.resources import CAPS as OLD_PHYSICAL

def total(parents,head_proofs,n_sub_steps):
    result=accepted_total(parents,head_proofs,n_sub_steps)
    # The failed partial has no completed usage seal. Charge the FULL approved
    # parent maxima rather than inventing retrospective measurements.
    extra={'visual_encoder_calls':1998,'encoded_frames':2062,'proprio_encoder_calls':0,
           'action_encoder_calls':5946,'predictor_calls':4955,'cost_api_calls':991}
    lewm=result['per_backbone_module_counts']['lewm']
    for key,n in extra.items():lewm[key]+=n
    values=result['all_attempt_counts'];caps=dict(result['unchanged_caps'])
    increments={'LeWM_predictor_calls':4955,'forecast_cost_API_operations':991,'encoded_frames':2062,
                'bank_reforecast_sequences':16,'native_CEM_decisions':33,'CEM_sequences':297000,
                'predicted_macro_sequence_transitions':1485080}
    for key,n in increments.items():values[key]+=n
    for key,n in increments.items():
        if key!='encoded_frames':caps[key]+=n
    physical=result['physical_work']
    pextra={'world_resets':49,'controller_actions':2980,'Reacher_dm_steps':5960,'native_CEM_decisions':33}
    for key,n in pextra.items():physical[key]+=n
    physical['Reacher_MuJoCo_integrator_steps']=physical['Reacher_dm_steps']*n_sub_steps
    pcaps=dict(OLD_PHYSICAL)
    for key,n in pextra.items():pcaps[key]+=n
    if any(type(values[k]) is not int or values[k]<0 or values[k]>v for k,v in caps.items()):raise ValueError('recovery-inclusive numerical cap')
    if any(type(physical[k]) is not int or physical[k]<0 or physical[k]>v for k,v in pcaps.items()):raise ValueError('recovery-inclusive physical cap')
    result['unchanged_caps']=caps
    result['physical_caps_with_one_explicit_failed_parent']=pcaps
    result['failed_original_grid66']={'status':'FAILED125_RETAINED_NO_SEAL','allocation_seconds':79,
        'usage_charged':'FULL_APPROVED_PARENT_MAXIMA_NOT_RETROSPECTIVE_MEASUREMENT','module_counts':extra,
        'physical_counts':pextra,'CEM_sequences':297000,'bank_sequences':16,'macro_transitions':1485080}
    return result
