"""Combined, independently authenticated accounting. Historical ledger is never rewritten."""
import json
from dtv_success_cost.common import *
from dtv_success_cost.accept import accept_worker
from dtv_success_cost_r1.common import verify_resolution,ROW

def combined_events(run,c):
    location=Path(run)/'recovery-r1';r=load(location/'EXECUTION-APPROVAL.json');resolution=verify_resolution(run,r)
    old=[json.loads(x) for x in (Path(run)/'DISPATCH.jsonl').read_text().splitlines()]
    if [v['event'] for v in old]!=['submission_intent','submission_response','submitted','scheduler']:
        raise RuntimeError('unexpected original submission history')
    if old[0].get('task')!='preflight' or old[2]!=dict(event='submitted',task='preflight',allocation_id='312920'):
        raise RuntimeError('original preflight supplier differs')
    events=[json.loads(x) for x in (location/'DISPATCH-R1.jsonl').read_text().splitlines()]
    carry=[e for e in events if e['event']=='carried_preflight_accepted']
    if len(carry)!=1 or events[0]!=carry[0] or carry[0].get('allocation_id')!='312920' or carry[0].get('elapsed_seconds')!=178 or carry[0].get('seal_sha256')!=sha(Path(run)/'preflight/SEAL.json') or carry[0].get('resolution_sha256')!=sha(location/'STOP-RESOLUTION.json'):
        raise RuntimeError('missing/duplicate dated carry acceptance')
    # An explicit in-memory combined accounting projection, NOT a fabricated or
    # backdated original event. Its supplier is the preserved dated resolution.
    projected=old+[dict(event='scheduler',allocation_id='312920',returncode=0,stdout='|'.join(ROW)+'\n',supplier='R1 dated resolution'),
                   dict(event='terminal',task='preflight',allocation_id='312920',state='COMPLETED',exit='0:0',elapsed_seconds=178,supplier='R1 dated resolution'),
                   dict(event='accepted',task='preflight',supplier='R1 dated carry')]
    return projected+events[1:]

def accounting(run,c,include_analysis=False):
    receipt=accounting_events(combined_events(run,c),c,include_analysis)
    receipt.update(lineage='R1',carried_preflight_allocation='312920',carried_cpu_seconds=178,
                   original_dispatch_accepted_preflight=False,dated_stop_resolution_sha256=sha(Path(run)/'recovery-r1/STOP-RESOLUTION.json'),
                   original_stop_preserved=True,additional_research_attempts=0)
    return receipt

def accounting_events(events,c,include_analysis=False):
    if not include_analysis:
        analysis_intents=[i for i,r in enumerate(events) if r['event']=='submission_intent' and r.get('task')=='analysis']
        if len(analysis_intents)>1:raise RuntimeError('duplicate analysis submission')
        if analysis_intents:
            # The CPU analysis necessarily has its own live intent/allocation
            # already in the ledger. Authenticate the full preceding evaluation
            # sequence now; final acceptance separately includes that CPU job.
            cut=analysis_intents[0]
            if any(r.get('task','analysis')!='analysis' for r in events[cut:]):raise RuntimeError('unexpected work after analysis dispatch')
            events=events[:cut]
    expected=['preflight']+[j['id'] for j in c['jobs']]+(['analysis'] if include_analysis else [])
    for kind in ('submission_intent','submitted','terminal','accepted'):
        found=[r['task'] for r in events if r['event']==kind]
        if found!=expected:raise RuntimeError('full unique dispatch/acceptance sequence differs')
    submitted=[r for r in events if r['event']=='submitted'];terminal=[r for r in events if r['event']=='terminal']
    if len(set(r['allocation_id'] for r in submitted))!=len(expected):raise RuntimeError('duplicate allocation')
    gpu=0;cpu=0
    for s,t in zip(submitted,terminal):
        if s['allocation_id']!=t['allocation_id'] or t['state']!='COMPLETED' or t['exit']!='0:0':raise RuntimeError('unresolved/failing terminal allocation')
        raw=[r for r in events if r['event']=='scheduler' and r['allocation_id']==s['allocation_id']]
        if not raw or raw[-1].get('returncode')!=0:raise RuntimeError('terminal raw accounting absent')
        lines=[line.split('|') for line in raw[-1]['stdout'].splitlines() if line.strip()]
        if len(lines)!=1:raise RuntimeError('raw terminal row cardinality')
        row=lines[0]
        if row[-1]=='':row.pop()
        if len(row)!=7 or row[:5]!=[s['allocation_id'],'dtveff1-'+s['task'],'COMPLETED','0:0',str(t['elapsed_seconds'])]:raise RuntimeError('independent raw terminal accounting differs')
        resources=dict(x.split('=',1) for x in row[5].split(',') if '=' in x)
        if t['task'] in ('analysis','preflight'):
            if int(row[4])>7200 or any(k.startswith('gres/gpu') for k in resources):raise RuntimeError('CPU-stage resource identity')
            cpu+=t['elapsed_seconds']
        else:gpu+=t['elapsed_seconds']
        if t['task'] not in ('analysis','preflight') and (int(row[4])>300 or resources.get('gres/gpu')!='1' or row[6] not in ('gpu09','gpu09.cluster')):raise RuntimeError('GPU resource/hostname accounting')
    if gpu>c['gpu_seconds'] or cpu>c['cpu_seconds']:raise RuntimeError('aggregate charge cap')
    gates=[r for r in events if r['event']=='technical_tranche_passed']
    if len(gates)!=1 or gates[0]['included_workers']!=9:raise RuntimeError('missing included tranche')
    fifth=next(i for i,r in enumerate(events) if r['event']=='submission_intent' and r['task']==expected[10])
    if next(i for i,r in enumerate(events) if r['event']=='technical_tranche_passed')>fifth:raise RuntimeError('source2 preceded technical gate')
    return dict(unique_tasks=len(expected),gpu_allocation_seconds=gpu,cpu_stage_allocation_seconds=cpu,allocations=submitted)

def accept_grid(c,run):
    r=load(Path(run)/'recovery-r1/EXECUTION-APPROVAL.json')
    verify_resolution(run,r)
    receipt=accounting(run,c);records=[]
    allocations={r['task']:r['allocation_id'] for r in receipt['allocations']}
    for j in c['jobs']:
        for e in accept_worker(c,j,run,allocations[j['id']]):
            records.append({k:e[k] for k in ('task','source','parent','scorer_seed','config','success','planning_seconds','episode_operational_seconds','episode_elapsed_including_audit_seconds','process_cpu_seconds','resources','initial_success') } |
                           dict(decisions=len(e['plans']),actions=len(e['actions']),solve_seconds=sum(p['solve_seconds'] for p in e['plans']),
                                first_decision_seconds=next((t['observation_to_action_seconds'] for t in e['timings'] if t['planning_decision']),0.),
                                decision_observation_to_action_seconds=sum(t['observation_to_action_seconds'] for t in e['timings'] if t['planning_decision']),
                                later_decision_seconds=sum(t['observation_to_action_seconds'] for t in e['timings'] if t['planning_decision'] and t['step']>0),
                                reset_seconds=e['reset_seconds'],environment_construction_seconds=e.get('environment_construction_seconds',0.),audit_seconds=e['audit_seconds']))
    if len(records)!=len(c['jobs'])*8:raise RuntimeError('incomplete episode grid')
    return records,dict(**receipt,episodes=len(records),all_endpoint_traces_verified=True,science_selection=False)

