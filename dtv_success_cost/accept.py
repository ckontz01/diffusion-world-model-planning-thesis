"""Independent exact-grid technical acceptance; no efficacy condition."""
from dtv_success_cost.common import *
from dtv_success_cost.episode import verify_episode

def verify_input_endpoints(directory,task,episodes):
    import numpy as np
    current_key,target_key={'pusht':('initial_state','target_state'),'reacher':('initial_qpos','target_qpos'),
                           'cube':('initial_privileged_block_0_pos','target_privileged_block_0_pos')}[task]
    with np.load(Path(directory)/'SOURCE-INPUT.npz',allow_pickle=False) as data:
        current=np.asarray(data[current_key]);target=np.asarray(data[target_key]);pixels=data['goal_pixels']
        if pixels.dtype!=np.uint8 or pixels.ndim!=3 or pixels.shape[-1]!=3 or pixels.nbytes>200000:raise RuntimeError('declared RGB target-frame interface/footprint changed')
    for e in episodes:
        initial=e['initial']
        if current.shape!=np.asarray(initial['current']).shape or target.shape!=np.asarray(initial['target']).shape or not np.allclose(current,initial['current'],rtol=0,atol=1e-12) or not np.allclose(target,initial['target'],rtol=0,atol=1e-12):raise RuntimeError('native reset/goal differs from authenticated saved input')

def accept_worker(c,job,run,allocation=None):
    d=Path(run)/job['id'];s=read_seal(d,job['id']);meta=load(d/'WORKER.json')
    if meta['bindings_sha256']!=sha(DOC/'BINDINGS.json') or meta['identity']!=job['id']:raise RuntimeError('worker identity')
    if allocation is not None and meta['allocation_id']!=str(allocation):raise RuntimeError('allocation differs')
    if meta['hostname'] not in ('gpu09','gpu09.cluster') or meta['gpu']!='NVIDIA RTX 6000 Ada Generation':raise RuntimeError('wrong hardware')
    spec=c['models'][f'{job["task"]}-{job["scorer_seed"]}']
    if meta['checkpoints']!={a:m['checkpoint_sha256'] for a,m in spec['models'].items()} or meta['world_checkpoint']!=spec['world_sha256']:raise RuntimeError('checkpoint freeze changed')
    if sha(d/'SOURCE-INPUT.npz')!=meta['source_input_sha256']:raise RuntimeError('allowlisted source input evidence changed')
    if any(r['path']=='FAILURE.json' for r in s['files']):raise RuntimeError('failed work cannot be accepted')
    out=[]
    for config in CONFIGS:
        e=load(d/(config+'.json'));verify_episode(e)
        journal=[__import__('json').loads(x) for x in (d/(config+'.trace.jsonl')).read_text().splitlines()]
        if [r['event'] for r in journal]!=['initial']+[v for _ in e['actions'] for v in ('action_intent','transition')]:raise RuntimeError('raw journal sequence changed')
        if journal[0]!=dict(event='initial',endpoint=e['initial'],initial_success=e['initial_success']):raise RuntimeError('initial journal evidence changed')
        transitions=[r for r in journal if r['event']=='transition'];intents=[r for r in journal if r['event']=='action_intent']
        if len(transitions)!=len(e['actions']) or len(intents)!=len(e['actions']):raise RuntimeError('partial/journal trajectory incomplete')
        if any(r['row']!=row or r['timing']!=timing for r,row,timing in zip(transitions,e['actions'],e['timings'])):raise RuntimeError('raw timing/action readback differs')
        if any(r['action']!=row['action'] or r['step']!=row['step'] for r,row in zip(intents,e['actions'])):raise RuntimeError('delivered action intent differs')
        plans={p['step']:{k:v for k,v in p.items() if k!='step'} for p in e['plans']}
        if any(r['plan']!=plans.get(r['step']) for r in intents):raise RuntimeError('raw plan intent differs')
        if (e['task'],e['source'],e['parent'],e['scorer_seed'],e['planner_seed'],e['config'])!=(job['task'],job['source_index'],c['cohort'][job['task']][job['source_index']]['parent_id'],job['scorer_seed'],job['planner_seed'],config):raise RuntimeError('episode grid identity changed')
        if out and e['initial']!=out[0]['initial']:raise RuntimeError('initial pairing lost')
        out.append(e)
    verify_input_endpoints(d,job['task'],out)
    if sum(p.stat().st_size for p in d.rglob('*') if p.is_file())>job['output_bytes']:raise RuntimeError('worker complete footprint')
    return out

def accounting(run,c,include_analysis=False):
    events=[__import__('json').loads(line) for line in (Path(run)/'DISPATCH.jsonl').read_text().splitlines()]
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
    if (Path(run)/'STOP.json').exists():raise RuntimeError('control STOP requires separately frozen resolution; never silently ignored')
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

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--approval',type=Path,default=DOC/'EXECUTION-APPROVAL.json');p.add_argument('--run',type=Path,required=True);a=p.parse_args();c=gate(a.approval)
    _,r=accept_grid(c,a.run);print(__import__('json').dumps(r))
if __name__=='__main__':main()
