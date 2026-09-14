"""Four-reference engineering pilot; no historical writes or new training.

All models and physics come from the completed study's pinned runtime. The
historical selected plans and delivered prefix must reproduce before any
intervention. Raw first banks are newly regenerated, not historical evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np

PILOT=(1269,582,525,722,567,716,630,1066,1074,1565,70,867,221,905,1287,621,428,288,1488,757,641,855,1280,420,860,98,886,432,181,783,706,989)
HORIZONS=(75,150)
ANCHORS=(0,30)
ATOL=1e-10
CONDITIONS=('baseline','state','latent','joint')

def require(ok,message):
    if not ok: raise RuntimeError(message)

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def array_hash(x):
    x=np.ascontiguousarray(x)
    return hashlib.sha256(str((x.shape,str(x.dtype))).encode()+x.tobytes()).hexdigest()

def delta_at(horizon,elapsed):
    require(horizon in HORIZONS and elapsed in ANCHORS,'Unapproved pilot coordinate')
    return horizon-elapsed%horizon

def decode(planner,decoder):
    shape=planner.shape
    require(shape[-1]==2,'Action dimension')
    decoded=decoder.inverse_transform(np.asarray(planner,np.float32).reshape(-1,2)).reshape(shape)
    require(np.isfinite(decoded).all(),'Nonfinite decoded actions')
    return decoded

def score(cost):
    require(cost.shape==(64,8) and np.isfinite(cost).all(),'Cost shape/finite')
    return np.partition(cost,1,axis=1)[:,:2].mean(axis=1)

def run(study,out,reference,repeat):
    require(reference in PILOT and repeat in (0,1),'Not an authorized pilot repeat')
    expected=Path('/lustreFS/data/superworld/ckontzias/thesis/experiments/independent-pusht/final-20260906-4a608e5')
    require(study.resolve()==expected,'Unexpected historical study')
    allowed=expected.parents[1]/'diffusion-bottleneck'
    require(allowed in out.resolve().parents,'Output outside diagnostic root')
    require(not out.exists(),'Refuse existing output')
    import torch
    import stable_worldmodel as swm
    from pusht_fresh_initialization import register,reset_world
    from independent_pusht_runtime import build,tensor_hash
    from independent_pusht_evaluate import initial_hash
    from independent_pusht_collect import body_fields
    from e18_fresh_driver import computational_info
    from gdp_cem_e15_models import action_active_mask
    from diffusion_bottleneck import LOCK_SHA,require_sha,checked_child

    require_sha(study/'INPUT-LOCK.json',LOCK_SHA)
    lock=json.loads((study/'INPUT-LOCK.json').read_text())
    require_sha(study/'collection/COLLECTION.json',lock['collection_sha256'])
    manifest=json.loads((study/'collection/COLLECTION.json').read_text())
    namespace='diffusion-bottleneck-v1|development-selection|2026-09-13'
    ordered=sorted(range(1600),key=lambda i:(hashlib.sha256(f'{namespace}|{i}'.encode()).hexdigest(),i))
    require(tuple(ordered[:32])==PILOT,'Identifier-only selection differs')
    ref=manifest['records'][reference]
    require(ref['index']==reference,'Reference identity')
    file=checked_child(study/'collection',ref['file']);require_sha(file,ref['sha256'])
    with np.load(file,allow_pickle=False) as data:
        initial=data['initial_request'].copy()
        goals={h:data['states'][h].copy() for h in HORIZONS}
    task=reference//64
    taskroot=study/f'stage-0/task-{task:04d}'
    done=json.loads((taskroot/'DONE.json').read_text())
    require(done['task']['arm']=='vad_continuation' and done['task']['seed']==7201,'Task identity')
    require_sha(taskroot/'results/RESULT.json',done['result_sha256'])
    archived=json.loads((taskroot/'results/RESULT.json').read_text())
    rows={r['horizon']:r for r in archived['rows'] if r['reference_index']==reference}
    require(set(rows)==set(HORIZONS),'Missing horizons')
    require(all(r['failure'] is None for r in rows.values()),'Historical planner exception')
    torch.set_num_threads(4)
    factory,modules,provenance=build('vad_continuation',7201)
    before=tensor_hash(modules)
    require(before==archived['model_state_sha256'],'Historical model-state hash mismatch')
    torch.cuda.reset_peak_memory_stats()
    out.mkdir(parents=True)
    arrays={}; reports=[];step_count=0;branch_count=0
    started=time.perf_counter()

    def cpu(x):return x.detach().cpu().numpy().copy()
    def save(prefix,**values):
        for name,x in values.items():arrays[prefix+'/'+name]=cpu(x) if torch.is_tensor(x) else np.asarray(x).copy()
    def new_world(record,seed):
        w=swm.World(register(),num_envs=1,image_shape=(224,224),max_episode_steps=300,
                    correct_velocity_space=True,verbose=0)
        bound_policy=factory(h,seed);w.set_policy(bound_policy)
        reset_world(w,[record],seed=seed)
        np.testing.assert_allclose(w.envs.envs[0].unwrapped._get_obs(),initial,rtol=0,atol=ATOL)
        require(initial_hash(w.infos)==row['initial_hash'],'Historical initial observation hash mismatch')
        return w,bound_policy
    def step(w,action):
        nonlocal step_count
        require(np.asarray(action).shape==(2,) and np.isfinite(action).all(),'Invalid physical command')
        w.states,_,w.terminateds,w.truncateds,w.infos=w.envs.step(np.asarray(action)[None])
        step_count+=1
        return bool(np.asarray(w.terminateds).any()),bool(np.asarray(w.truncateds).any())
    def snapshot(w):
        e=w.envs.envs[0].unwrapped
        return {'physical':e._get_obs().copy(),'controller':body_fields(e),
                'pixels':np.asarray(w.infos['pixels']).copy(),'goal':np.asarray(w.infos['goal']).copy()}

    for h in HORIZONS:
        row=rows[h]
        path=checked_child(taskroot/'results',row['trajectory_file']);require_sha(path,row['trajectory_sha256'])
        with np.load(path,allow_pickle=False) as data:
            historical_states=data['states'].copy();delivered=data['actions'].copy()
            np.testing.assert_array_equal(data['goal_state'],goals[h])
        record={'state':initial,'goal_state':goals[h],'proprio':initial[[0,1,5,6]]}
        seed=row['seed'];w,policy=new_world(record,seed)
        np.testing.assert_allclose(initial,historical_states[0],rtol=0,atol=ATOL)
        solver=policy.planner;original_solve=solver.solve
        archived_calls={c['at']:c for c in row['calls']}
        elapsed=0
        def verified_historical_solve(*args,**kw):
            result=original_solve(*args,**kw)
            require(array_hash(result['actions'].float().numpy())==archived_calls[elapsed]['plan_hash'],
                    'Historical prefix selected-plan hash mismatch')
            actual=solver.diagnostic_history[-1];expected=archived_calls[elapsed]['diagnostics']
            for key in ('delta','tau','proposal_generator_before_sha256','proposal_generator_after_sha256',
                        'gmm_generator_before_sha256','gmm_generator_after_sha256'):
                require(actual[key]==expected[key],'Historical planner lifecycle mismatch: '+key)
            return result
        solver.solve=verified_historical_solve
        try:
            for anchor in ANCHORS:
                if row['delivered']<=anchor:
                    reports.append({'horizon':h,'anchor':anchor,'available':False,'reason':'historical_episode_finished'})
                    continue
                while elapsed<anchor:
                    action=policy.get_action(computational_info(w.infos))[0]
                    np.testing.assert_array_equal(action,delivered[elapsed])
                    terminated,truncated=step(w,delivered[elapsed]);elapsed+=1
                    np.testing.assert_allclose(w.envs.envs[0].unwrapped._get_obs(),historical_states[elapsed],rtol=0,atol=ATOL)
                    require(not (terminated or truncated),'Unexpected prefix termination')
                require(not policy._action_buffer,'Nonempty anchor buffer')
                captures=[];rollouts=[];adapter=[];encodings=[]
                old_encode=solver._encode
                old_propose,old_rollout,old_adapter=solver._propose,solver._rollout,solver._predict_intermediate_state
                def capture_propose(**kw):
                    state_before=solver.proposal_generator.get_state().clone()
                    result=old_propose(**kw)
                    noisegen=torch.Generator(device=solver.device);noisegen.set_state(state_before)
                    mask=action_active_mask(kw['tau'],primitive_action_dim=2).reshape(len(kw['tau']),-1)
                    noise=torch.randn(len(kw['tau']),kw['count'],mask.shape[1],device=solver.device,generator=noisegen)*mask[:,None]
                    require(torch.equal(noisegen.get_state(),solver.proposal_generator.get_state()),'Noise consumption differs')
                    captures.append((kw,result,state_before,noise))
                    return result
                def capture_rollout(*args,**kw):
                    result=old_rollout(*args,**kw);rollouts.append(result.clone());return result
                def capture_adapter(**kw):
                    result=old_adapter(**kw);adapter.append(tuple(x.clone() for x in result));return result
                def capture_encode(*args,**kw):
                    result=old_encode(*args,**kw);encodings.append(tuple(x.clone() for x in result));return result
                solver._propose=capture_propose;solver._rollout=capture_rollout
                solver._predict_intermediate_state=capture_adapter;solver._encode=capture_encode
                at=snapshot(w)
                try:action=policy.get_action(computational_info(w.infos))[0]
                finally:
                    solver._propose=old_propose;solver._rollout=old_rollout
                    solver._predict_intermediate_state=old_adapter;solver._encode=old_encode
                np.testing.assert_array_equal(action,delivered[anchor])
                require(len(captures)==2 and len(rollouts)==2 and len(adapter)==1 and len(encodings)==1,'Unexpected continuation path')
                require(solver.diagnostic_history[-1]['delta']==delta_at(h,anchor),'Schedule mismatch')
                ck,first,_,first_noise=captures[0]
                sk,second,second_rng,second_noise=captures[1]
                first_raw,first_planner,_=first
                predicted_state,predicted_latent=adapter[0]
                first_terminal=rollouts[0];goal_raw=encodings[0][1].expand(64,-1)
                physical_first=decode(cpu(first_planner)[0,:,:15],policy.process['action'])
                post_baseline_rng=solver.proposal_generator.get_state().clone()
                prefix=f'h{h}/t{anchor}'
                save(prefix,first_raw=first_raw,first_planner=first_planner,first_noise=first_noise,
                     second_noise=second_noise,predicted_latent=first_terminal,predicted_state=predicted_state,
                     goal_raw=goal_raw,current_raw=encodings[0][0],physical_first=physical_first,
                     anchor_state=at['physical'],anchor_controller=at['controller'],
                     normalized_current=ck['current'],normalized_goal=ck['goal'],normalized_state=ck['state'])
                save(prefix,state_mean=solver.statistics.state_mean,state_std=solver.statistics.state_std,
                     latent_mean=solver.statistics.latent_mean,latent_std=solver.statistics.latent_std,
                     decoder_mean=policy.process['action'].mean_,decoder_scale=policy.process['action'].scale_,
                     goal_state=goals[h],prefix_actions=delivered[:anchor],second_rng=second_rng,
                     post_baseline_rng=post_baseline_rng)

                def physical_branch(first_actions,second_actions=None):
                    nonlocal branch_count
                    b,_=new_world(record,seed);branch_count+=1
                    states=[];terms=[]
                    try:
                        for t,a in enumerate(delivered[:anchor]):
                            term,trunc=step(b,a)
                            np.testing.assert_allclose(b.envs.envs[0].unwrapped._get_obs(),historical_states[t+1],rtol=0,atol=ATOL)
                            require(not (term or trunc),'Branch prefix terminated')
                        current=snapshot(b)
                        for k in at:
                            if k in ('pixels','goal'):np.testing.assert_array_equal(current[k],at[k])
                            else:np.testing.assert_allclose(current[k],at[k],rtol=0,atol=ATOL)
                        sequence=list(first_actions)+(list(second_actions) if second_actions is not None else [])
                        for a in sequence[:2*h-anchor]:
                            term,trunc=step(b,a)
                            states.append(b.envs.envs[0].unwrapped._get_obs().copy());terms.append([term,trunc])
                            if term or trunc:break
                        info=policy._prepare_info(computational_info(b.infos))
                        with torch.inference_mode():latent=solver._encode(info)[0][0].clone()
                        return np.stack(states),np.asarray(terms),latent
                    finally:b.close()

                actual_states=[];actual_latents=[];active=[];first_success=[]
                for i in range(64):
                    states,terms,latent=physical_branch(physical_first[i])
                    actual_states.append(states[-1]);actual_latents.append(latent)
                    active.append(len(states)==15 and not terms[-1].any())
                    first_success.append(bool(terms[:,0].any()))
                    save(prefix+f'/first-{i}',states=states,termination_flags=terms)
                actual_states=np.stack(actual_states)
                actual_latents=torch.stack(actual_latents)
                active_t=torch.as_tensor(active,device=solver.device)
                actual_state_norm=(torch.as_tensor(actual_states,device=solver.device,dtype=torch.float32)-solver.statistics.state_mean)/solver.statistics.state_std
                actual_latent_norm=(actual_latents-solver.statistics.latent_mean)/solver.statistics.latent_std
                save(prefix,actual_states=actual_states,actual_latents=actual_latents,active=active,first_success=first_success)
                outcomes={};choices={};baseline_cost=None
                try:
                    for condition in CONDITIONS:
                        solver.proposal_generator.set_state(second_rng)
                        inputs={k:v for k,v in sk.items()}
                        if condition in ('state','joint'):
                            inputs['state']=torch.where(active_t[:,None],actual_state_norm,predicted_state)
                        if condition in ('latent','joint'):
                            inputs['current']=torch.where(active_t[:,None],actual_latent_norm,predicted_latent)
                        with torch.inference_mode():
                            raw,planner,_=old_propose(**inputs)
                            terminal=old_rollout(first_terminal.reshape(64,-1),planner,tau=15)
                            cost=(terminal-goal_raw[:,None]).square().sum(-1)
                        if condition=='baseline':
                            require(torch.equal(planner,second[1]) and torch.equal(raw,second[0]),'Regenerated baseline second bank mismatch')
                            require(torch.equal(terminal,rollouts[1]),'Regenerated baseline rollout mismatch')
                            baseline_cost=cpu(cost)
                        require(torch.equal(solver.proposal_generator.get_state(),post_baseline_rng),'Condition RNG stream mismatch')
                        costs=cpu(cost);scores=score(costs);chosen=int(scores.argmin())
                        second_chosen=int(costs[chosen].argmin())
                        physical_second=decode(cpu(planner)[chosen,second_chosen,:15],policy.process['action'])
                        states,terms,_=physical_branch(physical_first[chosen],physical_second)
                        choices[condition]=[chosen,second_chosen]
                        outcomes[condition]={'short_branch_success':bool(terms[:,0].any()),'delivered':len(states),
                            'first_chunk_success':bool(terms[:15,0].any()),
                            'first_branch_active_for_intervention':bool(active[chosen])}
                        save(prefix+'/'+condition,second_raw=raw,second_planner=planner,costs=costs,scores=scores,
                             scoring_terminal=terminal,supplied_state=inputs['state'],supplied_latent=inputs['current'],
                             states=states,termination_flags=terms,
                             delivered_actions=np.concatenate((physical_first[chosen],physical_second))[:len(states)])
                    immediate=cpu((first_terminal-goal_raw[:1,None]).square().sum(-1))[0]
                    greedy=int(immediate.argmin())
                    states,terms,_=physical_branch(physical_first[greedy])
                    save(prefix+'/greedy64',costs=immediate,states=states,termination_flags=terms)
                    require(choices['baseline'][0]==int(score(baseline_cost).argmin()),'Selector inconsistency')
                    archived_macro=first_planner[0,choices['baseline'][0],:15].reshape(1,3,10).cpu()
                    require(array_hash(archived_macro.numpy())==archived_calls[anchor]['plan_hash'],'Same-bank baseline plan mismatch')
                finally:solver.proposal_generator.set_state(post_baseline_rng)
                reports.append({'horizon':h,'anchor':anchor,'available':True,'historical_plan_hash_checked':True,
                    'regenerated_bank_not_historical_raw_bank':True,'active_first_branches':sum(active),
                    'first_chunk_successes':sum(first_success),'selected':choices,'greedy64':greedy,
                    'short_outcomes':outcomes,'tail_policy_executed':False})
                # Deliver exactly the already-verified historical first action;
                # buffered actions and generator lifecycle continue unchanged.
                term,trunc=step(w,delivered[anchor]);elapsed=anchor+1
                np.testing.assert_allclose(w.envs.envs[0].unwrapped._get_obs(),historical_states[elapsed],rtol=0,atol=ATOL)
        finally:w.close()
    require(tensor_hash(modules)==before,'Model mutation')
    np.savez_compressed(out/'BANKS.npz',**arrays)
    report={'reference':reference,'repeat':repeat,'all_technical_checks_passed':True,'anchors':reports,
            'physical_branch_rollouts':branch_count,'primitive_steps_including_replays':step_count,
            'wall_seconds':time.perf_counter()-started,'model_state_sha256':before,'provenance':provenance,
            'gpu_peak_allocated_bytes':torch.cuda.max_memory_allocated(),
            'gpu_peak_reserved_bytes':torch.cuda.max_memory_reserved(),
            'banks_sha256':digest(out/'BANKS.npz'),'program_sha256':digest(__file__),
            'protected_payload_reads':0,'unevaluated_reference_payload_reads':0,'training_runs':0,
            'historical_decision_changed':False,'long_budget_tail_test':'unrun'}
    with (out/'REPORT.json').open('x') as f:json.dump(report,f,indent=2,sort_keys=True,allow_nan=False)
    with (out/'sha256.txt').open('x') as f:
        for name in ('BANKS.npz','REPORT.json'):f.write(digest(out/name)+'  '+name+'\n')
    print(json.dumps({'technical_pass':True,'reference':reference,'repeat':repeat}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--study',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--reference',type=int,required=True);p.add_argument('--repeat',type=int,required=True)
    a=p.parse_args();run(a.study,a.out,a.reference,a.repeat)
