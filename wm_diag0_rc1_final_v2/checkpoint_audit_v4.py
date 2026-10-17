"""Checkpoint006: exact charges/new root+archive+CPU preparation, local only."""
import ast,json,stat,sys
from pathlib import Path
from wm_diag0_rc1_completion_v1.common import ROOT,DOC,CAPS,identity,write_new,charge
from wm_diag0_rc1_monitor_v2.compact import decode_record
from .preservation_budget_v1 import SOURCE_DOC_BUNDLE_LIMIT,AUX_RESERVATIONS


def main():
    label=sys.argv[1]
    if not label.isalnum():raise ValueError('exclusive owned audit label')
    paths=[p for p in DOC.glob('LOCAL-*.json') if not p.name.endswith('.started.json')]
    rows=[json.loads(p.read_text()) for p in paths]
    starts=[p for p in DOC.glob('LOCAL-*.started.json') if not (DOC/p.name.replace('.started.json','.json')).exists()]
    if [p.name for p in starts]!=['LOCAL-'+label+'.started.json']:raise ValueError('only this audit may have an unpaired LOCAL start')
    own=json.loads(starts[0].read_text())
    if own['component']!='handoff' or own['reserved_seconds']!=30:raise ValueError('full existing handoff30 reservation')
    charges={k:sum(charge(r) for r in rows if r['component']==k) for k in CAPS};charges['handoff']+=30
    if any(charges[k]>CAPS[k] for k in CAPS) or sum(charges.values())>21600:raise ValueError('actual full component/total reservations, no transfer')
    source={};roots=[]
    for package in ('wm_diag0_rc1_completion_v1','wm_diag0_rc1_final_v2','wm_diag0_rc1_monitor_v2'):
        root=ROOT/package;roots.append(root)
        for p in root.glob('*.py'):
            ast.parse(p.read_text(),feature_version=(3,6));source[str(p.relative_to(ROOT)).replace('\\','/')]=identity(p)
    final_doc=ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016';monitor_doc=ROOT/'docs/world-model-diagnostic-rc1-monitor-v2-20261016'
    roots += [DOC,final_doc,monitor_doc]
    monitor_files=set()
    for p,r in zip(paths,rows):
        if r['component']=='monitoring':monitor_files.update((p,DOC/p.name.replace('.json','.started.json')))
    monitor_files.update(DOC.glob('OBSERVE-R*.json'))
    total=bundle=0
    for root in roots:
        for p in root.rglob('*'):
            s=p.lstat()
            if stat.S_ISLNK(s.st_mode) or getattr(s,'st_file_attributes',0)&0x400:raise ValueError('no new auxiliary redirect')
            if stat.S_ISREG(s.st_mode):
                total+=s.st_size
                if p not in monitor_files:bundle+=s.st_size
            elif not stat.S_ISDIR(s.st_mode):raise ValueError('ordinary auxiliary file/dir only')
    if total+200000>20000000 or bundle+200000>SOURCE_DOC_BUNDLE_LIMIT:raise ValueError('local20MB and prospective4.5MB non-monitor source/doc bundle')
    if sum(AUX_RESERVATIONS.values())!=63928640:raise ValueError('unchanged64MB all-copy auxiliary subreservations')
    pub=json.loads((monitor_doc/'SSD-VERIFIED-001.json').read_text())
    for n,want in pub['working_source_members'].items():
        if identity(ROOT/n)!=want:raise ValueError('published monitor source unchanged')
    receipts=('ARTIFICIAL-ROOT-BINDING-001.json','ARTIFICIAL-ARCHIVE-PIPELINE-001.json','ARTIFICIAL-CPU-SCHEDULE-001.json','ARTIFICIAL-CPU-SCHEDULE-002.json')
    for name in receipts:
        z=json.loads((final_doc/name).read_text())
        for n,want in z['source'].items():
            if identity(ROOT/'wm_diag0_rc1_final_v2'/n)!=want:raise ValueError('tested source/predecessor changed: '+n)
        if z['final_gate_ready'] is not False:raise ValueError('artificial/source-only work cannot grant real gates')
    cleanup=identity(ROOT/'wm_diag0_rc1_final_v1/cpu_process_v2.py')
    if cleanup!={'bytes':8269,'sha256':'13f3d73a8a83b3f561b331836e02c110b4db064d428e6bb70728c113e20a0672'}:raise ValueError('original tested cleanup never modified')
    raw=json.loads((DOC/'OBSERVE-R005.json').read_text());obs=decode_record(raw)
    if obs['accepted_grid_parents']!=55 or obs['accepted_indices']!=list(range(55)) or obs['GPU_terminal_all_attempts_seconds']!=35753 or obs['faults'] or obs['STOP_present']:
        raise ValueError('exact R005 technical snapshot, no inferred state')
    live=obs['active_process_records']
    if len(live)!=1 or live[0]['index']!=55 or live[0]['node_verification']!={'PID_exists':True,'start_ticks_match':True}:raise ValueError('both compute-node process identities verified')
    result={'status':'CHECKPOINT006_SOURCE_ONLY_ROOT_ARCHIVE_CPU_INTEGRATION_AUDITED_NOT_FINAL_GATE','source':source,
            'component_charged_including_this_reserved_audit':charges,'total_charged':sum(charges.values()),
            'remaining':21600-sum(charges.values()),'remaining_components':{k:CAPS[k]-charges[k] for k in CAPS},
            'monitor_checks_used':sum(r['component']=='monitoring' for r in rows),'scheduled_cluster_observations_this_wake':1,
            'all_new_local_auxiliary_bytes_before_final_compact_receipts':total,
            'new_non_monitor_source_doc_bundle_bytes_before_final_compact_receipts':bundle,
            'source_doc_bundle_future_limit':SOURCE_DOC_BUNDLE_LIMIT,'auxiliary_subreservations':AUX_RESERVATIONS,
            'auxiliary_subreservation_total_all_copies':sum(AUX_RESERVATIONS.values()),'auxiliary_locked_margin':71360,
            'auxiliary_and_whole_study_actual_future_copy_counts_still_require_final_stage_authentication':True,
            'observation':identity(DOC/'OBSERVE-R005.json'),'original_lossless_observation':raw['original_canonical_identity'],
            'snapshot_accepted_grid_parents':55,'snapshot_terminal_GPU_charge':35753,
            'new_receipts':{n:identity(final_doc/n) for n in receipts+('CPU-SCHEDULE-V1-DIAGNOSIS-001.json',)},
            'future_CPU_draft_adapter':'cpu_schedule_v2.validate_draft','original_V2_cleanup_source':cleanup,
            'unused_wrong_V1_size_constant_preserved_not_production':True,
            'new_network_cluster_or_SSD_query_by_audit':False,'scientific_values_read':False,
            'final_source_frozen_or_published':False,'actual_final_CPU_study_analysis_archive_or_full_SSD_run':False,'final_gate_ready':False}
    write_new(DOC/'CHECKPOINT-AUDIT-006.json',result,limit=64000)
    print(json.dumps({k:v for k,v in result.items() if k!='source'}))


if __name__=='__main__':main()
