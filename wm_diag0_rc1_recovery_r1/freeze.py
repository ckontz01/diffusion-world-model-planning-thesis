"""Freeze separately versioned repair only after real reconciliation/tests."""
import ast,copy,json
from .common import *
from .prepare import regression
from .supervisor import repaired_source

def main():
    regression()
    from .inspect_v2 import AFTER,program
    # New installed-Slurm compatibility cases, not an old suite rerun.
    base=[['317180_'+str(i),str(317181+i),'COMPLETED','0:0','1','4','gpu09'] for i in range(67)]
    group=['317180_[67-123%1]','317180','CANCELLED by 1201','0:0','0','4','None assigned']
    scope={'rows':copy.deepcopy(base)+[group]};exec(AFTER,scope)
    assert len(scope['rows'])==124 and len(scope['original_rows'])==68
    for bad in ([*group[:4],'1',*group[5:]],[*group[:6],'gpu09'],['317180_[68-123%1]']+group[1:]):
        try:exec(AFTER,{'rows':copy.deepcopy(base)+[bad]})
        except ValueError:pass
        else:raise AssertionError('unallocated grouped terminal coverage guard')
    ast.parse(program(),feature_version=(3,6))
    from .stage import STAGE
    from .observe import READ
    ast.parse(STAGE,feature_version=(3,6));ast.parse(READ,feature_version=(3,6))
    oldpath=ROOT/'docs/world-model-diagnostic-rc1-grid-v1-20261016/GRID-CONTRACT.json'
    if identity(oldpath)['sha256']!=GRID_HASH:raise ValueError('original contract preserved')
    old=json.loads(oldpath.read_text());c=copy.deepcopy(old)
    a=json.loads((DOC/'AUTHORITY-001.json').read_text());z=json.loads((DOC/'BINDING002.json').read_text());t=json.loads((DOC/'LINUXTEST001.json').read_text())
    if z['status']!='OLD81_ATTEMPTS_RECONCILED_FOR_EXACT58_RECOVERY' or z['accepted_indices']!=list(range(66)) or t['status']!='NEW_LINUX_MUTABLE_TMP_AND_EARLY_LEADER_CLEANUP_PASSED':raise ValueError('actual lineage and Linux guards')
    names=sorted((ROOT/'wm_diag0_rc1_recovery_r1').glob('*.py'))
    for p in names:
        ast.parse(p.read_text(),feature_version=(3,6));c['staged_members'][str(p.relative_to(ROOT)).replace('\\','/')]=identity(p)
    if any(c['staged_members'].get(k)!=v for k,v in old['staged_members'].items()):raise ValueError('no original source replacement')
    c.update(run=RUN,dino_source=RUN+'/source/dino')
    c['rc1_grid'].update(allocated_attempts_before=81,remaining_grid_attempts=58,all_attempts_full_future=139,
                       GPU_charged_before=45902,full_future_GPU_seconds=254702)
    c['rc1_recovery']={'authority':a,'indices':INDICES,'old_run':OLD,'old_contract_sha256':GRID_HASH,
      'allocated_before':81,'planned_total_attempts':139,'GPU_terminal_before':45902,'GPU_full_future':254702,
      'old_failure_controls':z['old_failure_controls'],'old_PID':z['old_PID'],'old_start_ticks':z['old_start_ticks'],
      'binding_receipt':identity(DOC/'BINDING002.json'),'accepted_control_commitment':z['accepted_control_commitment'],
      'Linux_regression_receipt':identity(DOC/'LINUXTEST001.json'),'original_supervisor_identity':old['staged_members']['wm_diag0_rc1_grid_v1/supervisor.py'],
      'repair':'no-follow single-stat mutable own-artifact scan; disappearance only; traceback; always owned-group cleanup',
      'exact_original_scientific_worker_and_validator':True,'no_successful_parent_recomputed':True,
      'old_failed_allocation_and_full_parent_work_reserved':True,'node_namespace_old_PID_ticks_gate_before_any_research_child':True,
      'storage_proof':z['storage'],'final_study_acceptance_or_archive_gate':False}
    closed_indices(c)
    for k,v in old.items():
        if k not in ('run','dino_source','staged_members','rc1_grid') and c[k]!=v:raise ValueError('original science/supplier/runtime field changed')
    if sum(x['bytes'] for x in c['staged_members'].values())>5000000:raise ValueError('full frozen source bound')
    write_new(DOC/'GRID-CONTRACT.json',c)
    review={'status':'RECOVERY_FIXED_SCOPE_SOURCE_AND_CONTRACT_REVIEW_PASSED','review':'Parent compared original/current science, worker, validator, all suppliers, runtime, root plan, deadlines and resource envelopes; only declared new recovery metadata/run paths/source additions differ.',
      'original_contract':identity(oldpath),'new_contract':identity(DOC/'GRID-CONTRACT.json'),
      'sources':{str(p.relative_to(ROOT)).replace('\\','/'):identity(p) for p in names},
      'original_scientific_source_members_unchanged':True,'first_allocation_node_namespace_entry_guard':True,
      'planned_new_indices':INDICES,'no_automatic_retry':True,'final_gate_ready':False,
      'additional_auxiliary_all_logical_copies_reserved':4000000,'within_overall_storage_proof':True}
    write_new(DOC/'REVIEW-001.json',review);print(json.dumps({'status':review['status'],'contract':review['new_contract']}))

if __name__=='__main__':main()
