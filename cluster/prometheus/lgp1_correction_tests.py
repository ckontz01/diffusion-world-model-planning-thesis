"""Three narrow findings: pinned-source contracts and artificial endpoint data."""
import ast,copy,hashlib,json,tempfile,unittest,subprocess,sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import torch
import torch.nn.functional as F
import lgp1_contract as c
from lgp1_runtime import FrozenBackend
from lgp1_endpoint import physical,identity,verify_file

def contracts():
    result=c.read(Path(__file__).resolve().parents[2]/c.DOC/'PINNED-CONTRACTS-CORRECTION.json')
    for value in result['sources'].values():
        c.require(hashlib.sha256(value['text'].encode()).hexdigest()==value['sha256'],'Pinned fixture source hash')
    return result


class HostControllerImportTests(unittest.TestCase):
    def test_dispatch_and_sealed_task_without_site_packages(self):
        # A separate isolated interpreter cannot inherit NumPy from this suite.
        code = '''import sys, tempfile
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import lgp1_dispatch as d
import lgp1_verify as v
import lgp1_contract as c
assert 'numpy' not in sys.modules
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp)
    spec=dict(name='cache',kind='cache',gpu=True,seconds=14400)
    c.write(root/'TECHNICAL.json',dict(task=spec,complete=True,gpu_used=True))
    c.seal(root)
    assert d.verify_task(root,spec)['complete'] is True
assert 'numpy' not in sys.modules
try:
    v.cache('/nonexistent-synthetic-cache')
except ModuleNotFoundError as e:
    assert e.name == 'numpy'
else:
    raise AssertionError('Cache verifier must still require NumPy')
'''
        result=subprocess.run([sys.executable,'-I','-S','-B','-c',code,str(Path(__file__).resolve().parent)],
                              capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

def method(suffix,cls,name):
    source=next(v['text'] for k,v in contracts()['sources'].items() if k.endswith(suffix))
    node=next(n for n in ast.parse(source).body if isinstance(n,ast.ClassDef) and n.name==cls)
    fn=next(n for n in node.body if isinstance(n,ast.FunctionDef) and n.name==name)
    ns=dict(torch=torch,F=F,np=np)
    exec(compile(ast.Module(body=[fn],type_ignores=[]),'authenticated-pinned-source','exec'),ns)
    return ns[name]

def fixture(h=75,n=None,success=False):
    n=2*h if n is None else n
    initial=np.zeros(7,np.float64);initial[0]=100;goal=np.zeros(7,np.float64)
    states=np.tile(initial,(n,1));flags=np.zeros((n,2),bool)
    if success:states[-1]=goal;flags[-1,0]=True
    if n==300:flags[-1,1]=True
    steps=np.arange(1,n+1,dtype=np.int64)
    evidence=dict(requested_initial=initial,initialized_state=initial.copy(),goal_state=goal,post_states=states,
        actions=np.zeros((n,2),np.float32),flags=flags,absolute_steps=steps,physical_remaining=2*h-steps,action_stage=(steps-1)//15)
    row=dict(reference=0,family='gmm',seed=8301,horizon=h,steps=n,success=int(success),failure=None,
        terminated=bool(flags[-1,0]),truncated=bool(flags[-1,1]),stages=[dict(stage=i,elapsed=t,remaining=h-t%h,
        physical_remaining=2*h-t,final_goal=h-t%h==15,rounds=[dict(candidates=300) for _ in range(30)])
        for i,t in enumerate(range(0,n,15))])
    return evidence,row

class CorrectionTests(unittest.TestCase):
    def test_wrapper_uses_pinned_get_cost_and_criterion(self):
        criterion=method('/wm/lewm/lewm.py','LeWM','criterion')
        get_cost=method('/wm/lewm/lewm.py','LeWM','get_cost')
        class SyntheticLeWM:
            def encode(self,info):return {'emb':torch.zeros(1,1,192)}
            def rollout(self,info,bank):
                self.supplied_goal=info['goal_emb'].clone()
                info['predicted_emb']=torch.arange(bank.shape[1],dtype=torch.float32)[None,:,None,None].expand(1,-1,3,192)
                return info
        SyntheticLeWM.criterion=criterion;SyntheticLeWM.get_cost=get_cost
        backend=FrozenBackend.__new__(FrozenBackend);backend.device=torch.device('cpu');backend.lewm=SyntheticLeWM()
        backend.pixels=lambda x:torch.zeros(1,1,3,2,2)
        goal=np.full((1,1,192),2,np.float32)
        result=backend.cost_function(np.zeros((3,2,2,3)),goal)(torch.zeros(1,7,3,10))
        self.assertEqual(tuple(backend.lewm.supplied_goal.shape),(1,1,192))
        torch.testing.assert_close(result,192*(torch.arange(7.)[None]-2)**2,rtol=0,atol=0)
        with self.assertRaises(RuntimeError):
            criterion(None,dict(predicted_emb=torch.zeros(1,7,3,192),goal_emb=torch.zeros(1,1,1,192)))

    def test_pinned_scaler_both_directions_and_old_regression(self):
        from local_goal_proposals import convert_actions
        from lgp1_tensor import affine,project
        f=contracts()['fixture'];x=np.array(f['x'],np.float32).reshape(-1,3,10)
        mean=np.array(f['mean'],np.float64);std=np.array(f['scale'],np.float64)
        for sm,ss,tm,ts,key in [(mean,std,[0,0],[1,1],'inverse'),([0,0],[1,1],mean,std,'forward')]:
            expected=np.array(f[key],np.float32).reshape(x.shape)
            np.testing.assert_array_equal(convert_actions(x,sm,ss,tm,ts),expected)
            np.testing.assert_array_equal(affine(torch.from_numpy(x),sm,ss,tm,ts).numpy(),expected)
        wrong=x.reshape(-1,2).copy();wrong*=std;wrong+=mean
        self.assertFalse(np.array_equal(wrong,np.array(f['inverse'],np.float32)))
        # The exact e7188b75 fixture, without importing its historical pipeline.
        y=np.arange(2000,dtype=np.float32).reshape(-1,2)/37
        expected=y*std.astype(np.float32)+mean.astype(np.float32)
        padded=np.pad(y.ravel(),(0,10)).reshape(-1,3,10)
        got=convert_actions(padded,mean,std,[0,0],[1,1]).reshape(-1,2)[:len(y)]
        np.testing.assert_array_equal(expected,got)
        wrong=y.copy();wrong*=std;wrong+=mean
        self.assertFalse(np.array_equal(expected,wrong))
        raw=torch.linspace(-1.000001,1.000001,300).reshape(1,10,3,10)
        encoded=affine(raw,[0,0],[1,1],mean,std)
        projected,diag=project(encoded,mean,std)
        decoded=affine(projected,mean,std,[0,0],[1,1])
        self.assertTrue((abs(decoded)<=1).all());self.assertEqual(decoded.dtype,torch.float32)
        np.testing.assert_array_equal(decoded.numpy(),convert_actions(projected.numpy(),mean,std,[0,0],[1,1]))

    def test_valid_first_chunk_and_final_budget_success(self):
        for h,n in [(75,1),(75,14),(75,150),(150,300)]:
            evidence,row=fixture(h,n,True);self.assertEqual(physical(evidence,row)['success'],1)
        for h in (75,150):
            evidence,row=fixture(h);self.assertEqual(physical(evidence,row)['success'],0)

    def test_reject_one_step_nonterminal_failure(self):
        e,r=fixture(n=1)
        with self.assertRaisesRegex(RuntimeError,'early nonterminal'):physical(e,r)

    def test_reject_success_label_inconsistent_with_states(self):
        e,r=fixture();r['success']=1
        with self.assertRaisesRegex(RuntimeError,'Reported success'):physical(e,r)

    def test_reject_missing_mislabeled_terminal_and_post_terminal(self):
        e,r=fixture(n=1,success=True);e['flags'][0,0]=False
        with self.assertRaisesRegex(RuntimeError,'terminal flag'):physical(e,r)
        e,r=fixture();del e['flags']
        with self.assertRaisesRegex(RuntimeError,'Missing'):physical(e,r)
        e,r=fixture();e['flags'][-1,0]=True
        with self.assertRaisesRegex(RuntimeError,'terminal flag'):physical(e,r)
        e,r=fixture();e['flags'][0,0]=True
        with self.assertRaisesRegex(RuntimeError,'Post-terminal'):physical(e,r)
        e,r=fixture();e['flags'][-1,1]=True
        with self.assertRaisesRegex(RuntimeError,'truncation'):physical(e,r)
        e,r=fixture(150);e['flags'][-1,1]=False
        with self.assertRaisesRegex(RuntimeError,'truncation'):physical(e,r)

    def test_predicate_domain_same_step_t0_and_schedule(self):
        native=method('/envs/pusht/env.py','PushT','eval_state')
        e,r=fixture();e['requested_initial'][:]=0;e['initialized_state'][:]=0
        self.assertEqual(physical(e,r)['success'],0)  # initial t0 not counted
        probes=np.array([[15,0,15,0,0,0,0],[0,0,0,0,1,0,0],[40,0,0,0,0,0,0],
                         [0,0,0,0,2*np.pi-.01,0,0],[20,0,0,0,0,0,0],[0,0,0,0,np.pi/9,0,0]],np.float64)
        for p in probes:
            wanted=bool(native(None,np.zeros(7),p)[0])
            x,row=fixture();x['post_states'][-1]=p;x['flags'][-1,0]=wanted;row.update(success=int(wanted),terminated=wanted)
            self.assertEqual(bool(physical(x,row)['success']),wanted)
        e,r=fixture();e['post_states'][-1,4]=np.nextafter(2*np.pi,np.inf)
        with self.assertRaisesRegex(RuntimeError,'angle domain'):physical(e,r)
        e,r=fixture();r['stages'][5]['physical_remaining']=150
        with self.assertRaisesRegex(RuntimeError,'schedule'):physical(e,r)

    def test_authenticated_file_evidence_and_small_storage(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);e,r=fixture(150,300,True)
            recorded=np.zeros((151,7));refpath=root/'synthetic-reference.npz'
            np.savez(refpath,initial_request=e['requested_initial'],states=recorded)
            ref=dict(file=str(refpath),sha256=c.sha(refpath));r['endpoint_identity']=identity(ref,e['requested_initial'],e['goal_state'],150)
            np.savez_compressed(root/'endpoint-h150.npz',**e)
            self.assertEqual(verify_file(root,r,ref)['actions'],300)
            self.assertLess((root/'endpoint-h150.npz').stat().st_size,50000)
            r['endpoint_identity']['goal_index']=75
            with self.assertRaisesRegex(RuntimeError,'identity'):verify_file(root,r,ref)

    def test_exact_observation_endpoint_without_byte_or_flag_changes(self):
        end=np.float64(2*np.pi)
        self.assertEqual(float(end).hex(),'0x1.921fb54442d18p+2')
        for angle in (0.,np.nextafter(end,-np.inf),end):
            e,r=fixture(n=1,success=True);e['post_states'][0,4]=angle
            before={k:v.tobytes() for k,v in e.items()}
            self.assertEqual(physical(e,r)['success'],1)
            self.assertEqual(before,{k:v.tobytes() for k,v in e.items()})
        e,r=fixture();e['requested_initial'][4]=np.nextafter(end,-np.inf);e['initialized_state'][4]=end
        physical(e,r)  # existing reset comparison retained, native endpoint admitted
        for angle in (np.nextafter(0.,-np.inf),np.nextafter(end,np.inf),np.nan,np.inf,-np.inf):
            for name in ('post_states','initialized_state'):
                e,r=fixture()
                if name=='post_states':e[name][-1,4]=angle
                else:e[name][4]=angle
                with self.assertRaises(RuntimeError):physical(e,r)
        for name in ('goal_state','requested_initial'):
            for angle in (end,np.nextafter(end,np.inf),-1.,np.nan,np.inf):
                e,r=fixture();e[name][4]=angle
                with self.assertRaises(RuntimeError):physical(e,r)

if __name__=='__main__':unittest.main()
