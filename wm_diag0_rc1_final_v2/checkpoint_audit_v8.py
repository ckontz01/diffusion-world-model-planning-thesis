"""Reusable compact exclusive local checkpoint audit; never a remote observer."""
import ast,json,re,stat,sys
from wm_diag0_rc1_completion_v1.common import ROOT,DOC,CAPS,identity,write_new,charge
from wm_diag0_rc1_monitor_v2.compact import decode_record
from .preservation_budget_v1 import SOURCE_DOC_BUNDLE_LIMIT,AUX_RESERVATIONS
from .transport_disposition_v1 import FAILURE


def main():
    label,number,observation,receipt=sys.argv[1:5]
    if not label.isalnum() or not re.fullmatch(r'[0-9]{3}',number) or not re.fullmatch(r'R[0-9]{3}',observation) or not re.fullmatch(r'ARTIFICIAL-[A-Z0-9-]+\.json',receipt):raise ValueError('bounded exclusive local audit selectors, never code or arbitrary paths')
    output=DOC/('CHECKPOINT-AUDIT-'+number+'.json')
    if output.exists():raise FileExistsError('never repeat an audit or replace its receipt')
    paths=[p for p in DOC.glob('LOCAL-*.json') if not p.name.endswith('.started.json')]
    rows=[json.loads(p.read_text()) for p in paths]
    starts=[p for p in DOC.glob('LOCAL-*.started.json') if not (DOC/p.name.replace('.started.json','.json')).exists()]
    if [p.name for p in starts]!=['LOCAL-'+label+'.started.json']:raise ValueError('only own audit may have an unpaired LOCAL start')
    own=json.loads(starts[0].read_text())
    if own['component']!='handoff' or own['reserved_seconds']!=30:raise ValueError('unchanged full handoff30 reservation')
    charges={k:sum(charge(r) for r in rows if r['component']==k) for k in CAPS};charges['handoff']+=30
    if any(charges[k]>CAPS[k] for k in CAPS) or sum(charges.values())>21600:raise ValueError('no transfer/refund/extension')
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
            if stat.S_ISLNK(s.st_mode) or getattr(s,'st_file_attributes',0)&0x400:raise ValueError('ordinary nonredirected auxiliary members only')
            if stat.S_ISREG(s.st_mode):
                total+=s.st_size
                if p not in monitor:bundle+=s.st_size
            elif not stat.S_ISDIR(s.st_mode):raise ValueError('no auxiliary special member')
    if total+200000>20000000 or bundle+200000>SOURCE_DOC_BUNDLE_LIMIT or sum(AUX_RESERVATIONS.values())!=63928640:raise ValueError('local20MB/sourcebundle4.5MB/64MB prospective allcopy bound')
    pub=json.loads((mondoc/'SSD-VERIFIED-001.json').read_text())
    for n,want in pub['working_source_members'].items():
        if identity(ROOT/n)!=want:raise ValueError('published monitor source changed')
    testpath=finaldoc/receipt;test=json.loads(testpath.read_text())
    for n,want in test['source'].items():
        if not re.fullmatch(r'[a-z0-9_]+\.py',n) or identity(ROOT/'wm_diag0_rc1_final_v2'/n)!=want:raise ValueError('exact new tested source identity')
    if test.get('final_gate_ready') is not False:raise ValueError('source-only/synthetic receipt never grants final gate')
    raw=json.loads((DOC/('OBSERVE-'+observation+'.json')).read_text());obs=decode_record(raw)
    if obs['faults'] or obs['STOP_present'] or obs['dispatch']['array_job_id']!='317180':raise ValueError('this checkpoint expects same-grid no-fault observation; faults require separate reconciliation')
    for row in obs['active_process_records']:
        if row['node_verification']!={'PID_exists':True,'start_ticks_match':True}:raise ValueError('both compute-node process identities required')
    if identity(DOC/'OBSERVE-R006.failure.json')!=FAILURE:raise ValueError('historical failed observer record unchanged')
    cleanup=identity(ROOT/'wm_diag0_rc1_final_v1/cpu_process_v2.py')
    if cleanup!={'bytes':8269,'sha256':'13f3d73a8a83b3f561b331836e02c110b4db064d428e6bb70728c113e20a0672'}:raise ValueError('original tested V2 cleanup unchanged')
    checks=sum(r['component']=='monitoring' for r in rows)
    result={'status':'LOCAL_SOURCE_ONLY_PREPARATION_CHECKPOINT_AUDITED_NOT_FINAL_GATE','checkpoint':number,
        'source':source,'component_charged_including_this_reserved_audit':charges,'total_charged':sum(charges.values()),
        'remaining':21600-sum(charges.values()),'remaining_components':{k:CAPS[k]-charges[k] for k in CAPS},
        'monitor_checks_used':checks,'remaining_checks':240-checks,
        'last_observation':identity(DOC/('OBSERVE-'+observation+'.json')),'original_lossless_observation':raw['original_canonical_identity'],
        'snapshot_accepted_grid_parents':obs['accepted_grid_parents'],'snapshot_terminal_GPU_charge':obs['GPU_terminal_all_attempts_seconds'],
        'snapshot_live_elapsed_NOT_final':obs['GPU_live_elapsed_not_final_seconds'],
        'snapshot_full_remaining_maxima_plus_terminal':obs['GPU_full_remaining_maxima_plus_terminal'],
        'manual_R008_preserved_if_present':identity(DOC/'OBSERVE-R008.json') if (DOC/'OBSERVE-R008.json').exists() else None,
        'new_test_receipt':identity(testpath),'original_V2_cleanup':cleanup,
        'all_new_local_auxiliary_bytes_before_final_compact_receipts':total,
        'new_non_monitor_source_doc_bundle_bytes_before_final_compact_receipts':bundle,'final_receipt_forward_allowance_bytes':200000,
        'auxiliary_subreservations':AUX_RESERVATIONS,'actual_whole_study_alllogicalcopies_preparation_volume_proof_passed':False,
        'network_WSL_cluster_SSD_or_scientific_queries_by_this_audit':0,'actual_final_CPU_analysis_studyarchive_fullSSD_run':False,
        'source_frozen_or_published':False,'final_gate_ready':False}
    write_new(output,result,limit=64000)
    print(json.dumps({k:v for k,v in result.items() if k!='source'}))


if __name__=='__main__':main()
