"""Record the exact resource blocker; never build/stage/submit a recovery."""
import json
from .common import DOC,ROOT,identity,write_new
from .resource_gate import reservation,require_within_original_limits


def main():
    r=json.loads((DOC/'RECONCILIATION-001.json').read_text())
    try:require_within_original_limits(r)
    except RuntimeError as e:blocked=str(e)
    else:raise RuntimeError('unexpected resource-gate state')
    if (DOC/'CONTRACT.json').exists():raise RuntimeError('unexpected frozen recovery contract')
    result={'study':'WM-DIAG0-A2','status':'BLOCKED_PHYSICAL_FULL_FUTURE_RESERVATION',
            'fault':'Reacher000 collection completed; pretty-printed audit exceeded 2MB writer cap before acceptance',
            'repair_status':'lossless compact writer implemented; artificial tests passed; real retry unexecuted',
            'successful_PushT_roots_preserved':60,'failed_source_job':'317102','failed_array':'317041',
            'previously_unstarted_Reacher_roots':59,'failed_replacement_proposed_not_authorized':1,
            'scope':'same fixed root/seed; four original numeric arrays would have to agree bit-for-bit',
            'physical_reservations':reservation(r),'blocker':blocked,
            'CPU_charged_seconds':r['CPU_total_with_preflight'],'CPU_charged_plus_full_future_seconds':r['CPU_total_charged_plus_full_future'],
            'CPU_cap_seconds':13800,'GPU_charged_seconds':0,'GPU_full_future_seconds':468000,'GPU_cap_seconds':468000,
            'live_full_future_bytes_including_failed_evidence':12836395242+r['failed_retained_bytes'],'live_cap_bytes':13000000000,
            'preparation_cumulative_seconds':14104.10301460012,'preparation_unreserved_seconds':295.89698539988,
            'preparation_actuals_not_added_twice':True,'source_gate_complete':False,'GPU_campaign_launched':False,
            'new_stage_created':False,'new_jobs_submitted':0,'science_changed':False,
            'reasoning_model_consulted':False,'reason':'resource authority is required, not a scientific design choice; external advice cannot expand limits',
            'reconciliation':identity(DOC/'RECONCILIATION-001.json'),
            'writer_artificial_test':identity(ROOT/'docs/world-model-diagnostic-a2-native-v3-20261015/LOCAL-SOURCER2TEST001.json'),
            'all_prior_source_errors_STOPs_partials_and_acceptances_untouched':True,
            'campaign_v4_remaining_unexecuted_work':['final source completeness gate','four readouts','first four native parity jobs','remaining fixed diagnostic grid','independent complete analysis','whole/member final SSD preservation'],
            'campaign_v4_draft_status':'unexecuted, incomplete and not launch-ready; no research result readout'}
    write_new(DOC/'BLOCKED-001.json',result)
    print(json.dumps(result,sort_keys=True,indent=2))


if __name__=='__main__':main()
