import hashlib,json
from pathlib import Path
from .common import DOC,ROOT,RUN,OLD,identity,write_new

def additions():
    return {'wm_diag0_native_v3/entry.py':(ROOT/'wm_diag0_source_r2/entry.py').read_bytes(),
            'wm_diag0_source_r2/__init__.py':(ROOT/'wm_diag0_source_r2/__init__.py').read_bytes(),
            'wm_diag0_source_r2/writer.py':(ROOT/'wm_diag0_source_r2/writer.py').read_bytes()}

def main():
    r=json.loads((DOC/'RECONCILIATION-001.json').read_text())
    if r['status']!='ALL_ALLOCATIONS_TERMINAL_AND_RECONCILED' or r['CPU_total_charged_plus_full_future']>13800:raise ValueError('complete reconciliation/full future')
    from .resource_gate import require_within_original_limits
    require_within_original_limits(r)
    c=json.loads((ROOT/'docs/world-model-diagnostic-a2-campaign-v4-20261015/source-import-r1/CONTRACT.json').read_text())
    c['run']=RUN
    for name,raw in additions().items():c['staged_members'][name]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    c['cpu_charged_before']=r['CPU_total_with_preflight'];c['cpu_full_future_reserved']=9000
    c['source_recovery']={'fault':'lossless full audit JSON exceeded generic pretty-print receipt size guard',
            'only_replaced_source_root':'WM-DIAG0-A2-v1:reacher:root-000','failed_job_id':'317102','failed_array_id':'317041',
            'failed_cpu_seconds':13,'failed_physical_work':r['failed_physical_work'],
            'failed_partial':r['failed_partial'],'partial_supplier':RUN+'/controls/original-reacher-000',
            'accepted_suppliers':r['accepted_suppliers'],'old_run':OLD,'authorized_indices':list(range(60,120)),
            'new_native_source_attempts_max':60,'new_genuinely_failed_replacement_attempts_max':1,'previously_unstarted_roots':59,
            'successful_roots_to_recompute':0,'logical_source_roots':120,'all_attempt_source_allocations_max':121,
            'original_planned_scientific_source_actions':5280,'extra_failed_source_actions_charged':44,
            'all_attempt_source_actions_reserved':5324,'original_planned_total_scientific_resets':6400,'all_attempt_resets_reserved':6401,
            'original_planned_total_scientific_controller_actions':386880,'all_attempt_controller_actions_reserved':386924,
            'science_target_count_unchanged':True,'new_array_scope':'60-119%1 on gpu06, same seeds and exact original bytes for root0',
            'old_STOP_and_failed_partials_untouched':True,'reconciliation':identity(DOC/'RECONCILIATION-001.json')}
    c['live_full_future_bytes']+=r['failed_retained_bytes']
    if c['live_full_future_bytes']>13_000_000_000:raise ValueError('all-failure-inclusive live cap')
    c['source_stage_total_CPU_actual_plus_full_future']=r['cpu_source_charged_seconds']+3600
    if c['source_stage_total_CPU_actual_plus_full_future']>7200:raise ValueError('original source-stage CPU envelope')
    write_new(DOC/'CONTRACT.json',c)
    print(json.dumps({'contract':identity(DOC/'CONTRACT.json'),'CPU_charged':c['cpu_charged_before'],'CPU_full_future':9000,
                      'CPU_with_full_future':c['cpu_charged_before']+9000,'source_stage_CPU_full_future':c['source_stage_total_CPU_actual_plus_full_future'],
                      'live_full_future':c['live_full_future_bytes'],'failed_replacements':1,'untouched_roots':59,'successful_roots_repeated':0}))

if __name__=='__main__':main()
