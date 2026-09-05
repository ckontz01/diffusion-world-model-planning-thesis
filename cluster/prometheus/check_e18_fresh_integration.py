"""Fixed exposed-record actual-planner integration; no efficacy reducer."""
import argparse
from copy import deepcopy
import hashlib
import inspect
import json
from pathlib import Path
import numpy as np
import torch
import gdp_cem_e19_r1 as r1
from gdp_cem_e19_r3_validation import inputs, check_start, physical, ENV_SHA
from gdp_cem_e19_r3_arms import setup, E18_ARMS
from e18_fresh_driver import FreshEpisode, complete_slots, computational_info
from pusht_fresh_initialization import register

INIT_SHA = '798bb6749dd30b9c6a91ac7018422edbefd356f3bb6bc322bd8ca95987506a65'


def module_hash(modules):
    h = hashlib.sha256()
    for m in modules:
        for key, tensor in sorted(m.state_dict().items()):
            h.update(key.encode())
            h.update(str((tensor.dtype, tuple(tensor.shape))).encode())
            h.update(tensor.detach().cpu().contiguous().reshape(-1).view(torch.uint8).numpy().tobytes())
    return h.hexdigest()


def coefficient_gate(policy, solver):
    scaler, stats = policy.process['action'], solver.statistics
    mean = stats.planner_action_mean.cpu().numpy()
    std = stats.planner_action_std.cpu().numpy()
    np.testing.assert_array_equal(np.asarray(scaler.mean_, dtype=np.float32), mean)
    np.testing.assert_array_equal(np.asarray(scaler.scale_, dtype=np.float32), std)
    raw = np.asarray([[-.99, .99], [0, 0], [.17, -.31]], dtype=np.float32)
    normalized = (raw - mean) / std
    decoded = scaler.inverse_transform(normalized.copy())
    np.testing.assert_allclose(decoded, raw, rtol=1e-6, atol=2e-7)
    values = {k: v.detach().cpu().tolist() if torch.is_tensor(v) else v
              for k, v in vars(stats).items()}
    return dict(checkpoint_statistics=values, action_mean=np.asarray(scaler.mean_).tolist(),
                action_scale=np.asarray(scaler.scale_).tolist(), fit_called=False,
                planner_action_coefficients_equal_float32=True,
                max_action_roundtrip_error=float(np.abs(decoded-raw).max()))


@torch.inference_mode()
def dependency_gate(policy, solver, info):
    # No synthetic coefficient fitting: delete irrelevant fields, retain real pixels.
    prepared = policy._prepare_info(deepcopy(info))
    minimal = policy._prepare_info(computational_info(info))
    full_emb = solver._encode(prepared)
    small_emb = solver._encode(minimal)
    assert all(torch.equal(a, b) for a, b in zip(full_emb, small_emb))
    seen = []
    class Reads(dict):
        def __getitem__(self, key):
            seen.append(key)
            return super().__getitem__(key)
    probe = Reads({k:v.to(solver.device) for k,v in prepared.items() if torch.is_tensor(v) and k!='action'})
    solver.world_model.encode(probe)
    assert set(seen) == {'pixels'}, seen
    raw = torch.as_tensor(np.asarray(info['state'])[:, -1], device=solver.device, dtype=torch.float32)
    condition = solver._condition(*small_emb, raw)
    torch.testing.assert_close(condition[2], (raw-solver.statistics.state_mean)/solver.statistics.state_std,
                               rtol=0, atol=0)
    return dict(non_action_evaluator_scalers_computationally_required=False,
                encoder_mapping_reads=sorted(set(seen)), full_minimal_latents_bit_identical=True,
                raw_state_checkpoint_normalization_exact=True,
                model_type=type(solver.world_model).__module__+'.'+type(solver.world_model).__name__,
                encode_source=inspect.getsource(type(solver.world_model).encode),
                predict_source=inspect.getsource(type(solver.world_model).predict),
                source_sha256=r1.sha(inspect.getsourcefile(type(solver.world_model))),
                world_model_episode_cache_attributes=[k for k in vars(solver.world_model)
                    if any(token in k.lower() for token in ('cache','history','goal'))])


class Audit:
    def __init__(self):
        self.rows=[]
        self.steps=0
        self.dep=None
        self.proposal_decoding_checks=0

    def observe(self, event, **data):
        if event == 'before_reset':
            self.record=data['record']; self.before_steps=self.steps
        elif event == 'initialized':
            assert self.before_steps == self.steps
            env, policy, info = data['env'], data['policy'], data['info']
            check_start(env,self.record,{'state':env._get_obs(),'proprio':env._get_obs()[[0,1,5,6]]})
            np.testing.assert_array_equal(info['pixels'][0,-1], self.world.envs.envs[0].render())
            assert policy._stage_index==0 and not policy._action_buffer
            solver=policy.planner
            from gdp_cem_e18_closed_loop import generator_state_sha256
            self.row=dict(initial=r1.digest(physical(env)), inputs=r1.digest(computational_info(info)),
                seed=data['seed'], fresh_rng=[generator_state_sha256(solver.proposal_generator),
                                            generator_state_sha256(solver.gmm_generator)],
                plans=[],actions=[],post_states=[],delivered=0,budget_exhausted=False)
            self.rows.append(self.row)
            if self.dep is None:
                self.dep=dependency_gate(policy,solver,info)
            original=solver.solve
            propose=solver._propose
            def audited_propose(**kw):
                raw, normalized, third=propose(**kw)
                reconstructed=(normalized*solver.statistics.planner_action_std+solver.statistics.planner_action_mean)
                # Padding is zero in planner coordinates, not a delivered action.
                from gdp_cem_e15_models import action_active_mask
                mask=action_active_mask(kw['tau'],primitive_action_dim=2)[:,None].expand_as(raw)
                torch.testing.assert_close(reconstructed[mask], raw[mask], rtol=1e-6, atol=2e-7)
                self.proposal_decoding_checks+=1
                return raw,normalized,third
            solver._propose=audited_propose
            def solve(payload, **kw):
                np.testing.assert_array_equal(kw['raw_state'].numpy(),
                    np.asarray(self.world.infos['state'])[:, -1].astype(np.float32))
                out=original(payload,**kw)
                self.plan=out['actions'].reshape(1,15,2).numpy().copy()
                self.row['plans'].append(dict(at=self.row['delivered'],delta=kw['delta_value'],
                    tau=kw['tau_value'],input=r1.digest(computational_info(self.world.infos)),
                    actions=r1.digest(self.plan)))
                assert len(solver.diagnostic_history)==len(self.row['plans'])
                d=solver.diagnostic_history[-1]
                assert d['call']==len(self.row['plans'])-1
                for field in ('proposal','gmm'):
                    before=d[field+'_generator_before_sha256']
                    if len(self.row['plans'])==1:
                        assert before==self.row['fresh_rng'][0 if field=='proposal' else 1]
                    else:
                        assert before==solver.diagnostic_history[-2][field+'_generator_after_sha256']
                return out
            solver.solve=solve
        elif event == 'before_action':
            np.testing.assert_array_equal(data['info']['state'][0,-1],self.world.envs.envs[0].unwrapped._get_obs())
        elif event == 'action':
            stats=data['policy'].planner.statistics
            expected=self.plan[:,data['steps']%15]*stats.planner_action_std.cpu().numpy()+stats.planner_action_mean.cpu().numpy()
            np.testing.assert_allclose(data['action'],expected,rtol=1e-6,atol=2e-7)
            self.row['actions'].append(r1.digest(data['action']))
        elif event == 'after_action':
            self.row['delivered']=data['steps']
            self.row['post_states'].append(r1.digest(physical(self.world.envs.envs[0].unwrapped)))
            if data['done']:
                self.row['budget_exhausted']=data['budget_exhausted']


def run(arm,out):
    import stable_worldmodel as swm
    import pymunk
    from stable_worldmodel.envs.pusht.env import PushT
    from gdp_cem_e18_closed_loop import E18Planner
    from gdp_cem_e18_runtime import E18ScheduledPolicy
    from evaluate_gdp_cem_e18 import image_transform
    import gdp_cem_e18_specs as spec
    import pusht_fresh_initialization as init
    assert r1.sha(inspect.getsourcefile(init))==INIT_SHA
    assert r1.sha(inspect.getsourcefile(PushT))==ENV_SHA['e18']
    cases=inputs('e18')
    make, template, modules, provenance=setup('e18',arm)
    coefficients=coefficient_gate(make(),template)  # before any planning
    before_hash=module_hash(modules)
    assert not [k for k in vars(template.world_model) if any(t in k.lower() for t in ('cache','history','goal'))]
    def factory(horizon,seed):
        solver=E18Planner(template.world_model,arm=arm,statistics=template.statistics,
            state_dim=7,primitive_action_dim=2,proposer=template.proposer,
            state_adapter=template.state_adapter,batch_size=1,proposal_seed=seed)
        return E18ScheduledPolicy(solver,schedule=spec.schedule_for(horizon),environment_budget=2*horizon,
            state_key='state',process={'action':make().process['action']},
            transform={'pixels':image_transform(224),'goal':image_transform(224)})
    register()
    worlds=[];audits=[];slots=[]
    for i in range(3):
        w=swm.World(register(),num_envs=1,image_shape=(224,224),max_episode_steps=300,
                    correct_velocity_space=True,verbose=0)
        a=Audit();a.world=w
        worlds.append(w);audits.append(a);slots.append(FreshEpisode(w,factory,observe=a.observe))
    native=pymunk.Space.step
    legacy=PushT._set_state
    def forbidden(*args,**kw):raise RuntimeError('legacy setter reached from fresh driver')
    def counted(space,dt):
        for a in audits:a.steps+=1
        return native(space,dt)
    pymunk.Space.step=counted;PushT._set_state=forbidden
    campaigns=[]
    def campaign(which,ids,horizon):
        before=audits[0].steps
        for idx,cid in zip(which,ids):
            seed=spec.derived_seed(f'fresh-integration|episode={cases[cid]["identity"]["episode"]}|h={horizon}|replicate=1')
            slots[idx].start(cases[cid]['record'],horizon=horizon,budget=31,seed=seed)
            assert audits[0].steps==before
        complete_slots([slots[i] for i in which])
        rows=[deepcopy(audits[i].rows[-1]) for i in which]
        for row in rows:
            assert 1<=row['delivered']<=31
            assert [p['at'] for p in row['plans']]==list(range(0,row['delivered'],15))
        assert any(len(row['plans'])>=2 for row in rows), 'replanning gate not exercised'
        assert audits[0].steps-before==10*sum(r['delivered'] for r in rows)
        campaigns.append(dict(slots=which,cases=ids,horizon=horizon,rows=rows))
    try:
        campaign([0],[0],75)
        campaign([0,1,2],[0,1,2],75)
        assert campaigns[0]['rows'][0]==campaigns[1]['rows'][0], 'singleton/three-slot differs'
        campaign([0,1,2],[0,1,2],75)
        assert campaigns[1]['rows']==campaigns[2]['rows'], 'fresh second episode differs'
        campaign([0,1,2],[1,2,0],150)
        # Terminal drivers reject extra planning/stepping, irrespective of stop cause.
        for s in slots:
            try:s.advance()
            except RuntimeError:pass
            else:raise AssertionError('completed episode accepted an action')
        assert module_hash(modules)==before_hash
    finally:
        pymunk.Space.step=native;PushT._set_state=legacy
        for w in worlds:w.close()
    assert r1.sha(inspect.getsourcefile(init))==INIT_SHA
    r1.seal(out/'INTEGRATION.json',dict(all_passed=True,arm=arm,provenance=provenance,
        coefficient_gate=coefficients,dependency_gate=audits[0].dep,inputs=[c['identity'] for c in cases],
        input_hashes=[c['input_sha256'] for c in cases],campaigns=campaigns,
        module_state_sha256=before_hash,checkpoints_modified=False,initializer_sha256=INIT_SHA,
        initializer_modified=False,historical_results_modified=False,protected_read=False,holdout_read=False,
        performance_metric_recorded=False,efficacy_claim=False,probe_fitted_scalers=False,
        actual_planner_calls=sum(len(row['plans']) for c in campaigns for row in c['rows']),
        primitive_actions=sum(row['delivered'] for c in campaigns for row in c['rows']),
        proposal_decode_checks=sum(a.proposal_decoding_checks for a in audits),
        fresh_initialization_physics_steps=0,native_vector_batch_size=1,interleaved_slots=[1,3]))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--arm',choices=E18_ARMS,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert r1.ROOT/'experiments/e18-fresh-integration' in a.output.resolve().parents
    if a.arm=='vad_greedy_300':
        import subprocess,sys
        subprocess.run([sys.executable,'-m','pytest','-q','-p','no:cacheprovider',
                        str(Path(__file__).with_name('test_e18_fresh_driver.py'))],check=True)
    torch.set_num_threads(4);run(a.arm,a.output)
