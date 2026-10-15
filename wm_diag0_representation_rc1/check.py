"""Read existing control metadata and check proposed arithmetic only."""
import json
from wm_diag0_native_v3.common import ROOT,identity,write_new

DOCREL='docs/world-model-diagnostic-representation-control-rc1-20261016'
DOC=ROOT/DOCREL

def main():
    prior=ROOT/'docs/world-model-diagnostic-a2-numerical-validation-v3-20261016'
    final=json.loads((prior/'FINAL-STATUS-20261016.json').read_text())
    old=ROOT/'docs/world-model-diagnostic-a2-campaign-v4-20261015/campaign/CONTRACT.json'
    assert identity(old)['sha256']=='f08e53e73035171340fe2438e3061685a3be6d1f18a8b132540717bd447a60dc'
    assert final['GPU_cumulative_all_attempts_seconds']==268 and final['CPU_cumulative_all_attempts_seconds']==1436
    assert final['role_compatibility_passed'] is False and final['Pro_review_complete'] is True
    baseline=12882899989;slack=13000000000-baseline
    raw_features=2*352*196*384*4
    proposed={'GPU_all_attempts_full_future_seconds':268+2*1800+180+127*3600,
              'CPU_full_future_seconds':1436+3600+1800,'all_GPU_attempts':135+3,
              'DINO_predictor_calls':950755+5,'cost_reforecast_API_operations':126859+1,
              'additional_parity_sequences':160+16,'macro_sequence_transitions':190091120+16*5,
              'bank_production_reforecast_sequences':2064,'readout_fit_tasks':4+2,
              'readout_fit_frames':1024+2*256,'readout_validation_frames':384+2*96,
              'encoded_full_future_frames':142987+2*352+72+16,'world_resets':6402,
              'live_full_future_bytes':baseline+2*(139000000+100000)+26000000+100000+1000000}
    assert proposed['GPU_all_attempts_full_future_seconds']==461248 and proposed['CPU_full_future_seconds']==6836
    assert proposed['live_full_future_bytes']==13188199989 and raw_features==211943424
    assert proposed['encoded_full_future_frames']==143779 and proposed['encoded_full_future_frames']<=265360
    assert proposed['GPU_all_attempts_full_future_seconds']<=468000 and proposed['CPU_full_future_seconds']<=13800
    assert raw_features>slack and proposed['live_full_future_bytes']>13000000000
    text=(DOC/'REPRESENTATION-CONTROL-AMENDMENT.md').read_text(encoding='utf8')
    for n in ('461248','950760','126860','190091200','143779','13188199989','188199989'):
        assert n in text
    row={'status':'DISABLED_PROPOSAL_ARITHMETIC_CHECKED_NOT_EXECUTABLE',
         'prior_final_status':identity(prior/'FINAL-STATUS-20261016.json'),
         'document':identity(DOC/'REPRESENTATION-CONTROL-AMENDMENT.md'),
         'original_contract':identity(old),'proposed_future_totals':proposed,
         'live_slack_bytes':slack,'new_head_raw_features_lower_bound_bytes':raw_features,
         'minimum_raw_features_above_live_slack_bytes':raw_features-slack,
         'conservative_live_cap_gap_bytes':proposed['live_full_future_bytes']-13000000000,
         'future_science_or_resource_exceptions_approved':False,'new_research_calls_executed':0,
         'research_frameworks_imported':False,'campaign_resumed':False,
         'preparation_cumulative_charge_seconds':14104.10301460012,
         'this_package_maximum_seconds_within_existing_charge':240,
         'future_implementation_preparation_requirement':'UNBOUND; not granted by documentation authority',
         'archive_and_inclusive_full_lineage_bounds':'UNRESOLVED; caps14GB/44GB unchanged'}
    write_new(DOC/'ARITHMETIC-CHECK-001.json',row);print(json.dumps(row,indent=2))

if __name__=='__main__':main()
