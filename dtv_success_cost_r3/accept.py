"""Independent R3 accounting: preserved failed attempt plus exactly one supplier/task."""
from dtv_success_cost.common import *
from dtv_success_cost.accept import accept_worker
from dtv_success_cost_r1.accept import accounting_events
from dtv_success_cost_r3.common import *
from dtv_success_cost_r2.render import verify_evidence

def combined_events(run,c):
    r=load(location(run)/'EXECUTION-APPROVAL.json')
    resolution=verify_resolution(run,r);r1_history,r2_history=authenticate_history(run)
    old=events(Path(run)/'DISPATCH.jsonl')
    if [x['event'] for x in old]!=['submission_intent','submission_response','submitted','scheduler']:
        raise RuntimeError('original history changed')
    projected=old+[dict(event='scheduler',allocation_id='312920',returncode=0,stdout='|'.join(ROW)+'\n',supplier='R1 dated resolution'),
                   dict(event='terminal',task='preflight',allocation_id='312920',state='COMPLETED',exit='0:0',elapsed_seconds=178,supplier='R1 dated resolution'),
                   dict(event='accepted',task='preflight',supplier='R1 dated carry')]
    # Only the authenticated successful R1 attempt records enter the logical
    # grid. The unsuccessful attempt is accounted separately, never erased.
    carried=load(LINEAGE)['carried']
    for history,suppliers in [(r1_history,carried[:3]),(r2_history,carried[3:])]:
        ids={x['allocation_id'] for x in suppliers};tasks={x['task'] for x in suppliers}
        projected += [x for x in history if x.get('allocation_id') in ids or x.get('task') in tasks]
    current=events(location(run)/'DISPATCH-R3.jsonl')
    carry=dict(event='carried_history_accepted',gpu_seconds=395,cpu_seconds=178,
               allocations=['312920']+CARRIED_IDS,failed_allocations=['312924','312928'],
               lineage_sha256=sha(LINEAGE),resolution_sha256=sha(location(run)/'STOP-RESOLUTION.json'))
    if not current or any(current[0].get(k)!=v for k,v in carry.items()) or sum(x['event']=='carried_history_accepted' for x in current)!=1:
        raise RuntimeError('dated R3 carry acceptance differs')
    return projected+current[1:]

def accounting(run,c,include_analysis=False):
    projected=combined_events(run,c)
    receipt=accounting_events(projected,c,include_analysis)
    allocations=receipt['allocations'];actual=[dict(x) for x in allocations]
    if {'312924','312928'} & {x['allocation_id'] for x in actual}:raise RuntimeError('failed allocation reused')
    actual.insert(4,dict(event='submitted',task='reacher-4374-6101',allocation_id='312924',state='FAILED',elapsed_seconds=19,supplier='preserved R1 failure'))
    actual.insert(8,dict(event='submitted',task='cube-3506-6101',allocation_id='312928',state='FAILED',elapsed_seconds=19,supplier='preserved R2 failure'))
    gpu=receipt['gpu_allocation_seconds']+FAILED_SECONDS
    if gpu>c['gpu_seconds'] or receipt['cpu_stage_allocation_seconds']>c['cpu_seconds']:
        raise RuntimeError('cumulative charge cap including failure')
    receipt.update(gpu_allocation_seconds=gpu,failed_gpu_allocation_seconds=38,failed_allocations=['312924','312928'],
                   successful_gpu_allocation_seconds=gpu-38,lineage='R3',actual_attempts=len(actual),
                   actual_allocations=actual,dated_stop_resolution_sha256=sha(location(run)/'STOP-RESOLUTION.json'),
                   all_historical_stops_preserved=True,successful_tasks_recomputed=False,replacement_attempts=2)
    return receipt

def accept_grid(c,run):
    receipt=accounting(run,c);records=[]
    allocations={x['task']:x['allocation_id'] for x in receipt['allocations']}
    for j in c['jobs']:
        root=output_root(run,j)
        if root!=Path(run):verify_evidence(root/j['id'])
        for e in accept_worker(c,j,root,allocations[j['id']]):
            records.append({k:e[k] for k in ('task','source','parent','scorer_seed','config','success','planning_seconds','episode_operational_seconds','episode_elapsed_including_audit_seconds','process_cpu_seconds','resources','initial_success')} |
                           dict(decisions=len(e['plans']),actions=len(e['actions']),solve_seconds=sum(p['solve_seconds'] for p in e['plans']),
                                first_decision_seconds=next((t['observation_to_action_seconds'] for t in e['timings'] if t['planning_decision']),0.),
                                decision_observation_to_action_seconds=sum(t['observation_to_action_seconds'] for t in e['timings'] if t['planning_decision']),
                                later_decision_seconds=sum(t['observation_to_action_seconds'] for t in e['timings'] if t['planning_decision'] and t['step']>0),
                                reset_seconds=e['reset_seconds'],environment_construction_seconds=e.get('environment_construction_seconds',0.),audit_seconds=e['audit_seconds']))
    if len(records)!=len(c['jobs'])*8:raise RuntimeError('incomplete episode grid')
    return records,dict(**receipt,episodes=len(records),all_endpoint_traces_verified=True,science_selection=False)
