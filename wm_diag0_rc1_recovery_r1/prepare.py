"""Native artificial regression + durable latest human authority, no cluster."""
import ast,copy,json,os,stat,tempfile,threading,time
from pathlib import Path
from unittest.mock import patch
from .common import *
from .supervisor import repaired_source

MAXIMA={'world_resets':49,'controller_actions':2980,'Reacher_dm_steps':5960,'CEM_decisions':33,'CEM_sequences':297000,'bank_sequences':16,'macro_transitions':1485080,'visual_encoder_calls':1998,'encoded_frames':2062,'action_encoder_calls':5946,'predictor_calls':4955,'cost_api_calls':991}

def regression():
    class Entry:
        path='vanished'
        def stat(self,follow_symlinks=False):raise FileNotFoundError('deliberately unlinked transient entry')
    class Entries:
        def __enter__(self):return iter([Entry()])
        def __exit__(self,*args):pass
    with tempfile.TemporaryDirectory(prefix='wm-rc1-recovery-native-') as tmp:
        root=Path(tmp)/'tmp';root.mkdir();(root/'ordinary').write_bytes(b'fixture')
        assert sampled_bytes(root)==7
        with patch('os.scandir',lambda p:Entries()):assert sampled_bytes(root)==0
        with patch.object(Entry,'stat',side_effect=PermissionError('must not suppress permission')):
            try:
                with patch('os.scandir',lambda p:Entries()):sampled_bytes(root)
            except PermissionError:pass
            else:raise AssertionError('permission swallowed')
        class OldEntry:
            def is_file(self):return True
            def stat(self):raise FileNotFoundError('old is_file/stat race')
        try:sum(x.stat().st_size for x in [OldEntry()] if x.is_file())
        except FileNotFoundError:pass
        else:raise AssertionError('old race not reproduced')
        assert sampled_bytes(Path(tmp)/'output')==0
        try:sampled_bytes(Path(tmp)/'missing-required-tmp')
        except FileNotFoundError:pass
        else:raise AssertionError('required root absence suppressed')
    old=(ROOT/'wm_diag0_rc1_grid_v1/supervisor.py').read_text();fixed=repaired_source(old)
    ast.parse(fixed,feature_version=(3,6))
    assert "wm_diag0_rc1_grid_v1.worker" in fixed and "wm_diag0_rc1_grid_v1.validate" in fixed
    assert fixed.count('stop_owned(proc)')==2 and 'traceback.format_exc()' in fixed
    r={'authority':{'direct_human_instruction':HUMAN,'replacement_parent_maxima':MAXIMA},'indices':INDICES,'old_run':OLD,'allocated_before':81,'planned_total_attempts':139,'GPU_terminal_before':45902,'GPU_full_future':254702}
    c={'run':RUN,'rc1_recovery':r};closed_indices(c)
    for key,bad in [('indices',list(range(65,124))),('planned_total_attempts',True),('GPU_full_future',468001),('old_run','wrong')]:
        d=copy.deepcopy(c);d['rc1_recovery'][key]=bad
        try:closed_indices(d)
        except ValueError:pass
        else:raise AssertionError('recovery guard '+key)

def main():
    regression()
    for p in (ROOT/'wm_diag0_rc1_recovery_r1').glob('*.py'):ast.parse(p.read_text(),feature_version=(3,6))
    authority={'status':'DIRECT_HUMAN_AUTHORIZED_BOUNDED_TECHNICAL_RECOVERY','direct_human_instruction':HUMAN,
      'old_authority_preserved':identity(ROOT/'docs/world-model-diagnostic-rc1-completion-budget-v1-20261016/AUTHORITY.json'),
      'planned_total_attempts_this_recovery':139,'new_allocations':58,'replacement_index':66,'never_started_indices':list(range(67,124)),
      'accepted_indices_never_rerun':list(range(66)),'GPU_total_seconds_unchanged':468000,'GPU_each_seconds_unchanged':3600,
      'replacement_parent_maxima':MAXIMA,'new_failure_inclusive_cumulative_caps':{'world_resets':6451,'controller_actions':389904,'Reacher_dm_steps':392928,'CEM_decisions':4257,'CEM_sequences':38313000,'bank_sequences':2080,'macro_transitions':191576280,'LeWM_predictor_calls':322095,'forecast_cost_API_operations':127851},
      'DINO_fit_source_generation_and_science_unchanged':True,'failed_partial_conservatively_charged_one_full_LeWM_parent':True,
      'automatic_requeue':False,'old_frozen_sources_edited':False,'further_diagnosed_technical_recovery_not_an_unlimited_retry_grant':True,
      'recovery_auxiliary_all_copies_max_bytes':4000000,'existing_completion_auxiliary_reservation_bytes':64000000,
      'combined_new_auxiliary_reservation_bytes':68000000,'overall_live_archive_inclusive_limits_unchanged':[13500000000,14000000000,44000000000],
      'new_recovery_artificial_whole_root_max_bytes':1000000,'all_old_artificial_roots_retained':True,
      'preparation_time_budget_and_components_unchanged':True,'publication_full_remote_and_small_source_SSD_before_allocation':True}
    write_new(DOC/'AUTHORITY-001.json',authority)
    result={'status':'NEW_NATIVE_RECOVERY_REGRESSIONS_PASSED','checks':['old disappearance race reproduced','new vanished entry handled','permission errors retained','required root absence retained','unchanged science argv','owned group cleanup after leader exit','traceback retained','exact failed/unstarted scope and GPU maxima'],
      'sources':{str(p.relative_to(ROOT)).replace('\\','/'):identity(p) for p in (ROOT/'wm_diag0_rc1_recovery_r1').glob('*.py')},
      'GPU_scheduler_WSL_SSD_or_scientific_payload_calls':0,'actual_failed_path_recovered':False}
    write_new(DOC/'ARTIFICIAL-NATIVE-001.json',result);print(json.dumps({'status':result['status'],'authority':identity(DOC/'AUTHORITY-001.json')}))

if __name__=='__main__':main()
