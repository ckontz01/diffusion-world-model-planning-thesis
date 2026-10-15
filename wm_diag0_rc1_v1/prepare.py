"""Freeze the one-gate contract; no fit/grid allocation is enabled."""
import ast,json
from .common import *

def additions():
    return {'wm_diag0_rc1_v1/'+p.name:p.read_bytes() for p in sorted((ROOT/'wm_diag0_rc1_v1').glob('*.py'))}

def main():
    if (DOC/'RC1-CONTRACT.json').exists():raise FileExistsError('frozen once')
    for name in ('LOCAL-RC1LOCAL001.json','LOCAL-RC1ART001.json','LOCAL-RC1GATETEST001.json'):
        r=json.loads((DOC/name).read_text())
        if r['returncode']:raise ValueError('artificial test failed')
    if json.loads((DOC/'RECONCILE-001.json').read_text())['GPU_charged_seconds']!=268:raise ValueError('fresh old-allocation reconciliation')
    a=json.loads((DOC/'AUTHORITY.json').read_text());caps=a['approved_RC1_cumulative_counters']
    if caps!={'GPU_allocated_attempts':138,'DINO_predictor_calls':950760,'forecast_cost_API_operations':126860,'additional_technical_parity_sequences':176,
              'predicted_macro_sequence_transitions':190091200,'readout_fit_tasks':6,'readout_fit_frame_processing':1536,'readout_validation_frame_processing':576}:
        raise ValueError('finite direct authority')
    old=ROOT/'docs/world-model-diagnostic-a2-numerical-validation-v3-20261016/VALIDATION-CONTRACT.json'
    if identity(old)['sha256']!='2045e463d88120ec2cf994293f06ea1a64e3392a0ed7f3414564965b7fb89287':raise ValueError('exact prior validation closure')
    c=json.loads(old.read_text())
    for n,b in additions().items():
        compile(b,n,'exec');c['staged_members'][n]={'bytes':len(b),'sha256':__import__('hashlib').sha256(b).hexdigest()}
    ast.parse((ROOT/'wm_diag0_rc1_v1/supervisor.py').read_bytes(),feature_version=(3,6))
    c.update(run=RUN,dino_source=RUN+'/source/dino',numerical_validation_authorized=False,gpu_stages_authorized=False,
             gpu_stage_authorized=False,source_generation_authorized=False,conditional_dispatch_ready=False,full_campaign_ready=False,
             live_cap=13500000000,archive_cap=14000000000,inclusive_cap=44000000000)
    c['rc1']={'representation':REPRESENTATION,'gate_authorized':True,'refit_dispatch_authorized_by_this_contract':False,'campaign_dispatch_authorized_by_this_contract':False,
      'authority':identity(DOC/'AUTHORITY.json'),'preparation_activation':identity(DOC/'PREPARATION-ACTIVATION.json'),
      'reviewed_plan_source':'5459aeeb6a11db1a2c3eb83b057c2db228cc7659','timing_and_review_source':'cb22298cfa171ee3bdda8c23491bf64fe6040b5c',
      'timing_spec':identity(ROOT/'docs/world-model-diagnostic-rc1-final-plan-v1-20261016/TIMING-CLARIFICATION-20261016.md'),
      'old_campaign':OLD_RUN,'V3_run':V3_RUN,'V3_report':V3_REPORT,
      'V3_output_seal':{'bytes':384,'sha256':'56f5e5b678f5bc1c9e07b2ddea68d9a7c8dc7c5c03843081163ab4dd889bae83'},
      'actual_usage':EXPECTED_GATE_USAGE,'common_indices':COMMON,'context_indices':CONTEXT,
      'GPU_charged_before':268,'CPU_charged_before':1436,'allocation_seconds':180,'work_seconds':120,'independent_validation_seconds':55,'finalize_seconds':5,
      'output_bytes':26000000,'log_bytes':100000,'approved_cumulative_counters':caps,'full_future_GPU_seconds':461248,'full_future_CPU_seconds':6836,
      'full_future_live_bytes':12840451198,'archive_payload_plus_overhead_bytes':13340451198,'inclusive_bytes':43715303510,
      'archive_overhead_bytes':500000000,'automatic_retries':0,'source_and_goal_must_match_V3_exactly':True,
      'full_forecast_rtol':2**-6,'full_forecast_atol':2**-8,'role_and_repeats_exact':True,'terminal_cost_exact':True,
      'head_timing_formula':'2*(L+352*max(E))+600<=1740','parent_timing_formula':'2*(L+166*max(E))+1800<=3540',
      'all_original_and_failed_sources_unchanged':True}
    if sum(x['bytes'] for x in c['staged_members'].values())>5000000:raise ValueError('small frozen source bound')
    write_new(DOC/'RC1-CONTRACT.json',c)
    print(json.dumps({'status':'RC1_GATE_ONLY_CONTRACT_FROZEN','contract':identity(DOC/'RC1-CONTRACT.json'),'gate_only':True,'campaign_ready':False,'research_calls':0}))

if __name__=='__main__':main()
