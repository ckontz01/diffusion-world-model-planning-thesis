"""Strict R3 scope, authenticated R1/R2 failure lineage and exact carried suppliers."""
from pathlib import Path
import json
from dtv_success_cost.common import *
from dtv_success_cost_r2 import common as prior
from dtv_success_cost_r1.common import STOP_SHA,LEDGER_SHA,SEAL_SHA,AUTH_SHA,ROW
RECOVERY=Path(__file__).resolve().parents[1]
HERE=RECOVERY/'docs/dtv-success-cost-publication-20261001/recovery-r3'
MANIFEST=HERE/'PACKAGE-MANIFEST.json';LINEAGE=HERE/'LINEAGE.json'
CARRIED_IDS=['312921','312922','312923','312925','312926','312927']
FAILED_ID='312928';FAILED_SECONDS=38
events=prior.events;terminal_row=prior.terminal_row
def location(run):return Path(run)/'recovery-r3'
def output_root(run,job):
    carried={x['task']:x for x in load(LINEAGE)['carried']}
    if job['id'] not in carried:return location(run)/'workers'
    return Path(run) if carried[job['id']]['output_lineage']=='original' else Path(run)/'recovery-r2/workers'
def authenticate_history(run):
    old=prior.authenticate_history(run);l=load(LINEAGE);root=Path(run)/'recovery-r2'
    for name,key in [('STOP-R2.json','r2_stop_sha256'),('DISPATCH-R2.jsonl','r2_dispatch_sha256'),('STOP-RESOLUTION.json','r2_resolution_sha256')]:
        if sha(root/name)!=l[key]:raise RuntimeError('R2 STOP/ledger/resolution changed')
    history=events(root/'DISPATCH-R2.jsonl')
    submitted=[x for x in history if x['event']=='submitted'];terminal=[x for x in history if x['event']=='terminal'];accepted=[x for x in history if x['event']=='accepted']
    expected=l['carried'][3:]
    if [x['task'] for x in history if x['event']=='submission_intent']!=[x['task'] for x in expected]+[l['failed_task']] or [x['allocation_id'] for x in submitted]!=CARRIED_IDS[3:]+[FAILED_ID] or len(terminal)!=4 or [x['task'] for x in accepted]!=[x['task'] for x in expected]:
        raise RuntimeError('unresolved/live/ambiguous/duplicate R2 work')
    for i,(s,t) in enumerate(zip(submitted,terminal)):
        state='COMPLETED' if i<3 else 'FAILED';code='0:0' if i<3 else '1:0';elapsed=[74,61,67,19][i]
        if (t['task'],t['allocation_id'],t['state'],t['exit'],t['elapsed_seconds'])!=(s['task'],s['allocation_id'],state,code,elapsed):raise RuntimeError('R2 terminal identity/charge differs')
        raw=[x for x in history if x['event']=='scheduler' and x.get('allocation_id')==s['allocation_id']]
        terminal_row(raw[-1],s['allocation_id'],s['task'],state,code,elapsed)
        if i<3:
            d=root/'workers'/s['task'];read_seal(d,s['task'])
            if sha(d/'SEAL.json')!=expected[i]['seal_sha256'] or accepted[i]['seal_sha256']!=expected[i]['seal_sha256']:raise RuntimeError('R2 carried successful supplier changed')
            from dtv_success_cost_r2.render import verify_evidence
            verify_evidence(d)
    failed=root/'workers'/l['failed_task']
    if {p.name for p in failed.iterdir()}!={x['path'] for x in l['failed_members']}:raise RuntimeError('failed Cube inventory changed')
    for x in l['failed_members']:
        p=failed/x['path']
        if p.stat().st_size!=x['bytes'] or sha(p)!=x['sha256']:raise RuntimeError('failed Cube evidence changed')
    return old,history
def verify_resolution(run,r):
    if (location(run)/'STOP-R3.json').exists():raise RuntimeError('new unresolved R3 STOP; never ignore or restart')
    authenticate_history(run);value=load(location(run)/'STOP-RESOLUTION.json');l=load(LINEAGE)
    expected=dict(original_stop_sha256=STOP_SHA,r1_stop_sha256=prior.R1_STOP,r2_stop_sha256=l['r2_stop_sha256'],
        r2_dispatch_sha256=l['r2_dispatch_sha256'],recovery_manifest_sha256=r['recovery_manifest_sha256'],authorization_sha256=r['authorization_sha256'],
        lineage_sha256=sha(LINEAGE),gpu_seconds=395,cpu_seconds=178,failed_allocations=['312924','312928'],
        replacement_task=l['failed_task'],successful_tasks_repeated=False,scientific_changes=False)
    if any(value.get(k)!=v for k,v in expected.items()) or not isinstance(value.get('observed_unix'),(int,float)):raise RuntimeError('dated R3 resolution differs')
    return value
def recovery_gate(approval):
    r=load(approval)
    if r.get('study')!='DTV-EFF1-R3' or r.get('execute') is not True:raise RuntimeError('R3 execution disabled')
    if sha(MANIFEST)!=r.get('recovery_manifest_sha256') or sha(LINEAGE)!=r.get('lineage_sha256'):raise RuntimeError('R3 closure differs')
    for row in load(MANIFEST)['files']:
        p=(RECOVERY/row['path']).resolve()
        if not p.is_relative_to(RECOVERY) or p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise RuntimeError('R3 source changed')
    authority=Path(r['authorization_record'])
    if sha(authority)!=r['authorization_sha256']:raise RuntimeError('R3 authority changed')
    a=load(authority)
    if any(a.get(k)!=v for k,v in r.items() if k not in ('authorization_record','authorization_sha256')):raise RuntimeError('R3 scope differs')
    if (r['remaining_gpu_workers'],r['remaining_cpu_analysis'],r['replacement_allowance'],r['carried_gpu_seconds'],r['carried_cpu_seconds'],r['scientific_changes'],r['resource_expansion'])!=(2874,1,1,395,178,False,False):raise RuntimeError('finite R3 scope differs')
    if sha(r['worker_approval'])!='8768e82f12746010f460d0e45ed29d58dc21e98375c04fb574cf722116d34c03':raise RuntimeError('original worker capability changed')
    c=gate(Path(r['worker_approval']))
    if str(ROOT)!=r['scientific_source'] or str(RECOVERY)!=r['recovery_source'] or str(run_namespace(c))!=r['run']:raise RuntimeError('exclusive R3 binding differs')
    for key,part,digest in [('r1_source','recovery-r1','61b46d8e206a078310e2f7a39eda58417f299a317efbc9b92473af3edfb48ad9'),('r2_source','recovery-r2','cb86f64c3c558218eeec2cfc2cfa866cba67aeb67653bd72f6030293c8df2dbd')]:
        root=Path(r[key]);manifest=root/'docs/dtv-success-cost-publication-20261001'/part/'PACKAGE-MANIFEST.json'
        if sha(manifest)!=digest:raise RuntimeError('accepted control dependency manifest changed')
        for row in load(manifest)['files']:
            if sha(root/row['path'])!=row['sha256']:raise RuntimeError('accepted control dependency bytes changed')
    verify_resolution(run_namespace(c),r);return c,r
