"""Freeze remaining included checks only; grid and full analysis stay disabled."""
import hashlib,json
from .common import *

def additions():return {'wm_diag0_rc1_technical_v1/'+p.name:p.read_bytes() for p in sorted((ROOT/'wm_diag0_rc1_technical_v1').glob('*.py'))}

def main():
    if (DOC/'TECHNICAL-CONTRACT.json').exists():raise FileExistsError('freeze once')
    h=ROOT/'docs/world-model-diagnostic-rc1-heads-v1-20261016';r=json.loads((h/'HEADS-RESULT-RECEIPT-001.json').read_text())
    if r['status']!='EXACT_TWO_NEW_RC1_HEADS_INDEPENDENTLY_ACCEPTED' or r['GPU_all_attempts_cumulative']!=331 or r['all_attempts_full_future']!=138:raise ValueError('both accepted new heads and finite attempt accounting')
    for n in ('ARTIFICIAL-LOCAL-001.json','ARTIFICIAL-REFERENCE-001.json'):
        z=json.loads((DOC/n).read_text())
        if z.get('status')!='PASSED' and z.get('returncode')!=0:raise ValueError('new artificial interface rejection/reference tests')
    previous=h/'HEADS-CONTRACT.json'
    if identity(previous)['sha256']!='5917ef387f6cbd528aa02e762d3fd9729f001f90d167a3808775648a71e3c629':raise ValueError('accepted frozen head closure')
    c=json.loads(previous.read_text())
    for n,b in additions().items():
        compile(b,n,'exec');c['staged_members'][n]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
    c.update(run=RUN,dino_source=RUN+'/source/dino',gpu_stages_authorized=False,full_campaign_ready=False)
    c['rc1_heads']['exact_two_fits_authorized']=False
    c['rc1_technical']={'three_settings_authorized':True,'settings':[1,2,3],'grid_authorized':False,'analysis_authorized':False,'heads_run':HEADS_RUN,
        'heads_contract':identity(previous),'head_suppliers':r['suppliers'],'heads_result_receipt':identity(h/'HEADS-RESULT-RECEIPT-001.json'),
        'gate_run':GATE_RUN,'gate_report':c['rc1_heads']['gate_report'],'gate_seal':c['rc1_heads']['gate_seal'],
        'scientific_gate_disposition':identity(h/'PRO-GATE-DISPOSITION-001.json'),'GPU_charged_before':331,'CPU_charged_before':1436,'allocated_attempts_before':11,
        'remaining_parents':127,'this_stage_allocations':3,'later_grid_allocations':124,'full_future_GPU_seconds':457531,'full_future_CPU_seconds':6836,
        'work_seconds':3540,'independent_validation_seconds':55,'finalize_seconds':5,'allocation_seconds_each':3600,'automatic_retries':0,
        'actual_usage_bounds':{str(i):bounds(i) for i in (1,2,3)},'output_tmp_bytes':{'1':60000000,'2':10000000,'3':60000000},'log_bytes_each':1000000,
        'preserved_technical0':c['recovery']['accepted_suppliers']['technical-0'],'source_calls_or_fitting_repeated':False,
        'failed_PushT_bank_and_V3_prediction_reused_only_after_exact_compatibility':True,'archive_overhead_bytes':500000000}
    if sum(x['bytes'] for x in c['staged_members'].values())>5000000:raise ValueError('bounded source closure')
    write_new(DOC/'TECHNICAL-CONTRACT.json',c)
    print(json.dumps({'status':'THREE_REMAINING_NATIVE_SETTINGS_FROZEN','contract':identity(DOC/'TECHNICAL-CONTRACT.json'),'grid_enabled':False,'new_fits':0}))

if __name__=='__main__':main()
