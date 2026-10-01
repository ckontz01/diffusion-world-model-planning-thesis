"""Independent supplier/attempt accounting and strict round-trip certificates."""
from dtv_success_cost.common import *
from dtv_success_cost.accept import accept_worker as original_accept_worker
from dtv_success_cost_r1.accept import accounting_events
from dtv_success_cost_r1.common import ROW
from dtv_success_cost_r4.common import *
from dtv_success_cost_r4.initialization import verify_pusht_initialization
from dtv_success_cost_r2.render import verify_evidence

def accept_worker(c,job,run,allocation=None):
    episodes=original_accept_worker(c,job,run,allocation)
    if job['task']=='pusht' and Path(run).name=='workers' and Path(run).parent.name=='recovery-r4':
        import numpy as np
        with np.load(Path(run)/job['id']/'SOURCE-INPUT.npz',allow_pickle=False) as data:source=data['initial_state']
        for e in episodes:
            certificate=verify_pusht_initialization(e['initial']['current'],source,[0.,45.])
            if load(Path(run)/job['id']/(e['config']+'.initialization.json'))!=certificate:raise RuntimeError('independent initialization certificate differs')
    return episodes
def supplier_events(history,suppliers):
    ids={x['allocation_id'] for x in suppliers};tasks={x['task'] for x in suppliers}
    return [x for x in history if x.get('allocation_id') in ids or x.get('task') in tasks or x['event']=='technical_tranche_passed']
def combined_events(run,c):
    r=load(location(run)/'EXECUTION-APPROVAL.json');verify_resolution(run,r)
    r1,r2,r3=authenticate_history(run);old=events(Path(run)/'DISPATCH.jsonl')
    if [x['event'] for x in old]!=['submission_intent','submission_response','submitted','scheduler']:raise RuntimeError('original history changed')
    projected=old+[dict(event='scheduler',allocation_id='312920',returncode=0,stdout='|'.join(ROW)+'\n',supplier='R1 dated resolution'),
        dict(event='terminal',task='preflight',allocation_id='312920',state='COMPLETED',exit='0:0',elapsed_seconds=178,supplier='R1 dated resolution'),dict(event='accepted',task='preflight',supplier='R1 dated carry')]
    early=load(prior.LINEAGE)['carried']
    for history,suppliers in ((r1,early[:3]),(r2,early[3:]),(r3,load(LINEAGE)['carried'])):projected+=supplier_events(history,suppliers)
    current=events(location(run)/'DISPATCH-R4.jsonl')
    from dtv_success_cost_r4.campaign import carry_record
    carry=carry_record(run)
    if not current or any(current[0].get(k)!=v for k,v in carry.items()) or sum(x['event']=='carried_history_accepted' for x in current)!=1:raise RuntimeError('R4 carry acceptance differs')
    return projected+current[1:]
def accounting(run,c,include_analysis=False):
    receipt=accounting_events(combined_events(run,c),c,include_analysis);actual=[dict(x) for x in receipt['allocations']]
    if set(FAILED_IDS)&{x['allocation_id'] for x in actual}:raise RuntimeError('failed supplier repeated')
    for index,task,allocation,elapsed,supplier in ((4,'reacher-4374-6101','312924',19,'R1'),(8,'cube-3506-6101','312928',19,'R2'),(30,'pusht-3819-6101','312950',21,'R3')):
        actual.insert(index,dict(event='submitted',task=task,allocation_id=allocation,state='FAILED',elapsed_seconds=elapsed,supplier='preserved '+supplier+' failure'))
    gpu=receipt['gpu_allocation_seconds']+59
    if gpu>c['gpu_seconds'] or receipt['cpu_stage_allocation_seconds']>c['cpu_seconds']:raise RuntimeError('cumulative cap including failed attempts')
    receipt.update(gpu_allocation_seconds=gpu,failed_gpu_allocation_seconds=59,failed_allocations=FAILED_IDS,successful_gpu_allocation_seconds=gpu-59,
        lineage='R4',actual_attempts=len(actual),actual_allocations=actual,dated_stop_resolution_sha256=sha(location(run)/'STOP-RESOLUTION.json'),
        all_historical_stops_preserved=True,successful_tasks_recomputed=False,replacement_attempts=3)
    return receipt
def accept_grid(c,run):
    receipt=accounting(run,c);records=[];allocations={x['task']:x['allocation_id'] for x in receipt['allocations']}
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
