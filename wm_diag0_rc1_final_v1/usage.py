"""Failure-inclusive numerical/physical counters for the complete fixed study.

Historical constants are not new instrumentation. A separately authenticated
historical counter/provenance receipt must be bound before real final execution.
"""
from wm_diag0_rc1_grid_v1.resources import source_and_failed_helper,add,require

KEYS=('visual_encoder_calls','encoded_frames','proprio_encoder_calls','action_encoder_calls','predictor_calls','cost_api_calls')
HISTORICAL_DINO=dict(zip(KEYS,(923,1613,1018,115,485,37)))
HISTORICAL_LEWM=dict(zip(KEYS,(88,704,0,0,0,0)))
CAPS={'DINO_predictor_calls':950760,'LeWM_predictor_calls':317140,'forecast_cost_API_operations':126860,
      'encoded_frames':265360,'readout_fit_tasks':6,'fit_frames':1536,'validation_frames':576,
      'bank_reforecast_sequences':2064,'additional_parity_sequences':176,'native_CEM_decisions':4224,
      'CEM_sequences':38016000,'predicted_macro_sequence_transitions':190091200}


def cpu_history(sources):
    old=[x.split('|') for x in sources['scheduler_original'].splitlines() if x.strip()]
    new=[x.split('|') for x in sources['scheduler_recovery'].splitlines() if x.strip()]
    if len(old)!=62 or len(new)!=60 or any(len(x)!=7 or x[5]!='4' or not x[4].isdigit() for x in old+new):raise ValueError('exact original/recovery CPU source history')
    if sum(int(x[4]) for x in old)!=678 or any(x[2]!='COMPLETED' or x[3]!='0:0' for x in new):raise ValueError('failure-inclusive CPU source charge')
    charge=17+sum(int(x[4]) for x in old+new)
    if charge!=1436 or sources['cpu_total_with_preflight']!=charge or sources['failed_replacement_attempts']!=1:raise ValueError('actual historical CPU preflight/source failure/recovery')
    return {'charged_before_analysis':charge,'unconsumed_conversion_reserved_seconds':1800,'final_analysis_reserved_seconds':3600,'full_future_seconds':charge+5400,'cap':13800}


def total(parents,head_proofs,n_sub_steps):
    if len(parents)!=128 or len({(r[0]['setting'],r[0]['root_index']) for r in parents})!=128:raise ValueError('complete128 only, no partial resource aggregate')
    if len(head_proofs)!=6 or sum(bool(h['active']) for h in head_proofs)!=4 or any(not h['accepted'] or h['fit_frames']!=256 or h['validation_frames']!=96 for h in head_proofs):raise ValueError('all six retained fits with four active')
    if type(n_sub_steps) is not int or n_sub_steps<1:raise ValueError('fixed native MuJoCo substeps')
    counts={'lewm':dict(HISTORICAL_LEWM),'dinowm_noprop':dict(HISTORICAL_DINO)}
    physical=source_and_failed_helper();production=32;parity=80
    for proof,out,usage,work,actual in parents:
        s,i=proof['setting'],proof['root_index'];backbone=proof['backbone'];n=proof['candidate_count']
        if backbone not in counts or not 1<=n<=16 or proof['technical']!=(i==0):raise ValueError('actual fixed parent resource row')
        if s==0 and i==0:
            # Original saved USAGE is authenticated, but no retrospective hook
            # measurement is invented. Native source arithmetic is disclosed.
            if (n,usage['predictor_calls'],usage['cost_api_calls'],usage['encoded_frames'])!=(16,4965,993,2066):raise ValueError('unchanged original accepted LeWM usage')
            actual=dict(zip(KEYS,(2*usage['cost_api_calls']+n,usage['encoded_frames'],0,6*usage['cost_api_calls'],usage['predictor_calls'],usage['cost_api_calls'])))
        if actual is None or set(actual)!=set(KEYS) or any(type(actual[k]) is not int or actual[k]<0 for k in KEYS):raise ValueError('exact invocation metadata')
        if any(actual[k]!=usage[k] for k in ('predictor_calls','cost_api_calls','encoded_frames')):raise ValueError('hook/manual counter agreement')
        counts[backbone]={k:counts[backbone][k]+actual[k] for k in KEYS}
        physical=add(physical,work)
        if not (s==1 and i==0):production+=n
        if i==0 and s in (0,2,3):parity+=2*n
    physical=require(physical)
    physical['Reacher_MuJoCo_integrator_steps']=physical['Reacher_dm_steps']*n_sub_steps
    cem=physical['native_CEM_decisions'];sequences=cem*9000
    values={'DINO_predictor_calls':counts['dinowm_noprop']['predictor_calls'],'LeWM_predictor_calls':counts['lewm']['predictor_calls'],
        'forecast_cost_API_operations':sum(x['cost_api_calls'] for x in counts.values()),'encoded_frames':sum(x['encoded_frames'] for x in counts.values()),
        'readout_fit_tasks':6,'fit_frames':1536,'validation_frames':576,'bank_reforecast_sequences':production,'additional_parity_sequences':parity,
        'native_CEM_decisions':cem,'CEM_sequences':sequences,'predicted_macro_sequence_transitions':5*(sequences+production+parity)}
    if any(values[k]>v for k,v in CAPS.items()):raise ValueError('failure-inclusive complete all-attempt invocation cap')
    return {'all_attempt_counts':values,'unchanged_caps':CAPS,'per_backbone_module_counts':counts,'physical_work':physical,
        'historical_DINO_baseline':HISTORICAL_DINO,'historical_LeWM_baseline':HISTORICAL_LEWM,
        'baseline_encoded_frames_all_six_fits_and_failed_diagnostics':2317,
        'original_LeWM_technical0_counts':'saved authenticated USAGE plus fixed native source arithmetic; not retrospective hooks',
        'retained_bank_initial_CEM_charged_once_to_original_failed_supplier':True,'failed_helpers_and_inactive_old_heads_retained_and_charged':True}
