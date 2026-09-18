"""Synthetic pipeline acceptance; no frozen model or simulator construction."""
import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import torch
import lgp1_contract as c
from lgp1_tensor import affine,project,cem
from local_goal_proposals import Context,common_cem,convert_actions
from local_goal_models import LocalProposer,gmm_nll,velocity_loss,sample
from lgp1_data import aligned,statistics,select_rows
from lgp1_train import train
from lgp1_dispatch import Controller
from lgp1_runtime import Policy


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):torch.set_num_threads(1)
    def test_fp32_decoder_matches_pinned_sklearn(self):
        from sklearn.preprocessing import StandardScaler
        mean=np.array([-.007812564379916172,.006860687229453032]);std=np.array([.20846744284501714,.20674862637362224])
        scaler=StandardScaler();scaler.mean_=mean;scaler.scale_=std;scaler.n_features_in_=2
        x=np.random.default_rng(7).normal(size=(2,3,10)).astype(np.float32)
        expected=scaler.inverse_transform(x.reshape(-1,2).copy()).reshape(x.shape)
        actual=convert_actions(x,mean,std,[0,0],[1,1]);self.assertEqual(actual.dtype,np.float32)
        np.testing.assert_array_equal(actual,expected)
        np.testing.assert_array_equal(affine(torch.from_numpy(x),mean,std,[0,0],[1,1]).numpy(),expected)
        expected=scaler.transform(expected.reshape(-1,2).copy()).reshape(x.shape)
        np.testing.assert_array_equal(convert_actions(actual,[0,0],[1,1],mean,std),expected)
        p,diag=project(torch.full((1,4,3,10),100.),mean,std)
        self.assertEqual(diag['exceeded'],120);self.assertTrue((affine(p,mean,std,[0,0],[1,1]).abs()<=1).all())

    def test_numpy_tensor_common_noise_all_rounds(self):
        rng=np.random.default_rng(7);bank=rng.normal(size=(1,8,3,10)).astype(np.float32)
        noise=rng.normal(size=(29,*bank.shape)).astype(np.float32);seen=[]
        ctx=Context(np.zeros((1,3,192)),np.zeros((1,1,192)),np.zeros((1,1,192)),np.zeros((1,11)),np.array([75]),np.array([15]))
        def cost(ctx,x):seen.append(x.dtype);return (x*x).sum((2,3),dtype=np.float32)
        a,logs=common_cem(ctx,lambda *x:bank,cost,proposal_rng=None,refinement_rng=None,candidates=8,elites=3,noises=noise)
        b,other=cem(torch.from_numpy(bank),lambda x:(x*x).sum((2,3)),generator=None,
            project_fn=lambda x:(x,{}),elites=3,noises=torch.from_numpy(noise))
        self.assertEqual(seen,[np.dtype('float32')]*30)
        self.assertTrue(all(x['dtype']=='torch.float32' for x in other))
        np.testing.assert_allclose(a,b.numpy(),atol=2e-5,rtol=2e-5)
        self.assertEqual([x['elite_indices'].tolist() for x in logs],[x['elite_indices'] for x in other])

    def test_whole_trajectory_mode(self):
        class GMM:
            family='gmm'
            def __call__(self,*args):
                modes=torch.arange(8.).view(1,8,1,1).expand(1,8,3,10)*10
                return torch.zeros(1,8),modes,torch.full_like(modes,-30)
        x=sample(GMM(),(torch.zeros(1,3,192),),100,torch.Generator().manual_seed(4))
        torch.testing.assert_close(x[:,:,:,0],x[:,:,0,0,None].expand(-1,-1,3),atol=1e-9,rtol=0)

    def test_source_roles_alignment_stats(self):
        registry=[dict(episode_id=i,episode_length=175,p1_role='P1_train' if i<2 else 'P1_val') for i in range(4)]
        rows=select_rows(registry,{1},{'P1_train':2,'P1_val':1});self.assertEqual(len(rows),30)
        self.assertNotIn(1,{r['episode'] for r in rows})
        calls=[]
        def reader(e,t,keys):
            calls.append(t)
            if keys==['action']:return {'action':np.stack([np.array([v,v])/100 for v in t])}
            state=np.tile(np.arange(7.),(len(t),1))
            return dict(pixels=np.array(t)[:,None,None,None]*np.ones((len(t),3,2,2)),state=state,proprio=state[:,[0,1,5,6]])
        h,g,s,a=aligned(reader,dict(episode=0,t=10,delta=30))
        self.assertEqual(calls,[[0,5,10,40],list(range(10,25))]);np.testing.assert_allclose(a.reshape(15,2)[:,0],np.arange(10,25)/100)
        arrays=dict(lowdim=np.array([np.zeros(11),np.ones(11)*100]),actions=np.array([np.zeros((3,10)),np.ones((3,10))*100]))
        stats=statistics(arrays,np.array([True,False]));np.testing.assert_array_equal(stats['lowdim_mean'],np.zeros(11))

    def test_loss_backward_optimizer_roundtrip(self):
        inputs=(torch.zeros(2,3,192),torch.ones(2,1,192),torch.ones(2,1,192)*2,torch.zeros(2,11),torch.full((2,),75.))
        for family in c.FAMILIES:
            torch.manual_seed(1);model=LocalProposer(family,width=16,depth=1,heads=2)
            optimizer=torch.optim.AdamW(model.parameters(),lr=1e-4)
            clean=torch.zeros(2,3,10)
            loss=(gmm_nll(model(*inputs),clean) if family=='gmm' else velocity_loss(model,inputs,clean,torch.ones_like(clean),torch.tensor([0,999]))).mean()
            loss.backward();self.assertTrue(all(p.grad is None or torch.isfinite(p.grad).all() for p in model.parameters()))
            optimizer.step()
            with tempfile.TemporaryDirectory() as t:
                path=Path(t)/'synthetic.pt';torch.save(model.state_dict(),path)
                other=LocalProposer(family,width=16,depth=1,heads=2);other.load_state_dict(torch.load(path,weights_only=True))
                a=sample(model,inputs,3,torch.Generator().manual_seed(2));b=sample(other,inputs,3,torch.Generator().manual_seed(2))
                torch.testing.assert_close(a,b,rtol=0,atol=0)

    def test_real_data_loop_artificial_cache(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);cache=root/'cache';cache.mkdir()
            n=20;rows=[dict(role='P1_train' if i<16 else 'P1_val',episode=i,t=10,delta=15) for i in range(n)]
            c.write(cache/'ROWS.json',rows)
            arrays={k:np.zeros(shape,np.float32) for k,shape in dict(history=(n,3,192),local=(n,1,192),far=(n,1,192),lowdim=(n,11),actions=(n,3,10),remaining=(n,)).items()}
            arrays['remaining'][:]=15
            for k,v in arrays.items():np.save(cache/(k+'.npy'),v)
            np.savez(cache/'normalization.npz',**statistics(arrays,np.arange(n)<16));c.seal(cache)
            for family in c.FAMILIES:
                out=root/family;out.mkdir()
                result=train(cache,out,family,8301,lambda:None,updates=2,width=16,depth=1,heads=2,device='cpu',synthetic=True)
                self.assertEqual(result['updates'],2);self.assertEqual(result['row_presentations'],256)
                self.assertEqual(result['validation']['rows'],4)
            out=root/'interrupted';out.mkdir()
            def stop():raise TimeoutError('synthetic pre-update interruption')
            with self.assertRaises(TimeoutError):
                train(cache,out,'gmm',8301,stop,updates=2,width=16,depth=1,heads=2,device='cpu',synthetic=True)
            saved=torch.load(out/'interrupted.pt',weights_only=True)
            self.assertEqual(saved['completed_updates'],0);self.assertFalse(saved['resume_authorized'])

    def test_full_grid_and_failure_state_machine(self):
        specs=c.grid(list(range(32)));self.assertEqual(len(specs),204)
        self.assertEqual(sum(s['gpu'] for s in specs),203)
        class Scheduler:
            def __init__(self,fail=None,ambiguous=False):self.n=0;self.fail=fail;self.ambiguous=ambiguous
            def submit(self,s):
                self.n+=1
                if self.ambiguous:raise TimeoutError('Unknown sbatch response')
                return str(self.n)
            def wait(self,j,s):return dict(seconds=7,state='FAILED' if int(j)==self.fail else 'COMPLETED',exit_code='1:0' if int(j)==self.fail else '0:0')
        events=[];stages=[];sch=Scheduler()
        ctl=Controller(specs,sch,events.append,lambda:0,lambda s:None,lambda stage,done:stages.append((stage,len(done))))
        result=ctl.run();self.assertEqual(result['jobs'],204);self.assertEqual(stages,[('models',7),('evaluation',203)])
        with self.assertRaises(RuntimeError):ctl.run()
        for sch in (Scheduler(fail=2),Scheduler(ambiguous=True)):
            events=[];ctl=Controller(specs,sch,events.append,lambda:0,lambda s:None,lambda *a:None)
            with self.assertRaises(RuntimeError):ctl.run()
            self.assertLessEqual(sch.n,2)
            if sch.fail:self.assertEqual(ctl.gpu,14)
            else:self.assertEqual(events[-1]['reserved_seconds'],14400)
        sch=Scheduler();ctl=Controller(specs,sch,lambda x:None,lambda:12_000_000_001,lambda s:None,lambda *a:None)
        with self.assertRaises(RuntimeError):ctl.run()
        self.assertEqual(sch.n,0)

    def test_preservation_aggregate_and_guards(self):
        from lgp1_preserve import verify_archive
        from lgp1_aggregate import summarize
        import tarfile
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'a').write_bytes(b'synthetic')
            with tarfile.open(root/'a.tar','w') as f:f.add(root/'a',arcname='run/a')
            expected={'run/a':dict(bytes=9,sha256=c.sha(root/'a'))}
            self.assertEqual(verify_archive(root/'a.tar',expected)['files'],1)
            expected['run/a']['sha256']='0'*64
            with self.assertRaises(RuntimeError):verify_archive(root/'a.tar',expected)
            source=root/'source';run=root/'run';source.mkdir();run.mkdir()
            self.assertEqual(c.storage(source,run)['worker_bytes'],0)
            (run/'log').write_bytes(b'xx')
            with patch.dict(c.CAPS,control_bytes=1):
                with self.assertRaises(RuntimeError):c.storage(source,run)
        rows=[dict(reference=r,horizon=h,family=f,seed=s,success=int(f=='diffusion'))
              for r in range(32) for h in (75,150) for f in c.FAMILIES for s in c.SEEDS]
        result=summarize(rows);self.assertEqual(result['primary'],1);self.assertEqual(len(result['source_effects']),32)
        with self.assertRaises(RuntimeError):summarize(rows[:-1])

    def test_unresolved_job_and_disabled_approval(self):
        class Scheduler:
            def submit(self,s):return '123'
            def wait(self,j,s):raise OSError('lost connection, not proof of job failure')
        events=[];ctl=Controller(c.grid(list(range(32))),Scheduler(),events.append,lambda:0,lambda s:None,lambda *a:None)
        with self.assertRaises(OSError):ctl.run()
        self.assertEqual(events[-1]['event'],'unresolved_live_or_terminal')
        self.assertEqual(events[-1]['reserved_seconds'],14400)
        with self.assertRaises(RuntimeError):ctl.run()
        with patch('lgp1_contract.verify'),patch('lgp1_contract.read',return_value={'execution_authorized':False}):
            with self.assertRaisesRegex(RuntimeError,'Disabled'):c.authorize(Path('.'),Path('none'))

    def test_saved_episode_action_verifier(self):
        from lgp1_verify import episodes
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);spec=dict(reference=0,family='gmm',seed=8301)
            rows=[dict(**spec,horizon=h,steps=1,success=1,failure=None,
                stages=[dict(elapsed=0,rounds=[dict(candidates=300) for _ in range(30)])]) for h in (75,150)]
            c.write(root/'REPORT.json',{'rows':rows})
            for h in (75,150):np.savez(root/f'actions-h{h}.npz',actions=np.zeros((1,2),np.float32))
            self.assertEqual(len(episodes(root,spec)),2)
            np.savez(root/'actions-h75.npz',actions=np.ones((1,2),np.float32)*2)
            with self.assertRaisesRegex(RuntimeError,'Delivered'):episodes(root,spec)

    def test_policy_history_context_lifecycle(self):
        class Backend:
            mean=np.zeros(2);std=np.ones(2)
            def __init__(self):self.frames=[];self.targets=[]
            def encode_frames(self,frames):self.frames.append(frames.copy());return np.zeros((len(frames),192),np.float32)
            def generate(self,h,f,s,r):self.targets.append(int(r[0]));return np.ones_like(f)
            def cost_function(self,frames,local):return lambda bank:(bank*bank).sum((2,3))
        backend=Backend();model=LocalProposer('gmm',width=16,depth=1,heads=2)
        stats=dict(lowdim_mean=np.zeros(11),lowdim_std=np.ones(11),action_mean=np.zeros(2),action_std=np.ones(2))
        def fake_cem(bank,cost,**kw):return torch.zeros(1,3,10),[dict(round=i) for i in range(30)]
        with patch('lgp1_runtime.sample',return_value=torch.zeros(1,300,3,10)),patch('lgp1_runtime.cem',side_effect=fake_cem):
            p=Policy(backend,model,stats,75,8301,0);p.set_env(object())
            for i in range(150):
                info=dict(pixels=np.full((1,1,2,2,3),i),goal=np.zeros((1,1,2,2,3)),state=np.zeros((1,1,7)))
                self.assertEqual(p.get_action(info).dtype,np.float32)
            self.assertEqual([s['remaining'] for s in p.diagnostic_history],[75,60,45,30,15]*2)
            self.assertEqual([s['physical_remaining'] for s in p.diagnostic_history],list(range(150,0,-15)))
            np.testing.assert_array_equal(backend.frames[0],np.zeros((3,2,2,3)))
            np.testing.assert_array_equal(backend.frames[2][:,0,0,0],[5,10,15])
            self.assertEqual(backend.targets,[75,60,45,30]*2)
            with self.assertRaises(RuntimeError):p.get_action(info)
            p.finish();self.assertFalse(p.history)
            other=Policy(backend,model,stats,75,8301,0)
            self.assertFalse(other.history);self.assertIsNot(p._action_buffer,other._action_buffer)
            with self.assertRaises(RuntimeError):p.set_env(object())

    def test_fresh_driver_native_termination_and_slot_ownership(self):
        from e18_fresh_driver import FreshEpisode,complete_slots
        from pusht_fresh_initialization import ENV_ID
        class World:
            num_envs=1
            def __init__(self,limit):
                self.limit=limit;self.steps=0
                self.native=SimpleNamespace(spec=SimpleNamespace(id=ENV_ID),queue_instantaneous_record=lambda r:None,
                    _fresh_pending=None,_get_obs=lambda:self.infos['state'][0,-1])
                self.envs=SimpleNamespace(envs=[SimpleNamespace(unwrapped=self.native)],step=self.step)
            def set_policy(self,p):p.set_env(self)
            def reset(self,record):
                self.steps=0;self.native.goal_state=record['goal_state'].copy()
                self.infos=dict(pixels=np.zeros((1,1,2,2,3)),goal=np.zeros((1,1,2,2,3)),state=record['state'][None,None].copy())
            def step(self,action):
                self.steps+=1;self.infos['action']=action[:,None].copy()
                return None,None,np.array([self.steps==self.limit]),np.array([False]),self.infos
        class P:
            def __init__(self):self.planner=SimpleNamespace(diagnostic_history=[]);self._action_buffer=[];self._stage_index=0;self.calls=0
            def set_env(self,e):self.env=e
            def get_action(self,i):self.calls+=1;return np.zeros((1,2),np.float32)
        record=dict(state=np.zeros(7),goal_state=np.zeros(7))
        worlds=[World(1),World(3),World(999)]
        with patch('e18_fresh_driver.reset_world',side_effect=lambda w,records,seed:w.reset(records[0])):
            episodes=[FreshEpisode(w,lambda h,s:P()) for w in worlds]
            for e in episodes:e.start(record,horizon=75,budget=150,seed=1)
            complete_slots(episodes)
            self.assertEqual([e.steps for e in episodes],[1,3,150])
            for e in episodes:
                with self.assertRaises(RuntimeError):e.advance()
                old=e.policy;e.start(record,horizon=75,budget=1,seed=1)
                self.assertIsNot(old,e.policy);self.assertIsNot(old.planner,e.policy.planner)
                e.advance();self.assertEqual(e.policy.calls,1)

if __name__=='__main__':unittest.main()
