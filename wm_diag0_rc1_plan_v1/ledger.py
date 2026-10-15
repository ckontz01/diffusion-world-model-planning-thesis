"""Check design arithmetic against recorded metadata; never import a model."""
import ast, json
from .inventory import DOC, DOCREL
from wm_diag0_native_v3.common import ROOT, identity, write_new

def main():
    obs = json.loads((DOC/'INVENTORY-001.json').read_text())
    runtime = json.loads((DOC/'RUNTIME-AND-SSD-001.json').read_text())
    assert obs['status']=='QUIESCENT_TECHNICAL_STORAGE_INVENTORY' and not obs['queue'].strip()
    assert runtime['status']=='WHOLE_RUNTIME_SIZE_AND_DESIGNATED_SSD_CHECKED'
    # Conservatively count every logical study file, not just unique hardlinks.
    existing = {'all_current_study_lineages_including_partials':obs['logical_study_bytes'],
                'whole_existing_venv_reserved':2100000000,'existing_SIF':obs['SIF_bytes'],
                'two_existing_LeWM_objects':sum(x['bytes'] for x in obs['LeWM'].values())}
    future = {'LeWM_63_remaining_output_and_tmp':63*10000000,
              'DINO_64_remaining_output_and_tmp':64*60000000,
              'all_127_parent_logs':127*1000000,
              'two_new_head_outputs_tmp_logs':2*139100000,
              'one_RC1_gate_output_tmp_log':26100000,
              'analysis_and_unused_conversion_evidence':60000000,
              'new_source_closures':20000000,'new_controls':300000000}
    live = sum(existing.values())+sum(future.values())
    archive = live+100000000
    inclusive = live+2*14000000000+2874852312
    assert (live, archive, inclusive)==(12840451198,12940451198,43715303510)
    assert live<=13500000000 and archive<=14000000000 and inclusive<=44000000000
    # Columns: visual invocations, image frames, proprio invocations, action
    # invocations, predictor invocations, forecast/cost API operations.
    names=('visual_calls','image_frames','proprio_calls','action_calls','predictor_calls','cost_forecast_API')
    dino_rows={
      'accepted_original_two_heads':(88,704,88,0,0,0),
      'failed_original_PushT_technical':(7,22,99,97,465,33),
      'completed_R1_encoding_probe':(2,17,2,6,0,0),
      'completed_V3_numerical_validation':(34,78,37,7,15,3),
      'proposed_new_two_heads':(704,704,704,0,0,0),
      'proposed_RC1_gate':(88,88,88,5,5,1),
      'remaining_63_ordinary_parent_base':tuple(63*x for x in (148,148,3119,2971,14855,991)),
      'included_Reacher_extra_parity':(18,18,19,6,10,2),
      'failed_PushT_continuation':(144,144,3024,2880,14400,960)}
    dino=dict(zip(names,(sum(x[i] for x in dino_rows.values()) for i in range(6))))
    lewm_rows={'accepted_original_two_heads':(88,704,0,0,0,0),
      'all_64_parent_base_including_accepted_PushT':tuple(64*x for x in (1998,2062,0,5946,4955,991)),
      'two_included_technical_extras_one_already_completed':(8,8,0,24,20,4)}
    lewm=dict(zip(names,(sum(x[i] for x in lewm_rows.values()) for i in range(6))))
    assert dino==dict(zip(names,(10409,11099,200558,190174,950760,63432)))
    assert lewm==dict(zip(names,(127968,132680,0,380568,317140,63428)))
    combined={n:dino[n]+lewm[n] for n in names}
    assert combined['image_frames']==143779 and combined['cost_forecast_API']==126860
    assert combined['visual_calls']==138377 and combined['action_calls']==570742
    assert 38016000*5+2064*5+176*5==190091200
    assert 268+180+2*1800+127*3600==461248<=468000
    assert 1436+3600+1800==6836<=13800
    local=ROOT/'docs/world-model-diagnostic-a2-native-v3-20261015'
    measured=sum(json.loads(p.read_text())['elapsed_seconds'] for p in local.glob('LOCAL-*.json') if not p.name.endswith('.started.json'))
    # Future proposal reserves500 measured seconds within the existing charge,
    # plus250 of295.896... unreserved. No activation/charge happens here.
    assert measured+500+120<=1700
    for p in (ROOT/'wm_diag0_rc1_plan_v1').glob('*.py'):ast.parse(p.read_bytes())
    from .inventory import PROGRAM
    ast.parse(PROGRAM,feature_version=(3,6))
    from .runtime_inventory import PROGRAM as RUNTIME_PROGRAM
    ast.parse(RUNTIME_PROGRAM,feature_version=(3,6))
    row={'status':'RESOURCE_PLAN_ARITHMETIC_CHECKED_EXECUTION_DISABLED',
      'input_inventory':identity(DOC/'INVENTORY-001.json'),'runtime_size_receipt':identity(DOC/'RUNTIME-AND-SSD-001.json'),
      'storage':{'existing':existing,'future':future,'live':live,'live_cap':13500000000,
        'archive_payload_plus_100MB_overhead':archive,'archive_cap':14000000000,
        'inclusive_with_two_full_14GB_archives':inclusive,'inclusive_cap':44000000000,
        'retained_preparation_full_future':2874852312,'compression_or_deletion_savings_assumed':False,
        'hardlink_dedup_savings_used':False,'sampled_metadata_not_filesystem_quota':True},
      'DINO_rows':{k:dict(zip(names,v)) for k,v in dino_rows.items()},'DINO_totals':dino,
      'LeWM_rows':{k:dict(zip(names,v)) for k,v in lewm_rows.items()},'LeWM_totals':lewm,'combined':combined,
      'proposed_exceptions':{'GPU_attempts':[135,138],'DINO_predictor_calls':[950755,950760],
        'cost_forecast_API':[126859,126860],'technical_parity_sequences':[160,176],
        'predicted_macro_sequence_transitions':[190091120,190091200],
        'readout_fit_tasks':[4,6],'fit_frame_processing':[1024,1536],'validation_frame_processing':[384,576]},
      'unchanged_outer_caps':{'GPU_allocation_seconds':468000,'CPU_stage_seconds':13800,'CPU_threads':4,'RAM_bytes':8589934592,
        'encoded_frames':265360,'source_roots':120,'world_resets':6402,'bank_reforecast_sequences':2064},
      'full_future_GPU_seconds':461248,'full_future_CPU_seconds':6836,
      'preparation':{'current_nonrefundable_charge':14104.10301460012,'cap':14400,
        'current_measured_existing_continuation_seconds_before_this_check':measured,
        'proposed_implementation_measured_seconds_inside_existing_charge':500,
        'proposed_additional_finite_charge_within_original_cap':250,
        'proposed_implementation_total_seconds':750,'charge_if_activated':14354.10301460012,
        'unreserved_after_activation':45.89698539988,'activated':False},
      'additional_operation_exceptions_authorized':False,'scientific_implementation_performed':False,
      'new_model_forwards':0,'campaign_resumed':False,
      'runtime_feasibility':'UNMEASURED; proposed count/timing checks and finite stop rules, not a timing guarantee'}
    write_new(DOC/'LEDGER-001.json',row)
    print(json.dumps(row,indent=2))

if __name__=='__main__':main()
