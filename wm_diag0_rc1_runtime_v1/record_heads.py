"""Receipt from terminal exact-dispatch metadata, never model/scientific data."""
import json
from wm_diag0_rc1_heads_v1.common import DOC,identity,write_new,USAGE

def main():
    z=json.loads((DOC/'OBSERVE-002.json').read_text());rows=[x.split('|') for x in z['scheduler'].splitlines() if x]
    if z['queue'] or z['STOP'] is not None or {x[0] for x in rows}!={'317175_1','317175_3'} or any(x[2:]!=['COMPLETED','0:0','22','4','gpu09'] for x in rows):raise ValueError('two exact terminal heads')
    suppliers={}
    for k in ('1','3'):
        t=z['tasks'][k]
        if t['RESULT']['status']!='ACCEPTED' or t['WORKER-SUCCESS']['actual_usage']!=USAGE or not t['ACCEPTED']['RC1_pointwise_route_independently_bound']:raise ValueError('real independent head acceptance')
        if t['RESULT']['output_seal']!=t['ACCEPTED']['output_seal']:raise ValueError('head seal chain')
        suppliers[k]={'output_seal':t['ACCEPTED']['output_seal'],'acceptance_identity':t['RESULT']['acceptance_identity'],'route':t['WORKER-SUCCESS']['route'],'job_id':t['RESULT']['job_id']}
    out={'status':'EXACT_TWO_NEW_RC1_HEADS_INDEPENDENTLY_ACCEPTED','dispatch':'317175','scheduler':z['scheduler'],
        'suppliers':suppliers,'observation':identity(DOC/'OBSERVE-002.json'),'GPU_charge_this_stage':44,'GPU_all_attempts_cumulative':331,'CPU_all_attempts_cumulative':1436,
        'GPU_full_future':457531,'CPU_full_future':6836,'allocated_attempts_done':11,'remaining_parent_attempts':127,'all_attempts_full_future':138,
        'new_fit_frames':512,'new_validation_frames':192,'new_visual_calls_and_frames':704,'original_heads_preserved':True,
        'quality_or_predictions_read':False,'main_campaign_resumed':False,'next':'Implement/freeze supplier-aware continuation and three remaining included setting checks; all four before grid',
        'process_observation_limitation':'Earlier /proc checks ran on login host, not gpu09; false there was not cluster failure evidence. Both scheduler allocations are now terminal; no live controller restart is needed.'}
    write_new(DOC/'HEADS-RESULT-RECEIPT-001.json',out);print(json.dumps(out,indent=2))

if __name__=='__main__':main()
