"""Authenticate terminal observation and publish only numerical/control metadata."""
import json
from wm_diag0_rc1_v1.common import ROOT,DOC,identity,write_new,EXPECTED_GATE_USAGE

def main():
    observed=json.loads((DOC/'OBSERVE-002.json').read_text())
    if observed['queue'].strip() or observed['scheduler'].strip()!='317174|COMPLETED|0:0|19|4|gpu09':raise ValueError('exact terminal allocation')
    if observed['STOP'] is not None or observed['stderr']:raise ValueError('fault/STOP before acceptance')
    result=observed['result'];report=observed['report']
    if result['actual_usage']!=EXPECTED_GATE_USAGE or not result['all_RC1_checks_passed'] or not result['saved_full_forecast_independently_recomputed']:
        raise ValueError('complete actual independent gate acceptance')
    write_new(DOC/'GATE-REPORT-001.json',report)
    if identity(DOC/'GATE-REPORT-001.json')!=result['report_identity']:raise ValueError('byte-identical original report')
    rows=[json.loads(p.read_text()) for p in DOC.glob('LOCAL-*.json') if not p.name.endswith('.started.json')]
    components={k:sum(r['elapsed_seconds'] for r in rows if r['component']==k) for k in ('implementation_artificial_schema','cluster_artificial_interface','freeze_publication_SSD','metadata_reconciliation_staging','fault_reserve')}
    row={'status':'RC1_GATE_ACCEPTED_TECHNICALLY_PENDING_PRO_SCIENTIFIC_REVIEW','job_id':'317174','scheduler':observed['scheduler'],
      'source_commit':'ed3dc7769d859744f8e87f6a80af8d1f27461a22','contract':identity(DOC/'RC1-CONTRACT.json'),
      'report':result['report_identity'],'output_seal':result['output_seal'],'actual_usage':EXPECTED_GATE_USAGE,
      'GPU_allocation_seconds':19,'GPU_cumulative_all_attempts_seconds':287,'CPU_cumulative_all_attempts_seconds':1436,
      'full_future_GPU_seconds':287+2*1800+127*3600,'full_future_CPU_seconds':1436+3600+1800,
      'full_temporal_forecast_exact_bits':report['reference']['forecast']['exact_bits'],'forecast_coordinates':6021120,
      'role_repeat_exact_both_tasks':True,'source_goal_and_terminal_cost_exact':True,
      'timing_screens_passed_both_tasks':True,'timing_not_worst_case_guarantee':True,
      'source_bank_forecast_reused_not_recomputed':True,'original_uncached_PushT':'FAILED','original_uncached_Reacher':'UNTESTED',
      'unsaved_role_arrays_not_independently_recomputed_later':True,'no_new_CEM_or_physics':True,
      'new_head_fits':0,'campaign_resumed':False,'Pro_review_complete':False,
      'nonrefundable_preparation_charge_seconds':14354.10301460012,'preparation_cap_seconds':14400,
      'remaining_unreserved_preparation_seconds':45.89698539988,'RC1_measured_seconds_before_this_record':sum(components.values()),
      'RC1_measured_component_seconds':components,'monitor_id':'monitor-wm-diag0-rc1-and-recover-technical-faults','monitor_ACTIVE':True,
      'efficacy_or_readout_quality_inspected':False,'old_successes_failures_or_closures_modified':False}
    write_new(DOC/'GATE-RESULT-RECEIPT-001.json',row);print(json.dumps(row,indent=2))

if __name__=='__main__':main()
