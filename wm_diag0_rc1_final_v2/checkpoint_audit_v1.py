"""Compact local checkpoint accounting/source audit, not a study gate."""
import ast,json,stat,sys
from pathlib import Path
from wm_diag0_rc1_completion_v1.common import ROOT,DOC,CAPS,identity,write_new,charge


def main():
    label=sys.argv[1]
    if not label.isalnum():raise ValueError('exact owned handoff label')
    starts={p.name:p for p in DOC.glob('LOCAL-*.started.json')}
    rows=[json.loads(p.read_text()) for p in DOC.glob('LOCAL-*.json') if not p.name.endswith('.started.json')]
    ambiguous=[n for n in starts if not (DOC/n.replace('.started.json','.json')).exists()]
    if ambiguous!=['LOCAL-'+label+'.started.json']:raise ValueError('only this active audit may be unpaired')
    own=json.loads(starts[ambiguous[0]].read_text())
    if own['component']!='handoff' or own['reserved_seconds']!=30:raise ValueError('exact already-reserved local audit')
    charged={k:sum(charge(r) for r in rows if r['component']==k) for k in CAPS}
    charged['handoff']+=30
    if any(charged[k]>CAPS[k] for k in CAPS):raise ValueError('no component overrun or transfer')
    used=sum(charged.values())
    if used>21600:raise ValueError('full approved future envelope')
    sources={}
    folder=ROOT/'wm_diag0_rc1_final_v2'
    for p in folder.glob('*.py'):
        ast.parse(p.read_text(),feature_version=(3,6));sources[p.name]=identity(p)
    total=0
    # Count BOTH completion and all new final-V2 code/docs, not merely the
    # completion runner's own small control directories. Remaining44MB still
    # reserved for remote/portable/SSD logical copies, no deduplication claim.
    for root in (DOC,ROOT/'wm_diag0_rc1_completion_v1',folder,ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016'):
        for p in root.rglob('*'):
            s=p.lstat()
            if stat.S_ISLNK(s.st_mode) or getattr(s,'st_file_attributes',0)&0x400:raise ValueError('no new local auxiliary redirect')
            if stat.S_ISREG(s.st_mode):total+=s.st_size
            elif not stat.S_ISDIR(s.st_mode):raise ValueError('ordinary new auxiliary only')
    if total+200000>20000000:raise ValueError('full local20MB allocation with forward compact receipt bound')
    artifact=ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016/HISTORICAL-USAGE-001.json'
    h=json.loads(artifact.read_text())
    if len(h['evidence'])!=56 or h['baseline_encoded_frames_all_six_fits_and_failed_diagnostics']!=2317 or not h['independently_authenticated']:raise ValueError('actual complete historical receipt required')
    result={'status':'LOCAL_CHECKPOINT_SOURCE_ACCOUNTING_AUDIT_NOT_FINAL_GATE',
            'component_charged_including_this_reserved_audit':charged,'total_charged':used,'remaining':21600-used,
            'remaining_component_full_reservations':{k:CAPS[k]-charged[k] for k in CAPS},
            'monitor_checks_used':sum(r['component']=='monitoring' for r in rows),
            'all_new_local_auxiliary_bytes_before_last_compact_receipts':total,
            'local_auxiliary_allocation':20000000,'all_new_auxiliary_logical_copies_reservation':64000000,
            'source':sources,'historical_usage_receipt':identity(artifact),
            'native_receiver_test001':identity(ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016/ARTIFICIAL-NATIVE-RECEIVER-001.json'),
            'native_receiver_test002':identity(ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016/ARTIFICIAL-NATIVE-RECEIVER-002.json'),
            'actual_final_source_published':False,'actual_final_analysis_archive_SSD_executed':False,
            'research_values_read':False,'fresh_whole_study_storage_proof':False,'final_gate_ready':False}
    write_new(DOC/'CHECKPOINT-AUDIT-003.json',result,limit=64000)
    print(json.dumps({k:v for k,v in result.items() if k!='source'}))


if __name__=='__main__':main()
