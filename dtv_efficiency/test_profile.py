"""Artificial CPU integration and semantic tests; no research bytes loaded."""
import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

import torch
from torch import nn
from gymnasium.spaces import Box
import numpy as np
from dtv_efficiency import profile as p
from dtv_efficiency import campaign,accept,package as pack

ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'docs/dtv-efficiency-20260930/evidence'
sys.path.insert(0,str(E/'snapshots/acid-alternative-core-v1-52acea39e4a1f6da'))
from acid_alternative import costs as core, models as m
# Only the historical loader's import is mocked. No real checkpoint is loaded.
mock=types.ModuleType('acid_alternative.evaluate_matched')
mock.load_scorer=lambda *a,**k:(_ for _ in ()).throw(RuntimeError('research loading forbidden in artificial tests'))
sys.modules['acid_alternative.evaluate_matched']=mock
spec=importlib.util.spec_from_file_location('artificial_d2',E/'snapshots/acid-alt-v3-d2-2c8f890c31e9f5bf/acid_alt_d2_models.py')
d2=importlib.util.module_from_spec(spec);spec.loader.exec_module(d2)
package=types.ModuleType('artificial_swm');package.__path__=[]
stub=types.ModuleType('artificial_swm.solver');stub.Costable=object
sys.modules['artificial_swm']=package;sys.modules['artificial_swm.solver']=stub
spec=importlib.util.spec_from_file_location('artificial_swm.cem',E/'runtime/stable_worldmodel/solver/cem.py')
cem=importlib.util.module_from_spec(spec);spec.loader.exec_module(cem)
torch.set_num_threads(4);torch.set_num_interop_threads(1)

class World(nn.Module):
    def __init__(self):super().__init__();self.dummy=nn.Parameter(torch.zeros(1),requires_grad=False);self.rollouts=0
    def encode(self,info):return {'emb':info['pixels']}
    def rollout(self,info,actions):
        self.rollouts+=1
        start=info['pixels'][...,0,:];increments=torch.cat((actions,actions),dim=-1)
        trajectory=torch.cat((start[:,:,None],start[:,:,None]+increments.cumsum(dim=2)),dim=2)
        info['predicted_emb']=trajectory;return info
    def criterion(self,info):return (info['predicted_emb'][:,:,-1]-info['goal_emb'][:,None,-1,:]).square().mean(-1)

class Integration(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(99);self.world=World();self.job=dict(task='pusht',scorer_seed=6101,planner_seed=7101)
        self.models=dict(acid=m.FlowInverseDynamics(4,2,width=6,depth=1,heads=2,mlp_ratio=2),diffusion=m.ConditionalDiffusionVerifier(4,2,width=8,depth=1,noise_embedding_dim=4),forward=m.DeterministicForwardVerifier(4,2,width=8,depth=1))
        for model in self.models.values():model.eval().requires_grad_(False)
        self.payloads={arm:dict(seed=6101,model_config=dict(latent_dim=4),latent_mean=torch.zeros(4),latent_std=torch.ones(4),acid_action_mean=torch.zeros(2),acid_action_std=torch.ones(2)) for arm in self.models}
        self.info=dict(pixels=torch.zeros(1,1,4),goal=torch.ones(1,1,4))
        self.expanded={k:v[:,None].expand(1,300,*v.shape[1:]) for k,v in self.info.items()}
        self.actions=torch.randn(1,300,5,2);self.trajectory=torch.randn(1,300,6,4);self.goal=torch.ones(1,1,4)
    def wrapper(self,arm):return p.make_wrapper(core,d2,self.world,self.models,self.payloads,self.job,arm,device='cpu')
    def solver(self,w):
        s=cem.CEMSolver(w,num_samples=300,n_steps=30,topk=30,seed=7101)
        s.configure(action_space=Box(-np.inf,np.inf,shape=(1,2),dtype=np.float32),n_envs=1,config=types.SimpleNamespace(horizon=5,action_block=1));return s
    def test_all_five_original_delegated_paths(self):
        for arm in p.ARMS:
            w1,w2=self.wrapper(arm),self.wrapper(arm)
            a,b=w1.get_cost(self.expanded,self.actions),w2.get_cost(self.expanded,self.actions)
            p.equivalent(torch,a,b);self.assertEqual(a.shape,(1,300))
            self.assertTrue(torch.equal(torch.topk(a,30,largest=False).indices,torch.topk(b,30,largest=False).indices))
    def test_dtv_literal_matches_original_multilevel_equation(self):
        w=self.wrapper('legacy_dtv');v=p.raw(w,self.trajectory,self.actions,self.goal)
        old=core.SharedRolloutCostModel(self.world,arm='diffusion',scorer=self.models['diffusion'],latent_mean=torch.zeros(4),latent_std=torch.ones(4),noise_seed=6101,lambda_weight=.005)
        p.equivalent(torch,v,old._diffusion_cost(self.trajectory,self.actions))
    def test_single_noise_bank_is_new_first_draw_not_legacy_middle(self):
        single=self.wrapper('d1_sigma025');legacy=self.wrapper('legacy_dtv')
        expected=torch.randn(1,5,4,generator=torch.Generator().manual_seed(6101))
        self.assertTrue(torch.equal(single.diffusion_noise,expected))
        self.assertFalse(torch.equal(single.diffusion_noise[0],legacy.legacy_dtv_noise_bank[1]))
        self.assertEqual(single.diffusion_sigmas,(.25,));self.assertEqual(single.lambda_weight,.07)
        # CPU randn's tail algorithm can depend on requested shape. The real
        # 192-latent bank is tested separately, not inferred from a tiny fixture.
        real_single=torch.randn(1,5,192,generator=torch.Generator().manual_seed(6101))
        real_multi=torch.randn(3,5,192,generator=torch.Generator().manual_seed(6101))
        self.assertTrue(torch.equal(real_single[0],real_multi[0]))
        self.assertFalse(torch.equal(real_single[0],real_multi[1]))
    def test_d1_reduction_and_scaling(self):
        w=self.wrapper('d1_sigma025');goal,trajectory,actions,emb=w._rollout_once(self.expanded,self.actions)
        raw=w._diffusion_cost(trajectory,actions);expected=goal+.07*goal.std(dim=1,unbiased=True)[:,None]/raw.std(dim=1,unbiased=True).clamp_min(1e-8)[:,None]*raw
        p.equivalent(torch,expected,w.get_cost(self.expanded,self.actions))
    def test_v3_forward_and_acid_lambdas(self):
        self.assertEqual(self.wrapper('legacy_dtv').lambda_weight,.005)
        self.assertEqual(self.wrapper('forward').lambda_weight,.005)
        self.assertEqual(self.wrapper('acid').lambda_weight,.07)
    def test_no_score_cache_and_one_rollout_each_call(self):
        w=self.wrapper('legacy_dtv');a=w.get_cost(self.expanded,self.actions);b=w.get_cost(self.expanded,self.actions+1)
        self.assertEqual(self.world.rollouts,2);self.assertFalse(torch.equal(a,b))
    def test_chunks_preserve_dtv_forward_and_acid_draws(self):
        bank=d2.build_legacy_dtv_noise_bank(scorer_seed=6101,horizon=5,latent_dim=4)
        for chunk in (None,17,8192):
            v=d2.legacy_dtv_costs(self.models['diffusion'],trajectory=self.trajectory,actions=self.actions,latent_mean=torch.zeros(4),latent_std=torch.ones(4),noise_bank=bank,batch_size=chunk)
            if chunk is None:reference=v
            else:p.equivalent(torch,reference,v)
        a=d2.acid_literal_costs(self.models['acid'],trajectory=self.trajectory,actions=self.actions,action_mean=torch.zeros(2),action_std=torch.ones(2),generator=torch.Generator().manual_seed(3),batch_size=None)
        b=d2.acid_literal_costs(self.models['acid'],trajectory=self.trajectory,actions=self.actions,action_mean=torch.zeros(2),action_std=torch.ones(2),generator=torch.Generator().manual_seed(3),batch_size=17)
        p.equivalent(torch,a,b)
    def test_operational_cpu_diagnostics_retained(self):
        for arm in p.ARMS:
            w=self.wrapper(arm);w.get_cost(self.expanded,self.actions)
            self.assertEqual(len(w.diagnostic_history),1)
    def test_cem_trace_indices_plan_rng_full_thirty_rounds(self):
        for arm in p.ARMS:
            w1,w2=self.wrapper(arm),self.wrapper(arm);t=p.Trace(w2);s1,s2=self.solver(w1),self.solver(t)
            with contextlib.redirect_stdout(io.StringIO()):a,b=s1.solve(self.info),s2.solve(self.info)
            p.equivalent(torch,a,b);self.assertEqual(len(t.rows),30)
            self.assertTrue(torch.equal(s1.torch_gen.get_state(),s2.torch_gen.get_state()))
            acts,_,indices=t.rows[-1];p.equivalent(torch,acts[torch.zeros_like(indices),indices].mean(1).cpu(),a['actions'])
    def test_separate_owned_equal_initial_streams_diverge_by_decisions(self):
        left,right=p.Trace(self.wrapper('plain')),p.Trace(self.wrapper('d1_sigma025'))
        with contextlib.redirect_stdout(io.StringIO()):self.solver(left).solve(self.info);self.solver(right).solve(self.info)
        self.assertTrue(torch.equal(left.rows[0][0],right.rows[0][0]))
        self.assertFalse(torch.equal(left.rows[1][0],right.rows[1][0]))
    def test_warmup_reset_cost_call_index(self):
        w=self.wrapper('acid');a=w.get_cost(self.expanded,self.actions);w.get_cost(self.expanded,self.actions)
        p.reset(w);b=w.get_cost(self.expanded,self.actions);self.assertTrue(torch.equal(a,b))
        p.reset(w,raw_call=True);self.assertEqual(w.call_count,1)
    def test_equivalence_rejects_changed_values_without_tolerance_relaxation(self):
        with self.assertRaises(RuntimeError):p.equivalent(torch,torch.zeros(3),torch.ones(3)*.001)

class Contract(unittest.TestCase):
    def test_disabled_gate_before_torch_or_payload_access(self):
        approval=json.loads((p.DOC/'EXECUTION-APPROVAL.json').read_text())
        with self.assertRaisesRegex(RuntimeError,'disabled'):p.gate(p.DOC/'BINDINGS.json',approval)
    def test_wrong_binding_and_missing_authority_rejected(self):
        with self.assertRaises(RuntimeError):p.gate(p.DOC/'BINDINGS.json',dict(execute=True,research_execution_authorized=True,study='DTV-EFF0',bindings_sha256='wrong'))
    def test_exact_grid_all_tasks_and_seeds_no_fastest_selection(self):
        c=json.loads((p.DOC/'BINDINGS.json').read_text())
        self.assertEqual(len(c['jobs']),9)
        self.assertEqual({(x['task'],x['scorer_seed']) for x in c['jobs']},{(t,s) for t in ('pusht','reacher','cube') for s in (6101,6102,6103)})
        self.assertEqual(sum(j['wall_limit_seconds'] for j in c['jobs']),7200)
        self.assertLessEqual(9*c['worker_output_bytes_cap']+20000000,c['live_bytes_cap'])
        self.assertLessEqual(c['live_bytes_cap']+c['archive_bytes_cap'],c['inclusive_new_bytes_cap'])
    def test_balanced_order_each_position(self):
        for position in range(5):self.assertEqual({p.order(b)[position] for b in range(5)},set(p.ARMS))
    def test_quantiles_and_no_averaging_unlike_scopes(self):
        s=p.summary([1,2,3,4]);self.assertEqual(s['median'],2.5);self.assertAlmostEqual(s['p95'],3.85,places=12)
    def test_source_authenticated_metadata_and_no_payload_recovery(self):
        receipt=json.loads((p.DOC/'evidence/RECOVERY.json').read_text())
        self.assertFalse(receipt['checkpoint_deserialization'])
        self.assertTrue(all(not row['path'].endswith(('.pt','.h5','.ckpt')) for row in receipt['files']))
    def test_exact_input_context_role_never_later_reference_ids(self):
        c=json.loads((p.DOC/'BINDINGS.json').read_text())
        for j in c['jobs']:
            self.assertEqual(j['context_indices'],[0,1]);self.assertEqual(j['capture']['analysis_role'],'D1')
            self.assertIn('acid-alternative-v1',j['capture']['eval_manifest'])
    def test_wrong_gpu_or_missing_allocation_rejected(self):
        fake=types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda:True,device_count=lambda:1,get_device_name=lambda _: 'A6000'))
        with self.assertRaisesRegex(RuntimeError,'wrong GPU'):p.hardware(fake)
    def test_campaign_full_future_reservation_and_no_requeue(self):
        c=json.loads((p.DOC/'BINDINGS.json').read_text())
        jobs=campaign.plan(c,ROOT,p.DOC/'EXECUTION-APPROVAL.json',Path('/artificial/run'))
        self.assertEqual(sum(j['reservation_seconds'] for j in jobs),7200)
        self.assertTrue(all('--no-requeue' in j['command'] for j in jobs))
        self.assertTrue(all('--nodelist=gpu09' in j['command'] and '--mem=8G' in j['command'] for j in jobs))
    def test_report_keeps_unfavorable_cells_and_separate_boundaries(self):
        rows=[]
        for context in (0,1):
            for level in ('A','B','C'):
                for block in range(5):
                    for rep in range(2):
                        for arm in p.ARMS:
                            if level=='A' and arm=='plain':continue
                            value=12 if arm=='legacy_dtv' else 10
                            rows.append(dict(context=context,arm=arm,level=level,phase='warm',block=block,repetition=rep,gpu_event_ms=value,synchronized_wall_ms=value+1))
        report=accept.comparisons([dict(job='artificial',records=rows)])
        unfavorable=[r for r in report if r['arm']=='legacy_dtv']
        self.assertTrue(all(r['absolute_ms_saved']<0 and not r['utility_cell_pass'] for r in unfavorable))
        self.assertEqual({r['metric'] for r in report},{'gpu_event_ms','synchronized_wall_ms'})
    def test_whole_member_verification_detects_corruption(self):
        import tarfile,hashlib
        with tempfile.TemporaryDirectory(prefix='dtveff-artificial-') as name:
            root=Path(name);source=root/'input.txt';source.write_bytes(b'artificial only');archive=root/'package.tar'
            with tarfile.open(archive,'w:') as t:t.add(source,arcname='safe/input.txt')
            entries=[dict(path='safe/input.txt',bytes=source.stat().st_size,sha256=p.sha(source))]
            self.assertEqual(pack.verify_archive(archive,entries),1)
            entries[0]['sha256']='0'*64
            with self.assertRaisesRegex(RuntimeError,'identity'):pack.verify_archive(archive,entries)
    def test_archive_rejects_parent_escape(self):
        import tarfile
        with tempfile.TemporaryDirectory(prefix='dtveff-artificial-') as name:
            path=Path(name)/'bad.tar'
            with tarfile.open(path,'w:') as t:
                member=tarfile.TarInfo('../bad');member.size=1;t.addfile(member,io.BytesIO(b'x'))
            with self.assertRaisesRegex(RuntimeError,'unsafe'):pack.verify_archive(path,[dict(path='../bad',bytes=1,sha256='')])
    def test_nonfinite_timings_are_rejected(self):
        for value in (float('nan'),float('inf'),-1):
            with self.assertRaises(ValueError):p.summary([value])
    def test_exact_world_loader_rejects_newest_directory_fallback(self):
        with tempfile.TemporaryDirectory(prefix='dtveff-artificial-') as name:
            root=Path(name);checkpoint=root/'fixed_object.ckpt'
            self.assertEqual(p.world_prefix(checkpoint),str(root/'fixed'))
            (root/'fixed').mkdir()
            with self.assertRaisesRegex(RuntimeError,'collision'):p.world_prefix(checkpoint)
            with self.assertRaisesRegex(RuntimeError,'filename'):p.world_prefix(root/'other.pt')
    def test_complete_serialized_footprint_reservation(self):
        c=json.loads((p.DOC/'BINDINGS.json').read_text())
        members=pack.files();size=sum(r['bytes'] for r in members)
        self.assertLess(size,4000000)
        # Nine complete worker caps, all console logs, source and bounded
        # scheduler/analysis metadata. Tar headers/padding/PAX have 2 MB slack.
        live=9*(4000000+2000000)+size+2000000
        self.assertLessEqual(live,c['live_bytes_cap'])
        self.assertLessEqual(live+2000000,c['archive_bytes_cap'])
        self.assertLessEqual(live+c['archive_bytes_cap']+20000000,c['inclusive_new_bytes_cap'])

if __name__=='__main__':
    import resource,time
    began=time.monotonic();cpu=time.process_time()
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    print(json.dumps(dict(artificial_only=True,test_count=result.testsRun,cpu_threads=torch.get_num_threads(),test_wall_seconds=time.monotonic()-began,process_cpu_seconds=time.process_time()-cpu,process_rss_high_water_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,torch=torch.__version__,cuda_available=torch.cuda.is_available(),research_checkpoint_loaded=False)))
    raise SystemExit(0 if result.wasSuccessful() else 1)
