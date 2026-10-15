"""Freeze only an encoding diagnostic, not an altered parity gate or rerun."""
import hashlib,json
from .common import DOC,ROOT,OLD_RUN,OLD_CONTRACT,RUN,identity,write_new

MODULES=('__init__','common','probe','supervisor')

def additions():
    return {'wm_diag0_parity_r1/'+m+'.py':(ROOT/'wm_diag0_parity_r1'/(m+'.py')).read_bytes() for m in MODULES}

def main():
    p=ROOT/'docs/world-model-diagnostic-a2-campaign-v4-20261015/campaign/CONTRACT.json'
    if identity(p)['sha256']!=OLD_CONTRACT:raise ValueError('unchanged frozen source')
    rec=json.loads((DOC/'RECONCILIATION-001.json').read_text())
    if rec['status']!='STOPPED_DAG_FULLY_TERMINAL_RECONCILED' or rec['GPU_charged_seconds']!=236:raise ValueError('terminal reconciliation')
    c=json.loads(p.read_text())
    for n,b in additions().items():
        compile(b,n,'exec');c['staged_members'][n]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
    c['recovery']={'old_run':OLD_RUN,'new_diagnostic_run':RUN,'old_contract':OLD_CONTRACT,
                   'human_request':'Fix the issue and resume the run','authority':'bounded technical diagnosis only; resume still gated',
                   'partial':rec['failed_partial_members'],'accepted_suppliers':rec['accepted'],
                   'reconciliation':identity(DOC/'RECONCILIATION-001.json'),
                   'GPU_charged_before':236,'probe_allocation_seconds':180,'probe_work_seconds':120,
                   'full_remaining_diagnostic_GPU_reservation':127*3600,'GPU_total_with_probe_and_future':236+180+127*3600,
                   'output_and_temporary_bytes':1000000,'log_bytes':100000,
                   'encoded_frames':17,'predictor_calls':0,'cost_calls':0,'physics_resets':0,'controller_actions':0,
                   'no_tolerance_change':True,'no_campaign_submission':True,'automatic_retry':False}
    c.update(gpu_stages_authorized=False,gpu_stage_authorized=False,source_generation_authorized=False,conditional_dispatch_ready=False)
    if c['recovery']['GPU_total_with_probe_and_future']>468000 or c['live_full_future_bytes']+1100000>c['live_cap']:raise ValueError('unchanged GPU/storage envelope')
    write_new(DOC/'PROBE-CONTRACT.json',c)
    print(json.dumps({'contract':identity(DOC/'PROBE-CONTRACT.json'),'encoding_only':True,'GPU_maximum':c['recovery']['GPU_total_with_probe_and_future'],
                      'real_predictor_calls':0,'physics_resets':0,'full_campaign_ready':False}))

if __name__=='__main__':main()
