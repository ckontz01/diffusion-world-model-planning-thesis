"""Freeze two fits only after the completed gate's scientific disposition."""
import hashlib,json
from .common import *

def additions():return {'wm_diag0_rc1_heads_v1/'+p.name:p.read_bytes() for p in sorted((ROOT/'wm_diag0_rc1_heads_v1').glob('*.py'))}

def main():
    if (DOC/'HEADS-CONTRACT.json').exists():raise FileExistsError('one freeze')
    review=json.loads((DOC/'PRO-GATE-DISPOSITION-001.json').read_text())
    if review['disposition']!='PROCEED_WITH_PLANNED_TWO_HEADS_CONDITIONAL_ON_REAL_CHECKS' or not review['parent_independently_reviewed']:
        raise ValueError('scientific result disposition unresolved')
    if json.loads((DOC/'ARTIFICIAL-ROUTE-001.json').read_text())['status']!='PASSED':raise ValueError('new interface tests')
    old=ROOT/'docs/world-model-diagnostic-rc1-v1-20261016/RC1-CONTRACT.json'
    if identity(old)!=GATE_CONTRACT:raise ValueError('gate closure')
    receipt=ROOT/'docs/world-model-diagnostic-rc1-v1-20261016/GATE-RESULT-RECEIPT-001.json'
    result=json.loads(receipt.read_text())
    if result['report']!=GATE_REPORT or result['output_seal']!=GATE_SEAL or result['GPU_cumulative_all_attempts_seconds']!=287 or not result['full_temporal_forecast_exact_bits']:
        raise ValueError('accepted gate result binding')
    c=json.loads(old.read_text())
    for n,b in additions().items():
        compile(b,n,'exec');c['staged_members'][n]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
    c.update(run=RUN,dino_source=RUN+'/source/dino',gpu_stages_authorized=False,full_campaign_ready=False)
    c['rc1']['gate_authorized']=False
    c['rc1_heads']={'exact_two_fits_authorized':True,'settings':[1,3],'campaign_dispatch_authorized':False,'gate_run':GATE_RUN,
        'gate_contract':GATE_CONTRACT,'gate_report':GATE_REPORT,'gate_seal':GATE_SEAL,'gate_job_id':'317174',
        'result_receipt':identity(receipt),'scientific_disposition':identity(DOC/'PRO-GATE-DISPOSITION-001.json'),
        'GPU_charged_before':287,'CPU_charged_before':1436,'allocated_attempts_before':9,'automatic_retries':0,
        'allocation_seconds_each':1800,'work_seconds':1740,'independent_validation_seconds':55,'finalize_seconds':5,
        'output_and_tmp_bytes_each':139000000,'log_bytes_each':100000,'actual_usage_each':USAGE,
        'full_future_GPU_seconds':461087,'full_future_CPU_seconds':6836,'original_fit_recipe_unchanged':True,
        'new_DINO_fit_frames_each':256,'new_DINO_validation_frames_each':96,'old_heads_preserved':True}
    if sum(x['bytes'] for x in c['staged_members'].values())>5000000:raise ValueError('source closure bound')
    write_new(DOC/'HEADS-CONTRACT.json',c)
    print(json.dumps({'status':'EXACT_TWO_HEAD_CONTRACT_FROZEN','contract':identity(DOC/'HEADS-CONTRACT.json'),'campaign_dispatch_enabled':False}))

if __name__=='__main__':main()
