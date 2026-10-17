"""Checkpoint009 local-only closure integration audit; no remote observation."""
import ast,json,stat,sys
from wm_diag0_rc1_completion_v1.common import ROOT,DOC,CAPS,identity,write_new,charge
from .preservation_budget_v1 import SOURCE_DOC_BUNDLE_LIMIT,AUX_RESERVATIONS
from .transport_disposition_v1 import FAILURE


def main():
    label=sys.argv[1]
    paths=[p for p in DOC.glob('LOCAL-*.json') if not p.name.endswith('.started.json')]
    rows=[json.loads(p.read_text()) for p in paths]
    starts=[p for p in DOC.glob('LOCAL-*.started.json') if not (DOC/p.name.replace('.started.json','.json')).exists()]
    if not label.isalnum() or [p.name for p in starts]!=['LOCAL-'+label+'.started.json']:raise ValueError('exclusive own audit; no ambiguous prior start')
    own=json.loads(starts[0].read_text())
    if own['component']!='handoff' or own['reserved_seconds']!=30:raise ValueError('full handoff30 reservation')
    charged={k:sum(charge(r) for r in rows if r['component']==k) for k in CAPS};charged['handoff']+=30
    if any(charged[k]>CAPS[k] for k in CAPS) or sum(charged.values())>21600:raise ValueError('unchanged caps/no transfer')
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
            if stat.S_ISLNK(s.st_mode) or getattr(s,'st_file_attributes',0)&0x400:raise ValueError('ordinary auxiliary members only')
            if stat.S_ISREG(s.st_mode):
                total+=s.st_size
                if p not in monitor:bundle+=s.st_size
            elif not stat.S_ISDIR(s.st_mode):raise ValueError('no auxiliary special member')
    if total+200000>20000000 or bundle+200000>SOURCE_DOC_BUNDLE_LIMIT or sum(AUX_RESERVATIONS.values())!=63928640:
        raise ValueError('local20MB/sourcebundle4.5MB/allcopies64MB prospective bounds')
    pub=json.loads((mondoc/'SSD-VERIFIED-001.json').read_text())
    for n,want in pub['working_source_members'].items():
        if identity(ROOT/n)!=want:raise ValueError('published observer unchanged')
    testpath=finaldoc/'ARTIFICIAL-ANALYSIS-CLOSURE-001.json';test=json.loads(testpath.read_text())
    for n,want in test['source'].items():
        if identity(ROOT/'wm_diag0_rc1_final_v2'/n)!=want:raise ValueError('new tested closure source changed')
    if test['final_gate_ready'] is not False or test['actual_historical_evidence_or_study_outputs_read'] is not False or test['research_WSL_cluster_scheduler_SSD_calls']!=0:
        raise ValueError('new tests local/synthetic only, no readiness promotion')
    checks=sum(r['component']=='monitoring' for r in rows)
    if checks!=7 or list(DOC.glob('OBSERVE-R008*.json')) or (DOC/'LOCAL-RESUMEOBS008.started.json').exists():raise ValueError('no new R008 observation start/check charge this wake')
    if identity(DOC/'OBSERVE-R006.failure.json')!=FAILURE:raise ValueError('retained original unavailable observation')
    cleanup=identity(ROOT/'wm_diag0_rc1_final_v1/cpu_process_v2.py')
    if cleanup!={'bytes':8269,'sha256':'13f3d73a8a83b3f561b331836e02c110b4db064d428e6bb70728c113e20a0672'}:raise ValueError('original V2 cleanup source unchanged')
    result={'status':'CHECKPOINT009_SOURCE_ONLY_CLOSED_ANALYSIS_HANDOFF_LOCAL_AUDIT_PASSED',
        'source':source,'component_charged_including_this_reserved_audit':charged,'total_charged':sum(charged.values()),
        'remaining':21600-sum(charged.values()),'remaining_components':{k:CAPS[k]-charged[k] for k in CAPS},
        'monitor_checks_used':checks,'remaining_checks':240-checks,'new_remote_observation_attempts_this_wake':0,
        'R008_label_never_started_or_charged':True,'WSL_path_available_at_bootstrap':False,
        'WSL_path_retested_or_WSL_started_by_this_audit':False,'current_cluster_health':'UNVERIFIED',
        'last_successful_R007_is_historical_not_current_proof':identity(DOC/'OBSERVE-R007.json'),
        'previous_R006_failure_preserved':FAILURE,'new_closure_test':identity(testpath),
        'all_new_local_auxiliary_bytes_before_final_compact_receipts':total,
        'new_non_monitor_source_doc_bundle_bytes_before_final_compact_receipts':bundle,
        'forward_final_receipt_allowance_bytes':200000,'auxiliary_subreservations':AUX_RESERVATIONS,
        'actual_whole_study_all_logical_copy_preparation_volume_proof_passed':False,
        'original_V2_cleanup':cleanup,'new_network_WSL_cluster_SSD_or_scientific_query_by_audit':False,
        'source_frozen_or_published':False,'actual_final_CPU_analysis_study_archive_full_SSD_run':False,'final_gate_ready':False}
    write_new(DOC/'CHECKPOINT-AUDIT-009.json',result,limit=64000)
    print(json.dumps({k:v for k,v in result.items() if k!='source'}))


if __name__=='__main__':main()
