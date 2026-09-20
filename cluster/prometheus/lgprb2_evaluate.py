"""Eight fixed episodes; shared read-only weights, fresh World/Policy per cell."""
import json,time
from pathlib import Path
import numpy as np
import lgprb2_contract as c
from lgp1_runtime import FrozenBackend,Policy
from lgp1_endpoint import identity,verify_file
from e18_fresh_driver import FreshEpisode

from lgprb2_contract import cell_name
from lgprb2_payload import write_payload

def load_bundle(source,spec):
    import stable_worldmodel as swm
    from pusht_fresh_initialization import register
    from lgp1_train import load_model
    from independent_pusht_runtime import tensor_hash
    lock=c.read(source/c.DOC/'INPUTS.json');c.verify_models(source)
    backend=FrozenBackend(lock)
    models={f:load_model(c.rb1.OLD_FITS/f"fit-{f}-{spec['seed']}") for f in c.old.FAMILIES}
    modules=[backend.lewm,backend.generator]+[models[f][0] for f in c.old.FAMILIES]
    ref=lock['references'][str(spec['reference'])]
    c.require(c.sha(ref['file'])==ref['sha256'],'Allowlisted source bytes')
    with np.load(ref['file'],allow_pickle=False) as z:
        initial=z['initial_request'].copy();goals={h:z['states'][h].copy() for h in (75,150)}
    def world():return swm.World(register(),num_envs=1,image_shape=(224,224),max_episode_steps=300,correct_velocity_space=True,verbose=0)
    return backend,models,ref,initial,goals,world,modules,tensor_hash

def run_cell(bundle,out,spec,cell,guard):
    backend,models,ref,initial,goals,make_world,modules,tensor_hash=bundle
    h=cell['horizon'];model,stats=models[cell['family']]
    started=time.monotonic();world=make_world();creation=time.monotonic()-started
    policy_factory=lambda hh,ss:Policy(backend,model,stats,hh,ss,spec['reference'],guard,
                                      populations=cell['populations'],record_bank_hashes=True)
    episode=FreshEpisode(world,policy_factory)
    actions=[];states=[];flags=[];initialized=[];steps=[];stages=[];tick=[0.];physics=[0.]
    def observe(event,**kw):
        if event=='initialized':initialized.append(kw['env']._get_obs().copy())
        if event=='action':actions.append(kw['action'].copy());tick[0]=time.monotonic()
        if event=='after_action':
            physics[0]+=time.monotonic()-tick[0]
            raw=world.envs.envs[0].unwrapped._get_obs().copy()
            np.testing.assert_array_equal(raw,kw['info']['state'][0,-1]);states.append(raw)
            flags.append([bool(world.terminateds[0]),bool(world.truncateds[0])])
            steps.append(kw['steps']);stages.append(episode.policy._stage_index-1)
    episode.observe=observe
    try:
        guard();reset_started=time.monotonic()
        episode.start(dict(state=initial.copy(),goal_state=goals[h].copy(),proprio=initial[[0,1,5,6]].copy()),
                      horizon=h,budget=2*h,seed=spec['seed'])
        reset_seconds=time.monotonic()-reset_started
        while episode.status=='running':episode.advance()
        policy=episode.policy;policy.finish()
        c.require(policy.terminal and not policy.history and not policy._action_buffer,'Complete fresh-policy teardown')
        row=dict(reference=spec['reference'],seed=spec['seed'],**cell,steps=episode.steps,
            success=int(bool(np.asarray(world.terminateds).any())),terminated=bool(np.asarray(world.terminateds).any()),
            truncated=bool(np.asarray(world.truncateds).any()),failure=None,reused=False,
            endpoint_identity=identity(ref,initial,goals[h],h),stages=policy.diagnostic_history,
            world_creation_seconds=creation,reset_seconds=reset_seconds,physics_delivery_seconds=physics[0])
        out.mkdir(exist_ok=False)
        np.savez_compressed(out/f'endpoint-h{h}.npz',actions=np.concatenate(actions,0),post_states=np.stack(states),
            flags=np.asarray(flags,bool),requested_initial=initial,initialized_state=initialized[0],goal_state=goals[h],
            absolute_steps=np.asarray(steps,np.int64),physical_remaining=2*h-np.asarray(steps,np.int64),action_stage=np.asarray(stages,np.int64))
        verify_started=time.monotonic();row['endpoint_check']=verify_file(out,row,ref)
        row['evidence_verification_seconds']=time.monotonic()-verify_started
        c.require((out/f'endpoint-h{h}.npz').stat().st_size<=c.CAPS['endpoint_bytes'],'Compact endpoint cap')
    finally:
        if getattr(episode,'policy',None) is not None:episode.policy.finish()
        close_started=time.monotonic();world.close();close_seconds=time.monotonic()-close_started
    row['world_close_seconds']=close_seconds
    row['complete_episode_seconds']=time.monotonic()-started
    c.require(len(json.dumps(row).encode())+c.old.size(out)<=c.CAPS['episode_bytes'],'Per-episode storage cap')
    write_payload(out/'EPISODE.json',row)
    return row

def technical_checks(rows):
    c.require(len(rows)==8,'Eight episodes')
    for f in c.old.FAMILIES:
        for h in (75,150):
            pair=[r for r in rows if r['family']==f and r['horizon']==h]
            c.require(len(pair)==2 and {r['populations'] for r in pair}=={5,30},'Paired budget identity')
            for key in ('context_sha256','initial_unprojected_bank_sha256','initial_projected_bank_sha256'):
                c.require(len({r['stages'][0][key] for r in pair})==1,'Common-initial-state bank differs by budget')
    return dict(common_initial_banks=True,fresh_episode_ownership=True,endpoint_checks_passed=8)

def evaluate(source,out,spec,guard):
    started=time.monotonic();bundle=load_bundle(source,spec);setup=time.monotonic()-started
    before=bundle[-1](bundle[-2]);rows=[]
    for cell in spec['episodes']:
        guard();rows.append(run_cell(bundle,out/cell_name(cell),spec,cell,guard))
        c.require(bundle[-1](bundle[-2])==before,'Read-only shared tensors changed')
    checks=technical_checks(rows)
    return dict(rows=rows,episodes=8,models_unchanged=True,model_tensor_sha256=before,
                freeze_sha256=c.FREEZE_SHA,setup_seconds=setup,technical_checks=checks)
