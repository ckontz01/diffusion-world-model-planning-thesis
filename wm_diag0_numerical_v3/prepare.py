"""Freeze a new validation contract without modifying any executed closure."""
import hashlib,json
from .common import *

MODULES=('__init__','common','metrics','reference','bank','worker','validate','supervisor','tests')

def additions():
    return {'wm_diag0_numerical_v3/'+m+'.py':(ROOT/'wm_diag0_numerical_v3'/(m+'.py')).read_bytes() for m in MODULES}

def main():
    DOC.mkdir(exist_ok=True)
    old=ROOT/'docs/world-model-diagnostic-a2-campaign-v4-20261015/campaign/CONTRACT.json'
    amended=ROOT/'docs/world-model-diagnostic-a2-numerical-validation-r2-20261015/NUMERICAL-VALIDATION-AMENDMENT.md'
    if identity(old)['sha256']!=OLD_CONTRACT or identity(amended)['sha256']!=AMENDMENT:raise ValueError('reviewed unchanged identities')
    rec=json.loads((ROOT/'docs/world-model-diagnostic-a2-parity-r1-20261015/RECONCILIATION-001.json').read_text())
    fresh=json.loads((DOC/'RECONCILIATION-001.json').read_text())
    if fresh['GPU_charged_seconds']!=249 or fresh['status']!='TERMINAL_AND_SEALS_RECONCILED':raise ValueError('fresh finite accounting')
    c=json.loads(old.read_text())
    for n,b in additions().items():
        compile(b,n,'exec');c['staged_members'][n]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
    c['recovery']={'old_run':OLD_RUN,'new_validation_run':RUN,'old_contract':OLD_CONTRACT,
        'amendment':identity(amended),'direct_authorization':identity(DOC/'DIRECT-AUTHORIZATION-20261016.txt'),
        'partial':rec['failed_partial_members'],'accepted_suppliers':rec['accepted'],
        'reconciliation':identity(DOC/'RECONCILIATION-001.json'),'GPU_charged_before':249,
        'allocation_seconds':180,'work_seconds':120,'preservation_seconds':60,
        'output_bytes':26_000_000,'log_bytes':100_000,'automatic_retries':0,
        'full_future_GPU_seconds':249+180+127*3600,'full_future_CPU_seconds':1436+3600+1800,
        'full_future_live_bytes':12_882_899_989,'actual_usage':EXPECTED_USAGE,
        'approved_cumulative_maxima':{'DINO_predictor_calls':950755,'cost_reforecast_API_operations':126859,
            'bank_reforecast_sequences':2064,'technical_parity_sequences':160,'predicted_macro_sequence_transitions':190091120,
            'world_resets':6402,'PushT_reset_internal_steps':6402},
        'common_indices':COMMON,'context_indices':CONTEXT,'old_uncached_status':{'pusht':'FAILED','reacher':'UNTESTED'}}
    c.update(numerical_validation_authorized=True,gpu_stages_authorized=False,gpu_stage_authorized=False,
        source_generation_authorized=False,conditional_dispatch_ready=False)
    if c['recovery']['full_future_GPU_seconds']>468000 or c['recovery']['full_future_live_bytes']>13_000_000_000:raise ValueError('unchanged outer caps')
    write_new(DOC/'VALIDATION-CONTRACT.json',c)
    print(json.dumps({'contract':identity(DOC/'VALIDATION-CONTRACT.json'),'validation_only':True,'campaign_ready':False}))

if __name__=='__main__':main()
