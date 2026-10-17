"""Local checkpoint004 source/charge/all-new-aux audit; no cluster/SSD queries."""
import ast,json,stat,sys
from pathlib import Path
from wm_diag0_rc1_completion_v1.common import ROOT,DOC,CAPS,identity,write_new,charge


def main():
    label=sys.argv[1]
    if not label.isalnum():raise ValueError('exclusive owned checkpoint label')
    rows=[json.loads(p.read_text()) for p in DOC.glob('LOCAL-*.json') if not p.name.endswith('.started.json')]
    ambiguous=[p for p in DOC.glob('LOCAL-*.started.json') if not (DOC/p.name.replace('.started.json','.json')).exists()]
    if [p.name for p in ambiguous]!=['LOCAL-'+label+'.started.json']:raise ValueError('only this bounded audit may have an unpaired LOCAL start')
    own=json.loads(ambiguous[0].read_text())
    if own['component']!='handoff' or own['reserved_seconds']!=30:raise ValueError('exact prospective30second audit')
    charged={k:sum(charge(r) for r in rows if r['component']==k) for k in CAPS};charged['handoff']+=30
    if any(charged[k]>CAPS[k] for k in CAPS) or sum(charged.values())>21600:raise ValueError('full existing component/total finite reservations')
    sources={};roots=[]
    for package in ('wm_diag0_rc1_completion_v1','wm_diag0_rc1_final_v2','wm_diag0_rc1_monitor_v2'):
        root=ROOT/package;roots.append(root)
        for p in root.glob('*.py'):
            ast.parse(p.read_text(),feature_version=(3,6));sources[str(p.relative_to(ROOT)).replace('\\','/')]=identity(p)
    roots += [DOC,ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016',ROOT/'docs/world-model-diagnostic-rc1-monitor-v2-20261016']
    total=0
    for root in roots:
        for p in root.rglob('*'):
            s=p.lstat()
            if stat.S_ISLNK(s.st_mode) or getattr(s,'st_file_attributes',0)&0x400:raise ValueError('no new auxiliary redirects')
            if stat.S_ISREG(s.st_mode):total+=s.st_size
            elif not stat.S_ISDIR(s.st_mode):raise ValueError('ordinary new auxiliaries only')
    if total+200000>20000000:raise ValueError('all-new local20MB allocation including both final and monitor packages')
    monitor=ROOT/'docs/world-model-diagnostic-rc1-monitor-v2-20261016';pub=json.loads((monitor/'SSD-VERIFIED-001.json').read_text())
    if pub['status']!='MONITOR_V2_SOURCE_WHOLE_EVERY_MEMBER_VERIFIED' or pub['remote_full_hash']!=pub['source_commit']:raise ValueError('published/fullremote/native whole-every-member source gate')
    for n,want in pub['working_source_members'].items():
        if identity(ROOT/n)!=want:raise ValueError('published monitor source/authority changed')
    failed=json.loads((DOC/'LOCAL-RESUMEOBS003.json').read_text())
    if failed['status']!='CHILD_NONZERO' or failed['automatic_retry'] is not False or (DOC/'OBSERVE-R003.json').exists():raise ValueError('R003 failure retained, no fabricated observation')
    result={'status':'CHECKPOINT004_LOCAL_AUDIT_NOT_FINAL_GATE','source':sources,
            'component_charged_including_this_reserved_audit':charged,'total_charged':sum(charged.values()),
            'remaining':21600-sum(charged.values()),'remaining_components':{k:CAPS[k]-charged[k] for k in CAPS},
            'monitor_checks_used':sum(r['component']=='monitoring' for r in rows),
            'all_new_local_auxiliary_bytes_before_final_compact_receipts':total,'local_allocation':20000000,
            'all_new_auxiliary_all_logical_copy_reservation':64000000,
            'new_monitor_source_package':pub['whole'],'source_commit':pub['source_commit'],
            'R003_result':'unavailable; underlying transport code/stdout not retained by old entry; no cause inferred',
            'R003_retried':False,'current_cluster_health_verified':False,
            'last_successful_observation':identity(DOC/'OBSERVE-R002.json'),
            'historical_alias_binding':identity(ROOT/'docs/world-model-diagnostic-rc1-final-v2-20261016/RUNTIME-ALIASES-001.json'),
            'new_current_cluster_or_SSD_query_performed':False,'scientific_values_read':False,
            'actual_final_source_frozen_or_published':False,'final_study_gate_ready':False}
    write_new(DOC/'CHECKPOINT-AUDIT-004.json',result,limit=64000)
    print(json.dumps({k:v for k,v in result.items() if k!='source'}))


if __name__=='__main__':main()
