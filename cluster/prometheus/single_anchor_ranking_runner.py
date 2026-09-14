"""Opt-in future real-runtime runner. No execution is authorized by preparation.

Historical solver/policy, initialization and physics remain imported unchanged.
Only the selected macro returned at one absolute anchor may be replaced.
"""
import argparse
import hashlib
import json
import time
from copy import deepcopy
from pathlib import Path
import numpy as np
import single_anchor_ranking as spec
from diffusion_bottleneck_branch import array_hash
from diffusion_bottleneck import require, sha256, require_sha

LIFECYCLE = ('delta','tau','proposal_generator_before_sha256',
             'proposal_generator_after_sha256','gmm_generator_before_sha256',
             'gmm_generator_after_sha256')


def exact(a,b):
    a,b = np.asarray(a),np.asarray(b)
    require(a.dtype == b.dtype and a.shape == b.shape and a.tobytes() == b.tobytes(), 'Exact array identity')


def capture_selection(solver, original, args, kwargs, arm):
    """Run original solve once; score with original torch arithmetic, no draws.

    Temporarily observe existing calls only. All methods restored even on error.
    The original output is checked against the continuation argmin before changing
    the immediate arm. Both arms execute this same instrumentation.
    """
    import torch
    from gdp_cem_e18_closed_loop import continuation_score
    require(arm in spec.ARMS, 'Unknown arm')
    events = {k:[] for k in ('_propose','_rollout','_encode','_predict_intermediate_state')}
    old = {k:getattr(solver,k) for k in events}
    def hook(name):
        def wrapped(*a,**kw):
            output = old[name](*a,**kw)
            events[name].append((kw,output))
            return output
        return wrapped
    for name in events: setattr(solver,name,hook(name))
    try: result = original(*args,**kwargs)
    finally:
        for name,value in old.items(): setattr(solver,name,value)
    require([len(events[k]) for k in events] == [2,2,1,1], 'Intervention workload changed')
    cpu = lambda t:t.detach().cpu().numpy().copy()
    first_kw, first = events['_propose'][0]
    second_kw, second = events['_propose'][1]
    terminal = events['_rollout'][0][1]
    second_terminal = events['_rollout'][1][1]
    current, goal = events['_encode'][0][1]
    proposal_after = solver.proposal_generator.get_state().clone()
    gmm_after = solver.gmm_generator.get_state().clone()
    global_after = torch.get_rng_state().clone()
    cuda_after = torch.cuda.get_rng_state_all() if solver.device.type == 'cuda' else []
    with torch.inference_mode():
        immediate = (terminal-goal[:,None]).square().sum(dim=-1)
        costs = (second_terminal-goal.expand(64,-1)[:,None]).square().sum(dim=-1)
        continuation = continuation_score(costs.reshape(1,64,8))
        ci,ii = int(continuation.argmin(dim=1).item()),int(immediate.argmin(dim=1).item())
        expected = first[1][:,:,:15].reshape(1,64,3,10)[0,ci].reshape(1,3,10).cpu()
        require(torch.equal(result['actions'],expected), 'Original production selection differs')
        chosen = ii if arm == 'immediate' else ci
        replacement = first[1][:,:,:15].reshape(1,64,3,10)[0,chosen].reshape(1,3,10).cpu()
    cuda_current = torch.cuda.get_rng_state_all() if cuda_after else []
    require(torch.equal(proposal_after,solver.proposal_generator.get_state()) and
            torch.equal(gmm_after,solver.gmm_generator.get_state()) and
            torch.equal(global_after,torch.get_rng_state()) and len(cuda_current)==len(cuda_after) and
            all(torch.equal(a,b) for a,b in zip(cuda_after,cuda_current)), 'Ranking consumed RNG')
    payload = dict(first_raw=cpu(first[0]),first_planner=cpu(first[1]),
        second_raw=cpu(second[0]),second_planner=cpu(second[1]),
        predicted_latent=cpu(terminal),scoring_terminal=cpu(second_terminal),
        current_raw=cpu(current),goal_raw=cpu(goal.expand(64,-1)),
        normalized_current=cpu(first_kw['current']),normalized_goal=cpu(first_kw['goal']),
        normalized_state=cpu(first_kw['state']),supplied_state=cpu(second_kw['state']),
        supplied_latent=cpu(second_kw['current']),costs=cpu(costs),
        immediate=cpu(immediate)[0],continuation=cpu(continuation)[0],
        proposal_after=cpu(proposal_after),gmm_after=cpu(gmm_after),global_after=cpu(global_after),
        chosen=np.array(chosen,np.int64),continuation_index=np.array(ci,np.int64),
        immediate_index=np.array(ii,np.int64))
    payload['cuda_global_after'] = np.stack([cpu(v) for v in cuda_after]) if cuda_after else np.empty((0,),np.uint8)
    return {**result,'actions':replacement},payload


def match_saved(payload, saved, h, anchor):
    prefix = f'h{h}/t{anchor}/'
    mapping = {'first_raw':'first_raw','first_planner':'first_planner',
        'second_raw':'baseline/second_raw','second_planner':'baseline/second_planner',
        'predicted_latent':'predicted_latent','scoring_terminal':'baseline/scoring_terminal',
        'current_raw':'current_raw','goal_raw':'goal_raw','normalized_current':'normalized_current',
        'normalized_goal':'normalized_goal','normalized_state':'normalized_state',
        'supplied_state':'baseline/supplied_state','supplied_latent':'baseline/supplied_latent',
        'costs':'baseline/costs','immediate':'greedy64/costs','continuation':'baseline/scores',
        'proposal_after':'post_baseline_rng'}
    for name,key in mapping.items(): exact(payload[name],saved[prefix+key])


def run(reference, repeat, out, combined, source_sha, protocol_sha):
    # run() is called by the approval-gated CLI, never during preparation/tests.
    spec.coordinate(reference,75,0,'continuation',repeat)
    root = spec.STUDY.parents[1]/'single-anchor-ranking-20260914'
    require(root in out.resolve().parents and not out.exists(), 'New experiment output only')
    initial,goals,histories,saved,provenance = spec.load_inputs(reference,combined)
    import torch
    import stable_worldmodel as swm
    from independent_pusht_runtime import build,tensor_hash
    from independent_pusht_evaluate import initial_hash
    from independent_pusht_collect import body_fields
    from pusht_fresh_initialization import register,reset_world
    from e18_fresh_driver import computational_info
    began = time.perf_counter()
    torch.set_num_threads(4)
    factory,modules,model_provenance = build('vad_continuation',7201)
    construction_seconds = time.perf_counter()-began
    require(tensor_hash(modules) == spec.MODEL_SHA, 'Historical model identity')
    torch.cuda.reset_peak_memory_stats()
    out.mkdir(parents=True,exist_ok=False)
    arrays, rows = {},[]
    primitive_steps = 0
    for h in spec.HORIZONS:
        row,history = histories[h]
        archived_calls = {c['at']:c for c in row['calls']}
        record = {'state':initial,'goal_state':goals[h],'proprio':initial[[0,1,5,6]]}
        for anchor in spec.ANCHORS:
            owned = []
            branch_data = {}
            for arm in spec.ARMS:
                # Each arm AND anchor freshly replays from historical t0. Never
                # initialize t30 from a treatment branch or visible-state setter.
                world = swm.World(register(),num_envs=1,image_shape=(224,224),max_episode_steps=300,
                                  correct_velocity_space=True,verbose=0)
                policy = factory(h,row['seed']);solver = policy.planner
                require(all(policy is not p and solver is not p.planner and
                    solver.proposal_generator is not p.planner.proposal_generator and
                    solver.gmm_generator is not p.planner.gmm_generator for p in owned), 'Shared branch ownership')
                owned.append(policy)
                world.set_policy(policy)
                reset_world(world,[record],seed=row['seed'])
                np.testing.assert_allclose(world.envs.envs[0].unwrapped._get_obs(),initial,rtol=0,atol=spec.ATOL)
                require(initial_hash(world.infos) == row['initial_hash'], 'Initial observation identity')
                world.terminateds=np.zeros(1,dtype=bool);world.truncateds=np.zeros(1,dtype=bool)
                world.rewards=None
                goal_pixels=np.asarray(world.infos['goal']).copy()
                elapsed=0;manipulations=0;calls=[];payload={};handoff=None
                prefix=f'h{h}/t{anchor}/{arm}/'
                original=solver.solve
                def solve(*args,**kwargs):
                    nonlocal manipulations,payload
                    require((kwargs['delta_value'],kwargs['tau_value']) == spec.schedule(h,elapsed), 'Solve schedule')
                    if elapsed == anchor:
                        require(manipulations == 0 and not policy._action_buffer, 'Repeated intervention/buffer')
                        at=world.envs.envs[0].unwrapped
                        sp=f'h{h}/t{anchor}/'
                        np.testing.assert_allclose(at._get_obs(),saved[sp+'anchor_state'],rtol=0,atol=spec.ATOL)
                        np.testing.assert_allclose(body_fields(at),saved[sp+'anchor_controller'],rtol=0,atol=spec.ATOL)
                        result,payload=capture_selection(solver,original,args,kwargs,arm)
                        match_saved(payload,saved,h,anchor)
                        payload.update(anchor_state=at._get_obs().copy(),anchor_controller=np.asarray(body_fields(at)),
                            anchor_pixels=np.asarray(world.infos['pixels']).copy(),anchor_goal=goal_pixels.copy(),
                            decoder_mean=policy.process['action'].mean_.copy(),decoder_scale=policy.process['action'].scale_.copy())
                        manipulations+=1
                    else: result=original(*args,**kwargs)
                    diag=deepcopy(solver.diagnostic_history[-1])
                    plan=result['actions'].float().numpy().copy()
                    if elapsed == anchor:
                        require(all(diag[k] == archived_calls[elapsed]['diagnostics'][k] for k in LIFECYCLE),
                                'Intervention historical RNG/schedule')
                    if arm == 'continuation' or elapsed < anchor:
                        require(elapsed in archived_calls, 'Historical control call unavailable')
                        expected=archived_calls[elapsed]
                        require(array_hash(plan) == expected['plan_hash'], 'Historical selected plan')
                        require(all(diag[k] == expected['diagnostics'][k] for k in LIFECYCLE), 'Historical RNG/schedule')
                    calls.append({'at':elapsed,'plan_hash':array_hash(plan),'diagnostics':diag})
                    arrays[prefix+f'plan-{elapsed}']=plan
                    return result
                solver.solve=solve
                def info():
                    np.testing.assert_array_equal(world.infos['goal'],goal_pixels)
                    np.testing.assert_array_equal(world.infos['state'][0,-1],world.envs.envs[0].unwrapped._get_obs())
                    return computational_info(world.infos)
                def step(action):
                    nonlocal elapsed,primitive_steps
                    world.states,_,world.terminateds,world.truncateds,world.infos=world.envs.step(action)
                    elapsed+=1;primitive_steps+=1
                    state=world.envs.envs[0].unwrapped._get_obs().copy()
                    flags=np.array([bool(np.asarray(world.terminateds).any()),bool(np.asarray(world.truncateds).any())])
                    np.testing.assert_array_equal(world.infos['action'][0,-1],action[0])
                    if arm == 'continuation':
                        require(elapsed <= row['delivered'], 'Control overrun')
                        exact(action[0],history['actions'][elapsed-1])
                        np.testing.assert_allclose(state,history['states'][elapsed],rtol=0,atol=spec.ATOL)
                    return state,flags
                def observe(absolute,p):
                    nonlocal handoff
                    if absolute == anchor+15 and not (world.terminateds.any() or world.truncateds.any()):
                        require(not p._action_buffer and p._stage_index == absolute//15, 'Handoff lifecycle')
                        exact(solver.proposal_generator.get_state().cpu().numpy(),payload['proposal_after'])
                        exact(solver.gmm_generator.get_state().cpu().numpy(),payload['gmm_after'])
                        handoff={'absolute':absolute,'stage_index':p._stage_index,'buffer_length':0}
                try:
                    trace=spec.execute_branch(policy,info,step,observe,horizon=h,anchor=anchor,history=history)
                    require(manipulations == 1, 'Exactly one intervention required')
                    require([c['at'] for c in calls] == list(range(0,elapsed,15)), 'Planning call coverage')
                    if arm == 'continuation':
                        require(elapsed == row['delivered'] and bool(trace['flags'][:,0].any()) == bool(row['success'])
                            and bool(trace['flags'][-1,1]) == row['native_truncation'], 'Historical control terminal identity')
                    metrics=spec.physical(trace['states'],trace['flags'],goals[h],2*h-anchor)
                    branch_data[arm]=(payload,trace,calls)
                    for name,value in {**payload,**trace,'goal_state':goals[h],
                        'prefix_actions':history['actions'][:anchor]}.items(): arrays[prefix+name]=np.asarray(value)
                    rows.append({'horizon':h,'anchor':anchor,'arm':arm,'metrics':metrics,
                        'calls':calls,'interventions':manipulations,'handoff':handoff})
                finally:
                    solver.solve=original;world.close()
            control,treatment=branch_data['continuation'],branch_data['immediate']
            for key in control[0]:
                if key != 'chosen': exact(control[0][key],treatment[0][key])
            if int(control[0]['chosen']) == int(treatment[0]['chosen']):
                for key in control[1]: exact(control[1][key],treatment[1][key])
                require([(c['at'],c['plan_hash'],{k:c['diagnostics'][k] for k in LIFECYCLE}) for c in control[2]] ==
                        [(c['at'],c['plan_hash'],{k:c['diagnostics'][k] for k in LIFECYCLE}) for c in treatment[2]], 'Same-choice tail identity')
    require(tensor_hash(modules) == spec.MODEL_SHA, 'Models mutated')
    if repeat == 1:
        from verify_diffusion_branch import seal
        prior_dir=out.parent/f'ref-{reference}-repeat-0'
        prior_report,_=seal(prior_dir)
        require((prior_report['reference'],prior_report['repeat'])==(reference,0) and
                prior_report['source_manifest_sha256']==source_sha and
                prior_report['protocol_sha256']==protocol_sha,'Fresh repeat provenance')
        with np.load(prior_dir/'BANKS.npz',allow_pickle=False) as previous:
            require(set(previous.files)==set(arrays),'Fresh repeat schema')
            for key in arrays:exact(previous[key],arrays[key])
    with (out/'BANKS.npz').open('xb') as f: np.savez_compressed(f,**arrays)
    report={'reference':reference,'repeat':repeat,'all_technical_checks_passed':True,'rows':rows,
        'primitive_steps_including_replays':primitive_steps,'physical_branch_rollouts':8,
        'model_construction_seconds':construction_seconds,'wall_seconds_including_construction':time.perf_counter()-began,
        'model_state_sha256':spec.MODEL_SHA,'provenance':provenance,'model_provenance':model_provenance,
        'source_manifest_sha256':source_sha,'protocol_sha256':protocol_sha,
        'program_sha256':sha256(Path(__file__)),'banks_sha256':sha256(out/'BANKS.npz'),
        'gpu_peak_allocated_bytes':torch.cuda.max_memory_allocated(),'gpu_peak_reserved_bytes':torch.cuda.max_memory_reserved(),
        'protected_payload_reads':0,'unevaluated_reference_payload_reads':0,'training_runs':0,'historical_decision_changed':False}
    with (out/'REPORT.json').open('x') as f: json.dump(report,f,indent=2,sort_keys=True,allow_nan=False)
    with (out/'sha256.txt').open('x') as f:
        for name in ('BANKS.npz','REPORT.json'): f.write(sha256(out/name)+'  '+name+'\n')


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    for name in ('out','combined','approval','source','protocol'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--reference',type=int,required=True);p.add_argument('--repeat',type=int,required=True)
    p.add_argument('--source-sha',required=True);p.add_argument('--protocol-sha',required=True)
    a=p.parse_args()
    from verify_diffusion_extension import verify_source
    verify_source(a.source,a.source_sha);require_sha(a.protocol,a.protocol_sha)
    spec.check_approval(a.approval,a.source_sha,a.protocol_sha)
    run(a.reference,a.repeat,a.out,a.combined,a.source_sha,a.protocol_sha)
