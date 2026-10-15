"""Allocated complete-study independent acceptance and fixed paired analysis.

Scientific outputs stay in the sealed result bundle. Stdout/control receipts
contain only completeness/resource identities, never partial efficacy.
"""
import json,sys
from pathlib import Path
import numpy as np
from .common import SETTINGS,identity,write_new
from wm_diag0_native_v3.store import authenticate,load_array,seal
from wm_diag0.analysis import estimate

def pack(rows):
    if not rows:raise ValueError('complete nonempty group')
    y=np.full((len(rows),16,2),-1,dtype=np.int8)
    for i,r in enumerate(rows):y[i,:r['candidate_count']]=r['outcomes']
    return estimate([r['root_id'] for r in rows],y,np.asarray([r['choices'] for r in rows],dtype=np.int64),
        np.zeros(len(rows),dtype=np.int64),np.asarray([r['initial_success'] for r in rows]),
        candidate_counts=np.asarray([r['candidate_count'] for r in rows],dtype=np.int64))

def native_distances(task,coordinates,goal):
    p=np.asarray(coordinates,dtype=np.float64);g=np.asarray(goal,dtype=np.float64)
    if task=='reacher':return {'raw_qpos_max_threshold_margin':float(np.max(np.abs(p-g)/.05))}
    d=abs(float(p[4]-g[4]))%(2*np.pi)
    pos=float(np.linalg.norm(p[:4]-g[:4])/20);angle=min(d,2*np.pi-d)/(np.pi/9)
    return {'joint_position_threshold_margin':pos,'wrapped_angle_threshold_margin':angle,'native_endpoint_margin':max(pos,angle)}

def main():
    contract=Path(sys.argv[1]);expected=sys.argv[2];taskdir=Path(sys.argv[3]);c=json.loads(contract.read_text())
    if identity(contract)['sha256']!=expected or not c['gpu_stages_authorized']:raise ValueError('exact authorized campaign')
    root=Path(c['run']);sources=json.loads((Path(c['source_run'])/'controls/ALL-SOURCES-ACCEPTED.json').read_text())
    if identity(Path(c['source_run'])/'controls/ALL-SOURCES-ACCEPTED.json')!=c['source_acceptance']:raise ValueError('complete source acceptance identity')
    accounting=json.loads((taskdir/'controls/ALL-ALLOCATIONS-TERMINAL.json').read_text())
    if accounting['status']!='ALL132_GPU_ALLOCATIONS_SUCCESSFUL_TERMINAL' or accounting['GPU_charged_seconds']>468000:raise ValueError('complete failure-inclusive allocation accounting')
    from .accept_readout import accept as accept_head
    from .accept import accept as accept_parent
    heads={};head_results=[]
    for setting in range(4):
        t=root/'tasks'/('readout-'+str(setting));ctl=json.loads((t/'controls/ACCEPTED.json').read_text())
        heads[setting]=(t/'output',ctl['output_seal']);head_results.append(accept_head(*heads[setting],c,setting))
    accepted=[];private=[];usage=[]
    for setting,(task,backbone) in enumerate(SETTINGS):
        for i in range(32):
            phase='technical' if i==0 else 'grid';index=setting if i==0 else setting*31+i-1
            t=root/'tasks'/(phase+'-'+str(index));ctl=json.loads((t/'controls/ACCEPTED.json').read_text())
            result=json.loads((t/'controls/RESULT.json').read_text());success=json.loads((t/'controls/WORKER-SUCCESS.json').read_text())
            if result['status']!='ACCEPTED' or ctl['output_seal']!=success['output_seal'] or result['acceptance_sha256']!=identity(t/'controls/ACCEPTED.json')['sha256']:raise ValueError('independent task acceptance chain')
            key=task+'-'+str(i).zfill(3)
            proof=accept_parent(t/'output',ctl['output_seal'],t/'controls/SELECTION-EXTERNAL.json',
                Path(c['source_runs'][task])/'tasks'/key/'output',sources['source_seals'][key],*heads[setting],c,gpu=False)
            if proof['task']!=task or proof['backbone']!=backbone or proof['technical']!=(i==0):raise ValueError('exact fixed task/backbone/root grid')
            proof.update(setting=setting,root_index=i);accepted.append(proof)
            usage.append(json.loads((t/'output/USAGE.json').read_text()))
            private.append((proof,t/'output'))
    if len(accepted)!=128 or len({(r['setting'],r['root_index']) for r in accepted})!=128:raise ValueError('complete fixed grid')
    # Every parent/source/selection/bank/readout/endpoint is now independently
    # accepted. Only this allocated analysis process creates full aggregates.
    result={'study':'WM-DIAG0-A2','status':'COMPLETE_RESULTS_PENDING_SSD_PRESERVATION','settings':{},'pooled_by_backbone':{},
        'head_quality':{},'independent_parent_count_per_backbone':64,'paired_bootstrap_seed':20261004,
        'limitations':['third-party DINO predictor bundles; training-time encoder checkout unverified',
        'accepted pinned DINOv2 encoder is prospective implementation definition, not historical equivalence',
        'readout coordinate supervision is additional training data; no tuning or historical-origin reconstruction',
        'raw Reacher qpos may be visually winding-ambiguous; no hidden winding correction',
        'descriptive paired bootstrap, not confirmatory/multiplicity-controlled or architectural causal attribution',
        'native success under fixed50-action tail budget is not global solvability; all-bank failure is not unreachability',
        'hindsight maximum is optimistic tested-bank opportunity; deterministic draws add no independent parents',
        'one failed source persistence attempt retained and charged; same-seed four-array identity required on retry'],
        'termination_reasons':{},'local_task_distances':{},'feature_prediction_diagnostics':{},
        'resource_accounting':accounting,'source_lineage':sources['exact_source_job_ids'],'source_contract':sources['source_contract']}
    for setting,(task,backbone) in enumerate(SETTINGS):
        key=task+'|'+backbone;rows=[r for r in accepted if r['setting']==setting]
        result['settings'][key]=pack(rows)
        result['head_quality'][key]=json.loads((heads[setting][0]/'READOUT.json').read_text())['quality']
        result['termination_reasons'][key]={r['root_id']:r['reasons'] for r in rows}
    for backbone in ('lewm','dinowm_noprop'):
        rows=[r for r in accepted if r['backbone']==backbone]
        result['pooled_by_backbone'][backbone]=pack(rows)
    physical={'world_resets':121,'controller_actions':5324,'Reacher_dm_steps':5368,'PushT_controller_actions':2640,'PushT_world_resets':60,'native_CEM_decisions':128}
    for proof,out in private:
        key=proof['root_id']+'|'+proof['backbone'];task=proof['task'];n=proof['candidate_count']
        source_dir=Path(c['source_runs'][task])/'tasks'/(task+'-'+str(proof['root_index']).zfill(3))/'output'
        coords=load_array(source_dir/'evidence/coordinates.npy');goal=coords[44]
        source_margin=native_distances(task,coords[20],goal);local=[]
        worlds=1+3*n+(2 if proof['technical'] else 0)
        physical['world_resets']+=worlds;physical['controller_actions']+=20*worlds
        if task=='pusht':physical['PushT_world_resets']+=worlds;physical['PushT_controller_actions']+=20*worlds
        else:physical['Reacher_dm_steps']+=40*worlds
        for i in range(n):
            oracle=json.loads((out/'oracle'/str(i)/'PREFIX.json').read_text())
            physical['controller_actions']+=oracle['actions']
            if task=='pusht':physical['PushT_controller_actions']+=oracle['actions']
            else:physical['Reacher_dm_steps']+=oracle['events'][-1]['native_clocks']['step_count']-oracle['events'][0]['native_clocks']['step_count']
            ends=[]
            for draw in (0,1):
                b=json.loads((out/'evaluation'/(str(i)+'-'+str(draw))/'BRANCH.json').read_text())
                physical['controller_actions']+=b['elapsed'];physical['native_CEM_decisions']+=b['tail_replans']
                if task=='pusht':physical['PushT_controller_actions']+=b['elapsed']
                else:physical['Reacher_dm_steps']+=b['events'][-1]['native_clocks']['step_count']-b['events'][0]['native_clocks']['step_count']
                ends.append(native_distances(task,b['events'][-1]['coordinates'],goal))
            local.append(ends)
        result['local_task_distances'][key]={'source':source_margin,'candidate_final_two_draws':local,
            'definition':'native endpoint threshold-normalized distances; descriptive only, not success replacement'}
        pred=load_array(out/'predicted.npy').astype(np.float64);real=load_array(out/'realized.npy').astype(np.float64)
        costs=load_array(out/'costs.npy')
        result['feature_prediction_diagnostics'][key]={'MSE_by_retained_sampling_position':np.mean((pred-real)**2,axis=(0,*range(2,pred.ndim))).tolist(),
            'within_bank_S0_pairwise_rank_agreement':float(np.mean(np.sign(costs[0,:,None]-costs[0,None,:])==np.sign(costs[2,:,None]-costs[2,None,:]))),
            'within_backbone_only_no_cross_latent_unit_comparison':True}
    physical['PushT_integrator_steps']=10*physical['PushT_controller_actions']+2*physical['PushT_world_resets']
    physical['Reacher_MuJoCo_integrator_steps']=physical['Reacher_dm_steps']*c['compiled_physics']['n_sub_steps']
    if physical['world_resets']>6401 or physical['controller_actions']>386924 or physical['Reacher_dm_steps']>386968 or physical['PushT_integrator_steps']>1940800 or physical['native_CEM_decisions']>4224:raise ValueError('all-attempt physical-work cap')
    models={backbone:sum(u['predictor_calls'] for r,u in zip(accepted,usage) if r['backbone']==backbone) for backbone in ('lewm','dinowm_noprop')}
    api=sum(u['cost_api_calls'] for u in usage);frames=1408+sum(u['encoded_frames'] for u in usage)
    if models['lewm']>317140 or models['dinowm_noprop']>950740 or api>126856 or frames>265360:raise ValueError('native model-call/frame cap')
    result['physical_work_including_failed_source']=physical
    result['native_model_usage']={'predictor_batch_or_chunk_calls':models,'cost_and_reforecast_api_calls':api,'encoded_frames':frames,'readout_frames':1408}
    out=taskdir/'output';out.mkdir(exist_ok=False)
    # These are full fixed results, still private until whole/member SSD gate.
    write_new(out/'RESULTS.json',result)
    write_new(out/'ACCEPTANCE.json',{'status':'ALL120_SOURCES_4_READOUTS_128_PARENTS_INDEPENDENTLY_ACCEPTED',
        'parent_output_seals':{r['root_id']+'|'+r['backbone']:r['output_seal'] for r in accepted},
        'readout_output_seals':{str(k):v[1] for k,v in heads.items()},'contract_sha256':expected,
        'source_acceptance':c['source_acceptance'],'GPU_charged_seconds':accounting['GPU_charged_seconds'],
        'publication_requires_final_SSD_whole_and_every_member_verification':True})
    s=seal(out,39_000_000)
    write_new(taskdir/'controls/ACCEPTED.json',{'accepted':True,'phase':'analysis','index':0,'output_seal':s,'source_roots':120,'readouts':4,'diagnostic_parents':128,'scientific_values_emitted_to_controls':False})
    print(json.dumps({'status':'COMPLETE_STUDY_INDEPENDENTLY_ACCEPTED_PENDING_SSD','output_seal':s,'source_roots':120,'readouts':4,'parents':128}))

if __name__=='__main__':main()
