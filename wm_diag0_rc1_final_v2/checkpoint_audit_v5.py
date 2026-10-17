"""Checkpoint007 local source/charge/transport disposition audit only."""
import ast,base64,hashlib,json,stat,sys
from pathlib import Path
from wm_diag0_rc1_completion_v1.common import ROOT,DOC,CAPS,identity,write_new,charge
from .preservation_budget_v1 import SOURCE_DOC_BUNDLE_LIMIT,AUX_RESERVATIONS
from .transport_disposition_v1 import FAILURE


def main():
    label=sys.argv[1]
    if not label.isalnum():raise ValueError('exclusive audit label')
    paths=[p for p in DOC.glob('LOCAL-*.json') if not p.name.endswith('.started.json')]
    rows=[json.loads(p.read_text()) for p in paths]
    starts=[p for p in DOC.glob('LOCAL-*.started.json') if not (DOC/p.name.replace('.started.json','.json')).exists()]
    if [p.name for p in starts]!=['LOCAL-'+label+'.started.json']:raise ValueError('no other ambiguous LOCAL start')
    own=json.loads(starts[0].read_text())
    if own['component']!='handoff' or own['reserved_seconds']!=30:raise ValueError('exact handoff30 reservation')
    charges={k:sum(charge(r) for r in rows if r['component']==k) for k in CAPS};charges['handoff']+=30
    if any(charges[k]>CAPS[k] for k in CAPS) or sum(charges.values())>21600:raise ValueError('unchanged component/total caps')
    source={};roots=[]
    for package in ('wm_diag0_rc1_completion_v1','wm_diag0_rc1_final_v2','wm_diag0_rc1_monitor_v2'):
        roots.append(ROOT/package)
        for p in (ROOT/package).glob('*.py'):
            ast.parse(p.read_text(),feature_version=(3,6));source[p.relative_to(ROOT).as_posix()]=identity(p)
    finaldoc=ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016';mondoc=ROOT/'docs/world-model-diagnostic-rc1-monitor-v2-20261016'
    roots.extend((DOC,finaldoc,mondoc));monitor=set(DOC.glob('OBSERVE-R*.json'))
    for p,z in zip(paths,rows):
        if z['component']=='monitoring':monitor.update((p,DOC/p.name.replace('.json','.started.json')))
    total=bundle=0
    for root in roots:
        for p in root.rglob('*'):
            s=p.lstat()
            if stat.S_ISLNK(s.st_mode) or getattr(s,'st_file_attributes',0)&0x400:raise ValueError('no new auxiliary redirect')
            if stat.S_ISREG(s.st_mode):
                total+=s.st_size
                if p not in monitor:bundle+=s.st_size
            elif not stat.S_ISDIR(s.st_mode):raise ValueError('ordinary auxiliary files and dirs')
    if total+200000>20000000 or bundle+200000>SOURCE_DOC_BUNDLE_LIMIT or sum(AUX_RESERVATIONS.values())!=63928640:
        raise ValueError('20MB local/4.5MB source bundle/64MB prospective all-copy reservation')
    pub=json.loads((mondoc/'SSD-VERIFIED-001.json').read_text())
    for n,want in pub['working_source_members'].items():
        if identity(ROOT/n)!=want:raise ValueError('published monitor source changed')
    receipt=finaldoc/'ARTIFICIAL-TERMINAL-ENTRY-001.json';test=json.loads(receipt.read_text())
    for n,want in test['source'].items():
        if identity(ROOT/'wm_diag0_rc1_final_v2'/n)!=want:raise ValueError('new tested source changed')
    if test['final_gate_ready'] is not False or test['actual_final_CPU_analysis_archive_or_SSD_run'] is not False:raise ValueError('no synthetic readiness promotion')
    if identity(DOC/'OBSERVE-R006.failure.json')!=FAILURE:raise ValueError('preserved exact failed observation')
    z=json.loads((DOC/'OBSERVE-R006.failure.json').read_text());stdout=z['captured']['stdout']
    raw=base64.b64decode(stdout['retained_prefix_base64'],validate=True)
    if len(raw)!=646 or hashlib.sha256(raw).hexdigest()!=stdout['sha256'] or stdout['truncated']:raise ValueError('full exact diagnostic retained')
    text=raw.decode('utf-16-le')
    if 'D:\\WSL\\Thesis-Ubuntu\\ext4.vhdx' not in text or 'MountDisk/ERROR_PATH_NOT_FOUND' not in text:raise ValueError('exact WSL path blocker evidence')
    blocker=finaldoc/'TRANSPORT-PATH-BLOCKER-007.json';b=json.loads(blocker.read_text())
    if b['evidence']['failure']!=FAILURE or b['new_network_WSL_cluster_SSD_or_research_calls']!=0:raise ValueError('local-only disposition')
    cleanup=identity(ROOT/'wm_diag0_rc1_final_v1/cpu_process_v2.py')
    if cleanup!={'bytes':8269,'sha256':'13f3d73a8a83b3f561b331836e02c110b4db064d428e6bb70728c113e20a0672'}:raise ValueError('original V2 cleanup unchanged')
    checks=sum(r['component']=='monitoring' for r in rows)
    result={'status':'CHECKPOINT007_LOCAL_PREFLIGHT_PREPARATION_AND_WSL_PATH_BLOCKER_AUDITED_NOT_FINAL_GATE',
        'source':source,'component_charged_including_this_reserved_audit':charges,'total_charged':sum(charges.values()),
        'remaining':21600-sum(charges.values()),'remaining_components':{k:CAPS[k]-charges[k] for k in CAPS},
        'monitor_checks_used':checks,'remaining_checks':240-checks,'new_scheduled_observation_attempts_this_wake':1,
        'second_WSL_or_scheduler_query_after_failure':False,'current_cluster_health':'UNVERIFIED',
        'observation_failure':FAILURE,'local_transport_disposition':identity(blocker),'new_targeted_test':identity(receipt),
        'all_new_local_auxiliary_bytes_before_final_compact_receipts':total,
        'new_non_monitor_source_doc_bundle_bytes_before_final_compact_receipts':bundle,
        'final_compact_receipt_forward_allowance_bytes':200000,
        'source_doc_bundle_limit':SOURCE_DOC_BUNDLE_LIMIT,'auxiliary_subreservations':AUX_RESERVATIONS,
        'actual_whole_study_all_logical_copies_preparation_volume_proof_passed':False,
        'published_observer_changed':False,'original_V2_cleanup':cleanup,
        'new_network_cluster_WSL_SSD_or_scientific_query_by_audit':False,
        'source_frozen_or_published':False,'actual_final_CPU_analysis_study_archive_full_SSD_run':False,'final_gate_ready':False}
    write_new(DOC/'CHECKPOINT-AUDIT-007.json',result,limit=64000)
    print(json.dumps({k:v for k,v in result.items() if k!='source'}))


if __name__=='__main__':main()
