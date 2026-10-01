"""Strict separate R2 capability, preserved lineage, and one failed-work replacement."""
from pathlib import Path
import json
from dtv_success_cost.common import *
from dtv_success_cost_r1.common import STOP_SHA,LEDGER_SHA,SEAL_SHA,AUTH_SHA,ROW
RECOVERY=Path(__file__).resolve().parents[1]
HERE=RECOVERY/'docs/dtv-success-cost-publication-20261001/recovery-r2'
MANIFEST=HERE/'PACKAGE-MANIFEST.json'
LINEAGE=HERE/'LINEAGE.json'
R1_STOP='6b732ef3492739127bed9abd44042bf574ccf15f3ea657ab12eeea1fe1c3f8cb'
R1_LEDGER='309dd6f2d5bbb01cbf811fca23116e02234528374d1551500fa921b823a57d19'
R1_RESOLUTION='aae9e28b83237a261811bcf6a41bca7a08c3f192fb96e086510b5932a4ec7a9e'
CARRIED_IDS=['312921','312922','312923']
FAILED_ID='312924'
FAILED_SECONDS=19
def location(run):return Path(run)/'recovery-r2'
def output_root(run,job):
    return Path(run) if job['id'] in {j['task'] for j in load(LINEAGE)['carried']} else location(run)/'workers'
def events(path):return [json.loads(x) for x in Path(path).read_text().splitlines()]
def terminal_row(raw,allocation,task,state,exit,elapsed):
    rows=[x.split('|') for x in raw['stdout'].splitlines() if x.strip()]
    if raw.get('returncode')!=0 or len(rows)!=1:raise RuntimeError('independent terminal row missing')
    row=rows[0]
    if row[-1]=='':row.pop()
    if len(row)!=7 or row[:5]!=[allocation,'dtveff1-'+task,state,exit,str(elapsed)]:raise RuntimeError('terminal accounting identity differs')
    res=dict(x.split('=',1) for x in row[5].split(',') if '=' in x)
    if res.get('cpu')!='4' or res.get('mem')!='8G':raise RuntimeError('CPU/RAM allocation changed')
    if task=='preflight':
        if any(k.startswith('gres/gpu') for k in res) or elapsed>7200:raise RuntimeError('CPU allocation changed')
    elif res.get('gres/gpu')!='1' or row[6] not in ('gpu09','gpu09.cluster') or elapsed>300:raise RuntimeError('GPU resource identity differs')
    return row
def authenticate_history(run):
    run=Path(run);l=load(LINEAGE)
    for path,digest in [(run/'STOP.json',STOP_SHA),(run/'DISPATCH.jsonl',LEDGER_SHA),
                        (run/'preflight/SEAL.json',SEAL_SHA),(run/'preflight/INPUT-AUTHENTICATION.json',AUTH_SHA),
                        (run/'recovery-r1/STOP-R1.json',R1_STOP),(run/'recovery-r1/DISPATCH-R1.jsonl',R1_LEDGER),
                        (run/'recovery-r1/STOP-RESOLUTION.json',R1_RESOLUTION)]:
        if sha(path)!=digest:raise RuntimeError('historical STOP/ledger/receipt changed')
    read_seal(run/'preflight','preflight')
    prior=events(run/'recovery-r1/DISPATCH-R1.jsonl')
    logical=[x['task'] for x in prior if x['event']=='submission_intent']
    expected=[x['task'] for x in l['carried']]+[l['failed_task']]
    if logical!=expected:raise RuntimeError('historical task intent differs')
    submitted=[x for x in prior if x['event']=='submitted'];terminal=[x for x in prior if x['event']=='terminal']
    accepted=[x for x in prior if x['event']=='accepted']
    if [x['allocation_id'] for x in submitted]!=CARRIED_IDS+[FAILED_ID] or len(terminal)!=4 or [x['task'] for x in accepted]!=expected[:3]:
        raise RuntimeError('unresolved/ambiguous or duplicate prior attempt')
    for i,(s,t) in enumerate(zip(submitted,terminal)):
        state='COMPLETED' if i<3 else 'FAILED';exit='0:0' if i<3 else '1:0';seconds=[50,59,46,19][i]
        if (t['task'],t['allocation_id'],t['state'],t['exit'],t['elapsed_seconds'])!=(s['task'],s['allocation_id'],state,exit,seconds):
            raise RuntimeError('historical terminal changed')
        raw=[x for x in prior if x['event']=='scheduler' and x.get('allocation_id')==s['allocation_id']]
        terminal_row(raw[-1],s['allocation_id'],s['task'],state,exit,seconds)
        if i<3:
            read_seal(run/s['task'],s['task'])
            if sha(run/s['task']/'SEAL.json')!=l['carried'][i]['seal_sha256'] or accepted[i]['seal_sha256']!=l['carried'][i]['seal_sha256']:
                raise RuntimeError('successful carried seal differs')
    failed=run/l['failed_task']
    if {p.name for p in failed.iterdir()}!={r['path'] for r in l['failed_members']}:raise RuntimeError('failed partial inventory changed')
    for row in l['failed_members']:
        p=failed/row['path']
        if p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise RuntimeError('failed evidence changed')
    return prior
def verify_resolution(run,r):
    if (location(run)/'STOP-R2.json').exists():raise RuntimeError('new unresolved R2 STOP; never ignore/restart')
    authenticate_history(run)
    value=load(location(run)/'STOP-RESOLUTION.json')
    expected=dict(original_stop_sha256=STOP_SHA,r1_stop_sha256=R1_STOP,r1_dispatch_sha256=R1_LEDGER,
                  recovery_manifest_sha256=r['recovery_manifest_sha256'],authorization_sha256=r['authorization_sha256'],
                  lineage_sha256=sha(LINEAGE),gpu_seconds=174,cpu_seconds=178,failed_allocation='312924',
                  replacement_task=load(LINEAGE)['failed_task'],successful_tasks_repeated=False,scientific_changes=False)
    if any(value.get(k)!=v for k,v in expected.items()) or not isinstance(value.get('observed_unix'),(int,float)):
        raise RuntimeError('dated R2 fault resolution differs')
    return value
def recovery_gate(approval):
    r=load(approval)
    if r.get('study')!='DTV-EFF1-R2' or r.get('execute') is not True:raise RuntimeError('R2 execution disabled')
    if sha(MANIFEST)!=r.get('recovery_manifest_sha256') or sha(LINEAGE)!=r.get('lineage_sha256'):raise RuntimeError('R2 freeze changed')
    for row in load(MANIFEST)['files']:
        p=(RECOVERY/row['path']).resolve()
        if not p.is_relative_to(RECOVERY) or p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise RuntimeError('R2 source changed')
    authority=Path(r['authorization_record'])
    if sha(authority)!=r['authorization_sha256']:raise RuntimeError('R2 authority changed')
    a=load(authority)
    if any(a.get(k)!=v for k,v in r.items() if k not in ('authorization_record','authorization_sha256')):raise RuntimeError('R2 authority scope differs')
    if (r['remaining_gpu_workers'],r['remaining_cpu_analysis'],r['replacement_allowance'],r['carried_gpu_seconds'],r['carried_cpu_seconds'],r['scientific_changes'],r['resource_expansion'])!=(2877,1,1,174,178,False,False):
        raise RuntimeError('finite recovery scope changed')
    if sha(r['worker_approval'])!='8768e82f12746010f460d0e45ed29d58dc21e98375c04fb574cf722116d34c03':raise RuntimeError('original capability changed')
    c=gate(Path(r['worker_approval']))
    if str(ROOT)!=r['scientific_source'] or str(RECOVERY)!=r['recovery_source'] or str(run_namespace(c))!=r['run']:raise RuntimeError('exclusive R2 binding changed')
    r1=Path(r['r1_source']);manifest=r1/'docs/dtv-success-cost-publication-20261001/recovery-r1/PACKAGE-MANIFEST.json'
    if sha(manifest)!='61b46d8e206a078310e2f7a39eda58417f299a317efbc9b92473af3edfb48ad9':raise RuntimeError('accepted R1 control dependency changed')
    for row in load(manifest)['files']:
        if sha(r1/row['path'])!=row['sha256']:raise RuntimeError('R1 dependency bytes changed')
    verify_resolution(run_namespace(c),r)
    return c,r

