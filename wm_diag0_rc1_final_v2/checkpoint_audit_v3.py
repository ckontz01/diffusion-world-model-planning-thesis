"""Checkpoint005: current technical receipt and source-only integration audit."""
import ast,json,stat,sys
from pathlib import Path
from wm_diag0_rc1_completion_v1.common import ROOT,DOC,CAPS,identity,write_new,charge
from wm_diag0_rc1_monitor_v2.compact import decode_record


def main():
    label=sys.argv[1]
    if not label.isalnum():raise ValueError('exclusive owned audit label')
    rows=[json.loads(p.read_text()) for p in DOC.glob('LOCAL-*.json') if not p.name.endswith('.started.json')]
    ambiguous=[p for p in DOC.glob('LOCAL-*.started.json') if not (DOC/p.name.replace('.started.json','.json')).exists()]
    if [p.name for p in ambiguous]!=['LOCAL-'+label+'.started.json']:raise ValueError('only this reserved audit may have an unpaired LOCAL start')
    own=json.loads(ambiguous[0].read_text())
    if own['component']!='handoff' or own['reserved_seconds']!=30:raise ValueError('existing handoff30 reservation')
    charged={k:sum(charge(r) for r in rows if r['component']==k) for k in CAPS};charged['handoff']+=30
    if any(charged[k]>CAPS[k] for k in CAPS) or sum(charged.values())>21600:raise ValueError('full component/total reservations')
    source={};roots=[]
    for package in ('wm_diag0_rc1_completion_v1','wm_diag0_rc1_final_v2','wm_diag0_rc1_monitor_v2'):
        root=ROOT/package;roots.append(root)
        for p in root.glob('*.py'):
            ast.parse(p.read_text(),feature_version=(3,6));source[str(p.relative_to(ROOT)).replace('\\','/')]=identity(p)
    final_doc=ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016'
    monitor_doc=ROOT/'docs/world-model-diagnostic-rc1-monitor-v2-20261016'
    roots += [DOC,final_doc,monitor_doc];size=0
    for root in roots:
        for p in root.rglob('*'):
            s=p.lstat()
            if stat.S_ISLNK(s.st_mode) or getattr(s,'st_file_attributes',0)&0x400:raise ValueError('no new auxiliary redirect')
            if stat.S_ISREG(s.st_mode):size+=s.st_size
            elif not stat.S_ISDIR(s.st_mode):raise ValueError('ordinary auxiliary file/dir only')
    if size+200000>20000000:raise ValueError('all six new local code/docs roots plus forward allowance fit20MB')
    pub=json.loads((monitor_doc/'SSD-VERIFIED-001.json').read_text())
    for n,want in pub['working_source_members'].items():
        if identity(ROOT/n)!=want:raise ValueError('published monitoring source/authority must remain unchanged')
    for name in ('PRESERVATION-LAYOUT-001.json','ARTIFICIAL-EVIDENCE-GUARD-001.json','ARTIFICIAL-COMPLETE-VALIDATOR-001.json'):
        z=json.loads((final_doc/name).read_text());src=z['source']
        if 'bytes' in src:
            if src!=identity(ROOT/'wm_diag0_rc1_final_v2/preservation_layout_v1.py'):raise ValueError('tested layout source changed')
        else:
            for n,want in src.items():
                if identity(ROOT/'wm_diag0_rc1_final_v2'/n)!=want:raise ValueError('tested new guard/validator source changed')
        if z['final_gate_ready'] is not False:raise ValueError('source-only checks cannot promote actual final readiness')
    wrapped=json.loads((DOC/'OBSERVE-R004.json').read_text());observed=decode_record(wrapped)
    if observed['dispatch']['array_job_id']!='317180' or observed['faults'] or observed['STOP_present'] or observed['research_jobs_or_controllers_changed'] or observed['scientific_values_or_quality_or_aggregates_inspected']:
        raise ValueError('exact new technical snapshot without mutation/science reads')
    if observed['accepted_grid_parents']!=54 or observed['accepted_indices']!=list(range(54)) or observed['GPU_terminal_all_attempts_seconds']!=34412:
        raise ValueError('exact current R004 receipt, no fabricated progress')
    if observed['active_process_records'][0]['node_verification']!={'PID_exists':True,'start_ticks_match':True}:raise ValueError('both node-local process identities verified')
    if not (DOC/'OBSERVE-R003.started.json').exists() or (DOC/'OBSERVE-R003.json').exists():raise ValueError('original unavailable R003 retained, never retried/fabricated')
    result={'status':'CHECKPOINT005_TECHNICAL_OBSERVATION_AND_SOURCE_ONLY_INTEGRATION_AUDITED_NOT_FINAL_GATE',
            'source':source,'component_charged_including_this_reserved_audit':charged,'total_charged':sum(charged.values()),
            'remaining':21600-sum(charged.values()),'remaining_components':{k:CAPS[k]-charged[k] for k in CAPS},
            'monitor_checks_used':sum(r['component']=='monitoring' for r in rows),
            'all_new_local_auxiliary_bytes_before_final_compact_receipts':size,'local_allocation':20000000,
            'all_new_auxiliary_all_logical_copy_reservation':64000000,
            'observation':identity(DOC/'OBSERVE-R004.json'),'original_lossless_observation':wrapped['original_canonical_identity'],
            'accepted_grid_parents_at_snapshot':54,'GPU_terminal_all_attempts_seconds_at_snapshot':34412,
            'R003_retried_or_cause_inferred':False,'scheduled_observations_this_wake':1,
            'integration_receipts':{n:identity(final_doc/n) for n in ('PRESERVATION-LAYOUT-001.json','ARTIFICIAL-EVIDENCE-GUARD-001.json','ARTIFICIAL-COMPLETE-VALIDATOR-001.json')},
            'new_current_cluster_or_SSD_query_performed_by_audit':False,'scientific_values_read':False,
            'actual_final_source_frozen_or_published':False,'actual_full_runtime_root_binding_or_storage_proof_passed':False,
            'actual_final_CPU_analysis_archive_or_full_SSD_run':False,'final_study_gate_ready':False}
    write_new(DOC/'CHECKPOINT-AUDIT-005.json',result,limit=64000)
    print(json.dumps({k:v for k,v in result.items() if k!='source'}))


if __name__=='__main__':main()
