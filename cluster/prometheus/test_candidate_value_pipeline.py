"""Synthetic integration; no reference payloads, real model, GPU or physics."""
import io
import json
import tarfile
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import torch
import candidate_value_contract as ct
import candidate_value_learning as c
from candidate_value_data import collect,validated_banks,write_npz,load_record
from candidate_value_models import train,Predictor,normalize_fit,transform
from candidate_value_analyze import validation,closed,final_report
from candidate_value_dispatch import sbatch_arguments,launch
from candidate_value_backup import verify_archive


def synthetic_record():
    return dict(state=np.array([100.,100.,200.,200.,.5,0.,0.]),
                goal_state=np.array([400.,400.,350.,350.,1.2,0.,0.]))


def synthetic_capsule(directory,allocation):
    record=synthetic_record();rows={}
    for ref in sum(allocation.values(),[]):
        p=Path(directory)/('synthetic-reference-%d.npz'%ref)
        write_npz(p,initial_request=record['state'],states=np.tile(record['goal_state'],(151,1)))
        rows[str(ref)]=dict(file=str(p),sha256=ct.sha(p),environment_seed=0)
    return dict(records=rows)


class SyntheticBackend:
    provenance={'synthetic_only':True}
    def assert_frozen(self):pass
    def episode(self,record,h,planner_seed,environment_seed,*,bank_times=(),forced=None,
                tail_seed=None,arm='continuation',predict=None):
        x=np.zeros((64,619),np.float32);x[:,384]=np.arange(64)%2
        raw=np.tile((np.arange(64,dtype=np.float32)/64)[:,None,None],(1,15,2))
        from verify_diffusion_branch import independent_decode
        pins=ct.json_read(Path(__file__).with_name('INDEPENDENT-PINNED-INPUTS.json'))['action_decoder']
        decoded=independent_decode(raw.reshape(-1,2),pins['scale'],pins['mean']).reshape(64,15,2)
        immediate=np.arange(64,dtype=float);immediate[1]=-1
        bank=dict(x=x,raw_actions=raw,planner_actions=raw,decoded_actions=decoded,immediate=immediate,
                  continuation=np.arange(64,dtype=float),continuation_index=np.array(0),immediate_index=np.array(1))
        candidate=forced[1] if forced else (int(predict(arm,x).argmax()) if arm in ('value','linear') else (1 if arm=='immediate' else 0))
        # Original prefix reaches a physical success at step30. Controlled
        # post-bank continuation streams use even-index chunks instead. Thus
        # negative labels run to the genuine budget, never a fabricated early
        # truncation. These are geometric fixtures, not a physics simulation.
        prefix=bool(bank_times);positive=prefix or bool(candidate%2)
        n=30 if prefix else (15 if positive else 2*h)
        actions=np.tile(decoded[2],(n//15,1));actions[:15]=decoded[candidate]
        if prefix:actions[15:30]=decoded[1]
        flags=np.zeros((n,2),bool);flags[-1,0]=positive
        if n==300:flags[-1,1]=True
        states=np.tile(record['state'],(n,1))
        if positive:states[-1]=record['goal_state']
        trace=dict(actions=actions,states=states,dynamics=np.zeros((n,10),np.float64),
                   flags=flags,initial=record['state'].copy())
        return dict(trace=trace,banks={0:bank},calls=[],success=bool(flags[-1,0]),score_seconds=0.,
                    tail_state=dict(seed=tail_seed,proposal=str(tail_seed),gmm=str(tail_seed)))


def save_report(p,kind,index,payload):
    ct.json_write(p/'REPORT.json',dict(kind=kind,index=index,source_sha256='src',capsule_sha256='cap',
                                     technical_valid=True,**payload));ct.seal(p)


class PipelineTests(unittest.TestCase):
    def test_full_grid_counts(self):
        g=ct.grid()
        self.assertEqual(sum(x['seconds'] for x in g if x['gpu']),173400)
        self.assertEqual(sum(x['seconds'] for x in g if not x['gpu']),7200)
        self.assertEqual(len(g),293)
        self.assertEqual(ct.allocation(),c.allocation())
        self.assertEqual(128*2*4*8*2,16384)
        self.assertEqual(32*2*2*len(ct.ARMS),512)
    def test_paired_tail_streams(self):
        all_seeds=[]
        for r in ct.allocation()['train']+ct.allocation()['validation']:
            for h in (75,150):
                for t in c.anchors(h):
                    a,b=ct.tail_seeds(r,h,t);self.assertNotEqual(a,b);all_seeds.extend((a,b))
                    ga=torch.Generator().manual_seed(a);gb=torch.Generator().manual_seed(b)
                    self.assertFalse(torch.equal(ga.get_state(),gb.get_state()))
        self.assertEqual(len(all_seeds),len(set(all_seeds)))
    def test_preprocessing_and_context(self):
        x=np.arange(3*619,dtype=np.float32).reshape(3,619)
        mean,scale=normalize_fit(x,[.25,.5,.25]);z=transform(x,mean,scale,True)
        self.assertTrue(np.all(z[:,384:576]==0));self.assertTrue(np.all(z[:,583:613]==0))
        np.testing.assert_allclose(mean,x[1]);self.assertTrue((scale>0).all())
    def test_no_approval_no_submit(self):
        with tempfile.TemporaryDirectory() as d,patch('candidate_value_dispatch.command') as call:
            with self.assertRaises(FileNotFoundError):launch(d,d+'/run',d+'/missing',d+'/capsule','bad')
            call.assert_not_called()
    def test_caps_and_cpu_dispatch(self):
        s=ct.task('fit',0);args=sbatch_arguments(s,'src','run','approve','capsule','hash')
        self.assertIn('--partition=defq',args);self.assertFalse(any('gres' in a for a in args))
        self.assertFalse(ct.reservation(179999,0,0,0,0,ct.task('train',0)))
        self.assertFalse(ct.reservation(0,1201,0,0,0,s))
        self.assertFalse(ct.reservation(0,0,0,0,20000000000,s))
    def test_seals_authentication_and_backup(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'train-0';p.mkdir();save_report(p,'train',0,dict(example=1))
            r=ct.check_report(p,'train',0,'src','cap');self.assertEqual(r['example'],1)
            tar=root/'stage.tar'
            with tarfile.open(tar,'w') as t:t.add(p,arcname='train-0')
            request=dict(seals={'train-0':ct.sha(p/'sha256.txt')})
            verify_archive(tar,request)
            (p/'extra').write_text('synthetic corruption')
            with self.assertRaises(RuntimeError):ct.verify_seal(p)
    def test_source_authentication(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'x').write_text('source')
            (p/'SOURCE-MANIFEST.sha256').write_text(ct.sha(p/'x')+'  x\n')
            sha=ct.sha(p/'SOURCE-MANIFEST.sha256');ct.verify_source(p,sha)
            (p/'x').write_text('changed')
            with self.assertRaises(RuntimeError):ct.verify_source(p,sha)
    def test_runtime_code_scan_excludes_payloads(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'module.py').write_text('x=1')
            (p/'results.json').write_text('not inspected');(p/'reference.npz').write_bytes(b'not inspected')
            original=ct.sha;seen=[]
            def traced(path):seen.append(Path(path).name);return original(path)
            with patch.object(ct,'sha',side_effect=traced):ct.tree_hash(p,code_only=True)
            self.assertEqual(seen,['module.py'])
    def test_registry_identity_projection(self):
        from candidate_value_freeze import identity_projection
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'registry.json'
            rows=[dict(index=i,file='reference-%05d.npz'%i,sha256='a'*64,environment_seed=3,
                       namespace='synthetic',attempt=i,ignored_outcome={'nested':[True,{'quote':'x"y'}]}) for i in range(3)]
            p.write_text(json.dumps(dict(records=rows,ignored_metadata=[1,2,3])))
            projected=identity_projection(p,[1])
            self.assertEqual(set(projected),{1});self.assertEqual(len(projected[1]),6)
            self.assertNotIn('ignored_outcome',projected[1])
    def test_serial_dispatch_full_grid_without_external_execution(self):
        import time
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'source';source.mkdir()
            (source/'SOURCE-MANIFEST.sha256').write_text('synthetic')
            approval=root/'approval.json';capsule=root/'capsule.json'
            approval.write_text(json.dumps(dict(prior_allocations=[dict(job='301159',gpu=True,seconds=45,state='FAILED')])))
            capsule.write_text('{}');run=root/'new-parent'/'run'
            ct.json_write(root/'BACKUP-READY.json',dict(external_mount='/mnt/d',free_bytes=40000000000,
                          source_sha256='src',utc=time.time()))
            submitted=[];last=[0];original_write=ct.json_write
            def command(*args):
                if args[0]=='sbatch':
                    submitted.append((args[-2],int(args[-1])));last[0]+=1;return str(last[0])
                self.assertEqual(args[0],'sacct')
                return '%d|COMPLETED|0:0|1|' % last[0]
            def report(path,kind,index,source_sha,capsule_sha):
                p=Path(path);p.mkdir()
                r=dict(kind=kind,index=index,advance=True,maxrss_bytes=1,bytes_before_report=1)
                original_write(p/'REPORT.json',r);ct.seal(p);return r
            def write(path,value):
                original_write(path,value)
                if Path(path).name.startswith('BACKUP-REQUEST-'):
                    original_write(run/('BACKUP-ACK-'+value['stage']+'.json'),dict(verified=True,
                        request_sha256=ct.sha(path),archive_sha256='synthetic_archive'))
            with patch.object(ct,'authorize'),patch.object(ct,'check_report',side_effect=report),\
                 patch.object(ct,'json_write',side_effect=write),patch('candidate_value_dispatch.command',side_effect=command),\
                 patch('candidate_value_dispatch.time.sleep'):
                launch(source,run,approval,capsule,'src')
            self.assertEqual(len(submitted),293)
            self.assertEqual(submitted[:10],[('preflight',0),('preflight',1)]+[('train',i) for i in range(8)])
            self.assertLess(submitted.index(('fit',0)),submitted.index(('validation',0)))
            self.assertLess(submitted.index(('validate',0)),submitted.index(('closed',0)))
            self.assertEqual(ct.json_read(run/'DISPATCH-FINAL.json')['decision'],'completed_development_only')
            self.assertEqual(ct.json_read(run/'DISPATCH-FINAL.json')['gpu_seconds'],335)
            self.assertEqual(ct.json_read(run/'DISPATCH-FINAL.json')['cpu_wall_seconds'],3)
    def test_synthetic_collection_training_validation_closed_report(self):
        # Smaller synthetic TRAIN/validation population only for test speed. The
        # separate immutable-grid test enforces the real 96/32/32 contract.
        a=ct.allocation();a['train']=a['train'][:20];a['validation']=a['validation'][:10]
        backend=SyntheticBackend()
        with tempfile.TemporaryDirectory() as d,patch.object(ct,'allocation',return_value=a):
            root=Path(d)
            capsule=synthetic_capsule(root,a)
            for role in ('train','validation'):
                for i,ref in enumerate(a[role]):
                    for offset,h in enumerate((75,150)):
                        index=i*2+offset;p=root/('%s-%d'%(role,index));p.mkdir()
                        record,environment_seed=load_record(capsule,ref,h,role)
                        report=collect(backend,record,environment_seed,ref,h,p)
                        save_report(p,role,index,report)
            p=root/'fit-0';p.mkdir();f=train(root,p,'src','cap',capsule);self.assertTrue(f['advance'])
            save_report(p,'fit',0,f)
            predict=Predictor(root,'src','cap')
            p=root/'validate-0';p.mkdir();v=validation(root,p,'src','cap',capsule)
            self.assertTrue(v['advance']);self.assertGreater(v['mean_informative_concordance'],.5)
            save_report(p,'validate',0,v)
            for i,ref in enumerate(a['closed_loop']):
                p=root/('closed-%d'%i);p.mkdir()
                r=closed(backend,lambda h:load_record(capsule,ref,h,'closed_loop'),ref,p,predict);save_report(p,'closed',i,r)
            p=root/'report-0';p.mkdir();r=final_report(root,p,'src','cap',capsule)
            self.assertEqual(r['episodes'],512);self.assertGreater(r['primary']['mean'],0)
            # Final closed-loop analysis must independently reject a resealed
            # physically false positive too, not merely trust its saved target.
            path=root/'closed-0'/'h75-d0-immediate.npz'
            from candidate_value_data import read_npz
            tr=read_npz(path);tr['states'][-1]=synthetic_record()['state']
            with path.open('wb') as f:np.savez_compressed(f,**tr)
            (root/'closed-0'/'sha256.txt').unlink();ct.seal(root/'closed-0')
            with self.assertRaises(AssertionError):final_report(root,root/'unused','src','cap',capsule)
            # A corruption is fatal; it is never silently reclassified as failure.
            (root/'train-0'/'prefix.npz').write_bytes(b'corruption')
            with self.assertRaises(RuntimeError):list(validated_banks(root,'train','src','cap',capsule))
    def test_actual_fresh_driver_and_policy_with_fake_physics(self):
        from test_single_anchor_ranking import real_policy_class
        from test_candidate_value_learning import FakeSolver
        import pusht_fresh_initialization as fresh
        from candidate_value_runtime import RealBackend
        class Solver(FakeSolver):
            primitive_action_dim=2
            def __init__(self):super().__init__();self.diagnostic_history=[]
            def configure(self,**kw):pass
            def _propose(self,**kw):
                raw,_,_=super()._propose(**kw);raw=raw.tanh()*.1
                return raw,raw.clone(),raw.clone()
            def solve(self,*a,**kw):
                out=super().solve(*a,**kw);self.diagnostic_history.append({'synthetic':True});return out
        class Decoder:
            mean_=np.array([.01,-.02]);scale_=np.array([.2,.3])
            def inverse_transform(self,x):
                from verify_diffusion_branch import independent_decode
                return independent_decode(x,self.scale_,self.mean_)
        class Env:
            def __init__(self):
                self.unwrapped=self;self.spec=types.SimpleNamespace(id=fresh.ENV_ID);self._fresh_pending=None
                self.agent=self.block=types.SimpleNamespace(velocity=(0.,0.),angular_velocity=0.,force=(0.,0.),torque=0.)
            def queue_instantaneous_record(self,r):self._fresh_pending=r
            def _get_obs(self):return self.state.copy()
        class World:
            def __init__(self,*a,**kw):
                self.num_envs=1;self.native=Env();self.envs=types.SimpleNamespace(envs=[self.native],step=self.step)
                self.action_space=types.SimpleNamespace(shape=(1,2))
            def set_policy(self,p):p.set_env(self)
            def reset(self,**kw):
                r=self.native._fresh_pending;self.native.state=r['state'].copy();self.native.goal_state=r['goal_state'].copy()
                self.native._fresh_pending=None;self.infos=dict(state=self.native.state[None,None],
                    pixels=np.zeros((1,1,2,2,3)),goal=np.ones((1,1,2,2,3)),action=np.zeros((1,1,2),np.float32))
            def step(self,a):
                self.native.state[:2]+=a[0];self.infos['state']=self.native.state[None,None].copy()
                self.infos['action']=a[:,None].copy()
                return None,None,np.zeros(1,bool),np.zeros(1,bool),self.infos
            def close(self):pass
        Policy=real_policy_class()
        def factory(h,s):
            solver=Solver();solver.proposal_generator.manual_seed(s)
            p=Policy(solver,schedule=(15,)*(h//15),environment_budget=2*h,state_key='state',
                     process={'action':Decoder()},transform={});p._prepare_info=lambda x:x
            return p
        backend=RealBackend.__new__(RealBackend);backend.factory=factory
        record=dict(state=np.array([120.,120.,250.,250.,.5,0.,0.]),
                    goal_state=np.array([450.,450.,400.,400.,1.,0.,0.]))
        with patch.dict('sys.modules',{'stable_worldmodel':types.SimpleNamespace(World=World)}),patch.object(fresh,'register',return_value=fresh.ENV_ID):
            for h in (75,150):
                for episode in range(2):
                    r=backend.episode(record,h,55,33,bank_times=c.anchors(h))
                    self.assertEqual(len(r['trace']['actions']),2*h)
                    self.assertEqual(sorted(r['banks']),list(c.anchors(h)))


if __name__=='__main__':
    torch.set_num_threads(1);unittest.main()
