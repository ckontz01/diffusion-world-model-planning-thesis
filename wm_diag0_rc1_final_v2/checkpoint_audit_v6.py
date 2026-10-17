"""Checkpoint008: recovered observation and finite native phase preparation."""
import ast,json,stat,sys
from pathlib import Path
from wm_diag0_rc1_completion_v1.common import ROOT,DOC,CAPS,identity,write_new,charge
from wm_diag0_rc1_monitor_v2.compact import decode_record
from .preservation_budget_v1 import SOURCE_DOC_BUNDLE_LIMIT,AUX_RESERVATIONS
from .transport_disposition_v1 import FAILURE


def main():
    label=sys.argv[1]
    paths=[p for p in DOC.glob('LOCAL-*.json') if not p.name.endswith('.started.json')]
    rows=[json.loads(p.read_text()) for p in paths]
    starts=[p for p in DOC.glob('LOCAL-*.started.json') if not (DOC/p.name.replace('.started.json','.json')).exists()]
    if not label.isalnum() or [p.name for p in starts]!=['LOCAL-'+label+'.started.json']:raise ValueError('one exclusive own audit start only')
    own=json.loads(starts[0].read_text())
    if own['component']!='handoff' or own['reserved_seconds']!=30:raise ValueError('full handoff30 reservation')
    charges={k:sum(charge(r) for r in rows if r['component']==k) for k in CAPS};charges['handoff']+=30
    if any(charges[k]>CAPS[k] for k in CAPS) or sum(charges.values())>21600:raise ValueError('no component/total transfer or extension')
    source={};roots=[]
    for pkg in ('wm_diag0_rc1_completion_v1','wm_diag0_rc1_final_v2','wm_diag0_rc1_monitor_v2'):
        roots.append(ROOT/pkg)
        for p in (ROOT/pkg).glob('*.py'):
            ast.parse(p.read_text(),feature_version=(3,6));source[p.relative_to(ROOT).as_posix()]=identity(p)
    finaldoc=ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016';mondoc=ROOT/'docs/world-model-diagnostic-rc1-monitor-v2-20261016'
    roots.extend((DOC,finaldoc,mondoc));monitor=set(DOC.glob('OBSERVE-R*.json'))
    for p,z in zip(paths,rows):
        if z['component']=='monitoring':monitor.update((p,DOC/p.name.replace('.json','.started.json')))
    total=bundle=0
    for root in roots:
        for p in root.rglob('*'):
            s=p.lstat()
            if stat.S_ISLNK(s.st_mode) or getattr(s,'st_file_attributes',0)&0x400:raise ValueError('no auxiliary alias/reparse redirect')
            if stat.S_ISREG(s.st_mode):
                total+=s.st_size
                if p not in monitor:bundle+=s.st_size
            elif not stat.S_ISDIR(s.st_mode):raise ValueError('ordinary auxiliary members only')
    if total+200000>20000000 or bundle+200000>SOURCE_DOC_BUNDLE_LIMIT or sum(AUX_RESERVATIONS.values())!=63928640:
        raise ValueError('unchanged local20MB/bundle4.5MB/allcopies64MB prospective reservation')
    pub=json.loads((mondoc/'SSD-VERIFIED-001.json').read_text())
    for n,want in pub['working_source_members'].items():
        if identity(ROOT/n)!=want:raise ValueError('published observer/source closure changed')
    testpath=finaldoc/'ARTIFICIAL-CPU-WORKFLOW-001.json';test=json.loads(testpath.read_text())
    for n,want in test['source'].items():
        if identity(ROOT/'wm_diag0_rc1_final_v2'/n)!=want:raise ValueError('new tested phase source changed')
    if test['actual_tiny_native_owned_synthetic_children']!=3 or test['actual_research_children']!=0 or test['final_gate_ready'] is not False:
        raise ValueError('synthetic native children not actual final analysis/archive')
    cleanup=identity(ROOT/'wm_diag0_rc1_final_v1/cpu_process_v2.py')
    if cleanup!={'bytes':8269,'sha256':'13f3d73a8a83b3f561b331836e02c110b4db064d428e6bb70728c113e20a0672'}:raise ValueError('original tested V2 owned cleanup unchanged')
    if identity(DOC/'OBSERVE-R006.failure.json')!=FAILURE:raise ValueError('original unavailable observation preserved')
    raw=json.loads((DOC/'OBSERVE-R007.json').read_text());obs=decode_record(raw)
    if obs['accepted_grid_parents']!=59 or obs['accepted_indices']!=list(range(59)) or obs['GPU_terminal_all_attempts_seconds']!=39503:
        raise ValueError('exact lossless original R007 technical rows and indices')
    if obs['STOP_present'] or obs['faults'] or obs['GPU_live_elapsed_not_final_seconds']!=384 or obs['GPU_full_remaining_maxima_plus_terminal']!=273503:
        raise ValueError('exact historical R007 status and full-future bound')
    live=obs['active_process_records']
    if len(live)!=1 or (live[0]['index'],live[0]['job_id'],live[0]['PID'],live[0]['start_ticks'])!=(59,'317303',240967,'9255875') or live[0]['node_verification']!={'PID_exists':True,'start_ticks_match':True}:
        raise ValueError('both exact compute-node PID/ticks bindings')
    checks=sum(r['component']=='monitoring' for r in rows)
    result={'status':'CHECKPOINT008_RESTORED_OBSERVATION_AND_SOURCE_ONLY_NATIVE_CPU_PHASE_INTEGRATION_AUDITED',
        'source':source,'component_charged_including_this_reserved_audit':charges,'total_charged':sum(charges.values()),
        'remaining':21600-sum(charges.values()),'remaining_components':{k:CAPS[k]-charges[k] for k in CAPS},
        'monitor_checks_used':checks,'remaining_checks':240-checks,'new_scheduled_cluster_observations_this_wake':1,
        'observation':identity(DOC/'OBSERVE-R007.json'),'original_lossless_observation':raw['original_canonical_identity'],
        'snapshot_accepted_grid_parents':59,'snapshot_terminal_GPU_charged_seconds':39503,'snapshot_live_elapsed_NOT_final':384,
        'previous_R006_failure_preserved':FAILURE,'older_R003_cause_retrospectively_inferred':False,
        'WSL_disk_path_configuration_environment_changed_by_agent':False,'new_phase_test':identity(testpath),
        'all_new_local_auxiliary_bytes_before_final_compact_receipts':total,
        'new_non_monitor_source_doc_bundle_bytes_before_final_compact_receipts':bundle,
        'final_compact_receipt_forward_allowance_bytes':200000,'auxiliary_subreservations':AUX_RESERVATIONS,
        'actual_whole_study_all_logical_copy_preparation_volume_proof_passed':False,
        'original_V2_cleanup':cleanup,'new_network_WSL_cluster_SSD_or_scientific_query_by_audit':False,
        'source_frozen_or_published':False,'actual_final_CPU_analysis_study_archive_full_SSD_run':False,'final_gate_ready':False}
    write_new(DOC/'CHECKPOINT-AUDIT-008.json',result,limit=64000)
    print(json.dumps({k:v for k,v in result.items() if k!='source'}))


if __name__=='__main__':main()
