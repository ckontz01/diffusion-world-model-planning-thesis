"""Check documentation arithmetic only, using existing technical receipts."""
import json
from pathlib import Path
from wm_diag0_native_v3.common import ROOT,write_new,identity

DOCREL='docs/world-model-diagnostic-a2-numerical-validation-r2-20261015'
DOC=ROOT/DOCREL

def main():
    old=ROOT/'docs/world-model-diagnostic-a2-campaign-v4-20261015/campaign/CONTRACT.json'
    assert identity(old)['sha256']=='f08e53e73035171340fe2438e3061685a3be6d1f18a8b132540717bd447a60dc'
    c=json.loads(old.read_text())
    r=json.loads((ROOT/'docs/world-model-diagnostic-a2-parity-r1-20261015/RECONCILIATION-001.json').read_text())
    z=json.loads((ROOT/'docs/world-model-diagnostic-a2-parity-r1-20261015/OBSERVE-ONE.json').read_text())
    assert r['accepted_technical0_physical']['world_resets']==51 and r['accepted_technical0_physical']['controller_actions']==2888
    assert r['accepted_technical0_usage']['predictor_calls']==4965
    assert z['scheduler'].split('|')[3]=='13' and z['result']['report']['actual_usage']['predictor_calls']==0
    old_counts=json.loads((ROOT/'docs/world-model-diagnostic-a2-20261004/RESOURCE-PLAN.json').read_text())['counts']
    assert old_counts['dino_predictor_chunk_calls_max']==950740 and old_counts['cost_api_calls_max']==126856
    a={
       'GPU_charged_seconds':236+13,'GPU_proposed_verification_seconds':180,
       'GPU_full_future_seconds':236+13+180+127*3600,'CPU_full_future_seconds':1436+3600+1800,
       'LeWM_predictor_calls':4965+63*4955+10,'DINO_predictor_calls':465+63*14855+10+32*450+15,
       'cost_reforecast_API_operations':993+33+63*991+2+63*991+2+960+3,
       'CEM_decisions':33+1+63*33+63*33+32,'world_resets':121+51+1+124*49+3*51,
       'controller_actions':5324+2888+20+124*2980+3*3020,
       'PushT_controller_actions':2640+2888+20+62*2980+3020,'PushT_resets':60+51+1+62*49+51,
       'Reacher_dm_and_MuJoCo_steps':5368+64*2980*2+4*20*2,
       'role_visual_encoder_calls':2*2*(5+1+1),'role_encoded_frames':2*2*(5+5+8),
       'new_visual_encoder_calls':2*2*(5+1+1)+6,'new_encoded_frames':2*2*(5+5+8)+6,
       'new_proprio_encoder_calls':2*2*(5+1+1)+9,'new_action_encoder_calls':7,'new_predictor_calls':15,
       'new_cost_reforecast_API_operations':3,'new_terminal_score_reductions':3,'new_physics_resets':0,
       'new_controller_actions':0,'encoded_full_future_frames':1408+2066+22+17+63*2062+4+63*148+18+144+78,
       'bank_reforecast_sequences':2048+16,'technical_parity_sequences':128+32,
       'predicted_macro_sequence_transitions':190090880+3*16*5,
       'live_full_future_bytes':12844699989+10000000+1100000+26100000+1000000,
       'proposed_all_study_GPU_attempts':132+1+1+1}
    a['PushT_integrator_steps']=10*a['PushT_controller_actions']+2*a['PushT_resets']
    a['PushT_reset_internal_steps']=2*a['PushT_resets']
    assert (a['GPU_full_future_seconds'],a['DINO_predictor_calls'],a['cost_reforecast_API_operations'],a['world_resets'])==(457629,950755,126859,6402)
    assert (a['controller_actions'],a['encoded_full_future_frames'],a['live_full_future_bytes'])==(386812,142987,12882899989)
    assert a['GPU_full_future_seconds']<=468000 and a['CPU_full_future_seconds']<=13800 and a['live_full_future_bytes']<=13000000000
    assert a['controller_actions']<=c['physical_all_attempt_maxima']['all_controller_steps_max']
    assert a['Reacher_dm_and_MuJoCo_steps']<=386968 and a['PushT_integrator_steps']<=1940800
    gaps={'DINO_predictor_calls':15,'cost_reforecast_API_operations':3,'bank_reforecast_sequences':16,
          'technical_parity_sequences':32,'predicted_macro_sequence_transitions':240,'world_resets':1,'PushT_reset_internal_steps':2}
    row={'status':'DISABLED_DOCUMENTATION_ARITHMETIC_CHECKED','scientific_or_resource_approval':False,
         'new_inference_authorized':False,'campaign_resumption_authorized':False,'original_contract':identity(old),
         'proposed_counts':a,'required_human_exceptions':gaps,
         'new_model_or_physics_operations_executed_by_this_check':0,'models_imported':False,
         'document':identity(DOC/'NUMERICAL-VALIDATION-AMENDMENT.md')}
    write_new(DOC/'ARITHMETIC-CHECK-001.json',row);print(json.dumps(row,indent=2))

if __name__=='__main__':main()
