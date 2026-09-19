"""Frozen LGP1 endpoint/driver path with explicit original model roots/budget."""
import importlib.util,hashlib,json,time,types
import numpy as np
import torch
import lgprb1_contract as c
from lgp1_runtime import FrozenBackend,Policy
from lgp1_endpoint import identity,verify_file,array_sha
from e18_fresh_driver import FreshEpisode,computational_info

def load(source,spec):
    import stable_worldmodel as swm
    from pusht_fresh_initialization import register
    from lgp1_train import load_model
    from independent_pusht_runtime import tensor_hash
    lock=c.read(source/c.old.DOC/'INPUTS.json');reuse=c.verify_reuse(source,all_workers=False)
    model,stats=load_model(c.OLD_FITS/f"fit-{spec['family']}-{spec['seed']}")
    backend=FrozenBackend(lock);modules=[backend.lewm,backend.generator,model]
    ref=lock['references'][str(spec['reference'])]
    c.require(c.sha(ref['file'])==ref['sha256'],'Same allowlisted reference')
    with np.load(ref['file'],allow_pickle=False) as z:
        initial=z['initial_request'].copy();goals={h:z['states'][h].copy() for h in (75,150)}
    def world():return swm.World(register(),num_envs=1,image_shape=(224,224),max_episode_steps=300,correct_velocity_space=True,verbose=0)
    return backend,model,stats,ref,initial,goals,world,modules,tensor_hash

def evaluate(source,out,spec,guard):
    began=time.monotonic()
    backend,model,stats,ref,initial,goals,make_world,modules,tensor_hash=load(source,spec)
    before=tensor_hash(modules);world=make_world();rows=[];setup=time.monotonic()-began
    episode=FreshEpisode(world,lambda h,s:Policy(backend,model,stats,h,s,spec['reference'],guard,
        populations=spec['populations'],record_bank_hashes=True))
    try:
        for h in (75,150):
            guard();episode_began=time.monotonic();events=[];states=[];flags=[];initialized=[];steps=[];stages=[];tick=[0.];physics=[0.]
            def observe(event,**kw):
                if event=='initialized':initialized.append(kw['env']._get_obs().copy())
                if event=='action':events.append(kw['action'].copy());tick[0]=time.monotonic()
                if event=='after_action':
                    physics[0]+=time.monotonic()-tick[0]
                    raw=world.envs.envs[0].unwrapped._get_obs().copy()
                    np.testing.assert_array_equal(raw,kw['info']['state'][0,-1]);states.append(raw)
                    flags.append([bool(world.terminateds[0]),bool(world.truncateds[0])]);steps.append(kw['steps']);stages.append(episode.policy._stage_index-1)
            episode.observe=observe
            reset_began=time.monotonic()
            episode.start(dict(state=initial,goal_state=goals[h],proprio=initial[[0,1,5,6]]),horizon=h,budget=2*h,seed=spec['seed'])
            reset_seconds=time.monotonic()-reset_began
            while episode.status=='running':episode.advance()
            policy=episode.policy;policy.finish()
            c.require(policy.terminal and not policy.history and not policy._action_buffer,'Unchanged teardown')
            row=dict(reference=spec['reference'],family=spec['family'],seed=spec['seed'],horizon=h,populations=spec['populations'],
                success=int(bool(np.asarray(world.terminateds).any())),steps=episode.steps,
                terminated=bool(np.asarray(world.terminateds).any()),truncated=bool(np.asarray(world.truncateds).any()),
                endpoint_identity=identity(ref,initial,goals[h],h),physics_delivery_seconds=physics[0],
                reset_seconds=reset_seconds,episode_execution_seconds=time.monotonic()-episode_began,
                failure=None,stages=policy.diagnostic_history,reused=False)
            np.savez_compressed(out/f'endpoint-h{h}.npz',actions=np.concatenate(events,0),post_states=np.stack(states),
                flags=np.asarray(flags,dtype=bool),requested_initial=initial,initialized_state=initialized[0],goal_state=goals[h],
                absolute_steps=np.asarray(steps,np.int64),physical_remaining=2*h-np.asarray(steps,np.int64),action_stage=np.asarray(stages,np.int64))
            row['endpoint_check']=verify_file(out,row,ref)
            size=(out/f'endpoint-h{h}.npz').stat().st_size
            c.require(size<=50000 and size+len(json.dumps(row,sort_keys=True,indent=2).encode())<=c.CAPS['episode_bytes'],'Existing compact endpoint allowance')
            rows.append(row)
    finally:world.close()
    c.require(tensor_hash(modules)==before,'Frozen tensors changed')
    return dict(rows=rows,models_unchanged=True,episodes=2,setup_seconds=setup,
        model_tensor_sha256=before,freeze_sha256=c.FREEZE_SHA)

def legacy_module(source):
    path=source/c.DOC/'LEGACY-RUNTIME.py.txt';expected=c.read(source/c.DOC/'REUSE.json')['legacy_runtime_sha256']
    c.require(c.sha(path)==expected,'Exact executed Policy source')
    module=types.ModuleType('executed_lgp1_runtime');module.__file__=str(path)
    exec(compile(path.read_text(),str(path),'exec'),module.__dict__)
    return module

def compatibility(source,out,spec,guard):
    # No world.step/episode.advance: 16 total first-decision checks, zero delivered actions.
    backend,model,stats,ref,initial,goals,make_world,modules,tensor_hash=load(source,spec)
    before=tensor_hash(modules);legacy=legacy_module(source);records=[]
    for h in (75,150):
        same=[]
        for budget in ('legacy30',1,5,30):
            guard();world=make_world();captured={};calls=[]
            klass=legacy.Policy if budget=='legacy30' else Policy
            kwargs={} if budget=='legacy30' else dict(populations=budget,record_bank_hashes=True)
            if budget=='legacy30':
                original=legacy.sample
                def observed(*args,**kw):
                    bank=original(*args,**kw)
                    transformed=legacy.affine(bank,stats['action_mean'],stats['action_std'],backend.mean,backend.std)
                    captured['initial_unprojected_bank_sha256']=array_sha(transformed.detach().cpu().numpy())
                    return bank
                legacy.sample=observed
            e=FreshEpisode(world,lambda hh,ss:klass(backend,model,stats,hh,ss,spec['reference'],guard,**kwargs))
            try:
                e.start(dict(state=initial,goal_state=goals[h],proprio=initial[[0,1,5,6]]),horizon=h,budget=2*h,seed=spec['seed'])
                p=e.policy;action=p.get_action(computational_info(world.infos))
                chunk=np.concatenate([action]+list(p._action_buffer),0)
                c.require(e.steps==0 and chunk.shape==(15,2),'No technical action delivery')
                log=p.diagnostic_history[0]
                same.append(dict(budget=budget,context=log['context_sha256'],
                    bank=captured.get('initial_unprojected_bank_sha256',log.get('initial_unprojected_bank_sha256')),
                    action_sha256=array_sha(chunk),rounds=log['rounds']))
                p.finish()
            finally:
                world.close()
                if budget=='legacy30':legacy.sample=original
        c.require(len({r['context'] for r in same})==len({r['bank'] for r in same})==1,'Common-state proposal bank differs by budget')
        c.require(same[0]['action_sha256']==same[3]['action_sha256'] and same[0]['rounds']==same[3]['rounds'],'New30 versus executed legacy30')
        records.append(dict(horizon=h,reference=spec['reference'],family=spec['family'],seed=spec['seed'],
            same_bank_sha256=same[0]['bank'],context_sha256=same[0]['context'],legacy_new30_action_sha256=same[0]['action_sha256'],
            checked_budgets=['legacy30',1,5,30],first_decisions=4,physical_actions=0))
    c.require(tensor_hash(modules)==before,'Compatibility changed model tensors')
    return dict(passed=True,records=records,first_decisions=8,episodes=0,physical_actions=0,
        models_unchanged=True,historical_raw_bank_equality_claim=False)
