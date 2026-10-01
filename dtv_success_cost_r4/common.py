"""Authenticated R4 scope, carried suppliers and preserved R3 failure."""
from pathlib import Path
from dtv_success_cost.common import *
from dtv_success_cost_r3 import common as prior
RECOVERY=Path(__file__).resolve().parents[1]
HERE=RECOVERY/'docs/dtv-success-cost-publication-20261001/recovery-r4'
MANIFEST=HERE/'PACKAGE-MANIFEST.json';LINEAGE=HERE/'LINEAGE.json'
events=prior.events;terminal_row=prior.terminal_row
FAILED_IDS=['312924','312928','312950'];FAILED_SECONDS=59
def location(run):return Path(run)/'recovery-r4'
def output_root(run,job):
    if job['id'] in {x['task'] for x in load(LINEAGE)['carried']}:return Path(run)/'recovery-r3/workers'
    if job['id'] in {x['task'] for x in load(prior.LINEAGE)['carried']}:return prior.output_root(run,job)
    return location(run)/'workers'
def authenticate_history(run):
    r1,r2=prior.authenticate_history(run);l=load(LINEAGE);root=Path(run)/'recovery-r3'
    for name,key in [('STOP-R3.json','r3_stop_sha256'),('DISPATCH-R3.jsonl','r3_dispatch_sha256'),('STOP-RESOLUTION.json','r3_resolution_sha256')]:
        if sha(root/name)!=l[key]:raise RuntimeError('R3 STOP/ledger/resolution changed')
    history=events(root/'DISPATCH-R3.jsonl');ss=[x for x in history if x['event']=='submitted'];tt=[x for x in history if x['event']=='terminal'];aa=[x for x in history if x['event']=='accepted']
    expected=l['carried']
    if len(ss)!=22 or len(tt)!=22 or len(aa)!=21 or [x['task'] for x in history if x['event']=='submission_intent']!=[x['task'] for x in expected]+[l['failed_task']]:raise RuntimeError('unresolved/live/ambiguous R3 work')
    if [x['allocation_id'] for x in ss]!=[x['allocation_id'] for x in expected]+[l['failed_allocation']] or [x['task'] for x in aa]!=[x['task'] for x in expected]:raise RuntimeError('R3 supplier identity differs')
    for i,(s,t) in enumerate(zip(ss,tt)):
        ok=i<21;state='COMPLETED' if ok else 'FAILED';code='0:0' if ok else '1:0';elapsed=expected[i]['elapsed_seconds'] if ok else 21
        if (t['task'],t['allocation_id'],t['state'],t['exit'],t['elapsed_seconds'])!=(s['task'],s['allocation_id'],state,code,elapsed):raise RuntimeError('R3 terminal identity/charge differs')
        raw=[x for x in history if x['event']=='scheduler' and x.get('allocation_id')==s['allocation_id']]
        terminal_row(raw[-1],s['allocation_id'],s['task'],state,code,elapsed)
        if ok:
            d=root/'workers'/s['task'];read_seal(d,s['task'])
            if sha(d/'SEAL.json')!=expected[i]['seal_sha256'] or aa[i]['seal_sha256']!=expected[i]['seal_sha256']:raise RuntimeError('R3 successful supplier changed')
            from dtv_success_cost_r2.render import verify_evidence
            verify_evidence(d)
    if [x for x in history if x['event']=='technical_tranche_passed']!=l['technical_gate'] or len(l['technical_gate'])!=1:raise RuntimeError('historical included gate changed')
    gate_i=next(i for i,x in enumerate(history) if x['event']=='technical_tranche_passed')
    if gate_i>=next(i for i,x in enumerate(history) if x['event']=='submission_intent' and x['task']==expected[3]['task']):raise RuntimeError('source2 preceded gate')
    failed=root/'workers'/l['failed_task']
    if {p.name for p in failed.iterdir()}!={x['path'] for x in l['failed_members']}:raise RuntimeError('failed PushT inventory changed')
    for x in l['failed_members']:
        p=failed/x['path']
        if p.stat().st_size!=x['bytes'] or sha(p)!=x['sha256']:raise RuntimeError('failed PushT evidence changed')
    for x in l['error_logs']:
        p=Path(x['path'])
        if p.stat().st_size!=x['bytes'] or sha(p)!=x['sha256']:raise RuntimeError('preserved error log changed')
    if load(root/'STOP-R3.json')['charges']!=dict(gpu=1622,cpu=178):raise RuntimeError('R3 carried charges changed')
    return r1,r2,history
def resolution_fields(r):
    l=load(LINEAGE)
    return dict(r3_stop_sha256=l['r3_stop_sha256'],r3_dispatch_sha256=l['r3_dispatch_sha256'],r3_resolution_sha256=l['r3_resolution_sha256'],
        recovery_manifest_sha256=r['recovery_manifest_sha256'],authorization_sha256=r['authorization_sha256'],lineage_sha256=sha(LINEAGE),
        gpu_seconds=1622,cpu_seconds=178,failed_allocations=FAILED_IDS,replacement_task=l['failed_task'],successful_tasks_repeated=False,scientific_changes=False)
def verify_resolution(run,r):
    if (location(run)/'STOP-R4.json').exists():raise RuntimeError('new unresolved R4 STOP; never ignore or restart')
    authenticate_history(run);value=load(location(run)/'STOP-RESOLUTION.json')
    if any(value.get(k)!=v for k,v in resolution_fields(r).items()) or not isinstance(value.get('observed_unix'),(int,float)):raise RuntimeError('dated R4 resolution differs')
    return value
def recovery_gate(approval):
    r=load(approval)
    if r.get('study')!='DTV-EFF1-R4' or r.get('execute') is not True:raise RuntimeError('R4 execution disabled')
    if sha(MANIFEST)!=r.get('recovery_manifest_sha256') or sha(LINEAGE)!=r.get('lineage_sha256'):raise RuntimeError('R4 closure differs')
    for row in load(MANIFEST)['files']:
        p=(RECOVERY/row['path']).resolve()
        if not p.is_relative_to(RECOVERY) or p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise RuntimeError('R4 source changed')
    authority=Path(r['authorization_record'])
    if sha(authority)!=r['authorization_sha256'] or any(load(authority).get(k)!=v for k,v in r.items() if k not in ('authorization_record','authorization_sha256')):raise RuntimeError('R4 authority/scope changed')
    if (r['remaining_gpu_workers'],r['remaining_cpu_analysis'],r['replacement_allowance'],r['carried_gpu_seconds'],r['carried_cpu_seconds'],r['scientific_changes'],r['resource_expansion'])!=(2853,1,1,1622,178,False,False):raise RuntimeError('finite R4 scope differs')
    if sha(r['worker_approval'])!='8768e82f12746010f460d0e45ed29d58dc21e98375c04fb574cf722116d34c03':raise RuntimeError('original worker capability changed')
    c=gate(Path(r['worker_approval']))
    if str(ROOT)!=r['scientific_source'] or str(RECOVERY)!=r['recovery_source'] or str(run_namespace(c))!=r['run']:raise RuntimeError('exclusive R4 binding differs')
    for key,part,digest in [('r1_source','recovery-r1','61b46d8e206a078310e2f7a39eda58417f299a317efbc9b92473af3edfb48ad9'),('r2_source','recovery-r2','cb86f64c3c558218eeec2cfc2cfa866cba67aeb67653bd72f6030293c8df2dbd'),('r3_source','recovery-r3','a75d361f6e23fad93742498f92bc7cfd9e4d07e96644c7bfd6418ebf87db5e15')]:
        root=Path(r[key]);m=root/'docs/dtv-success-cost-publication-20261001'/part/'PACKAGE-MANIFEST.json'
        if sha(m)!=digest:raise RuntimeError('control dependency manifest changed')
        for row in load(m)['files']:
            if sha(root/row['path'])!=row['sha256']:raise RuntimeError('control dependency bytes changed')
    verify_resolution(run_namespace(c),r);return c,r
