import common as c
import copy
import tempfile
import unittest
from unittest import mock as patching
from pathlib import Path
import numpy as np
from bridge import LeWMBridge,delivered,load_backend
from artificial import FakeLeWM,FakeTorch,factory,d192_fixture
from episodes import collect,evaluate,save
from verify import verify_arrays,load_verify,dataset_rows
from dispatch import execute
from model import JointModel,OrdinaryModel,Preprocessing
from policy import Selector

SMALL={'population':4,'elites':2,'rounds':1}  # Interface tests only; never real settings.


def backend():return LeWMBridge(FakeLeWM(),FakeTorch,'artificial-cpu')


class Bindings(unittest.TestCase):
    def test_mocked_actual_loader_order(self):
        import bridge
        import types
        calls=[]
        class Loaded:
            def to(self,value):calls.append(('to',value));return self
            def eval(self):calls.append('eval');return self
            def requires_grad_(self,value):self.requires_grad=value;return self
            def state_dict(self):return {}
        capability=object.__new__(c.Authorization)
        capability.inputs={'model_sources':{'lewm':'artificial/lewm.py','module':'artificial/module.py'}}
        torch=types.SimpleNamespace(manual_seed=lambda x:None,cuda=types.SimpleNamespace(manual_seed_all=lambda x:None),
            use_deterministic_algorithms=lambda x:None,bfloat16='bfloat16',
            backends=types.SimpleNamespace(cudnn=types.SimpleNamespace(),cuda=types.SimpleNamespace(matmul=types.SimpleNamespace())))
        def cost(path):calls.append(('checkpoint-loader',path));return Loaded()
        with patching.patch.object(c.Authorization,'runtime',lambda _:calls.append('runtime-auth')), \
             patching.patch.object(c.Authorization,'checkpoint',lambda _:calls.append('checkpoint-hash') or '/artificial/test_object.ckpt'), \
             patching.patch.dict('sys.modules',{'torch':torch,'stable_worldmodel':types.SimpleNamespace(policy=types.SimpleNamespace(AutoCostModel=cost))}), \
             patching.patch.object(bridge,'load_module',lambda name,path:types.SimpleNamespace(LeWM=Loaded,Predictor=Loaded)):
            loaded=bridge.load_backend(capability)
        self.assertEqual(calls[:3],['runtime-auth','checkpoint-hash',('checkpoint-loader','/artificial/test')])
        self.assertFalse(loaded.model.requires_grad)

    def test_image_tensor_dtype_layout(self):
        b=backend();image=np.full((224,224,3),255,np.uint8)
        z=b.encode(image,current=True);self.assertEqual(z.shape,(192,))
        out=b.rollout(z,np.zeros((7,3,10)));self.assertEqual(out.shape,(7,4,192))
        np.testing.assert_array_equal(out[:,0],np.broadcast_to(z,(7,192)))
        with self.assertRaises(AssertionError):b.rollout(z+1,np.zeros((7,3,10)))
        x=b.pixels(image);self.assertEqual(x.dtype,'bfloat16')
        expected=(1-np.array([.485,.456,.406]))/np.array([.229,.224,.225])
        np.testing.assert_allclose(x.a[0,0,:,0,0],expected,atol=.008,rtol=0)
        for value in ([1.1,0],[float('nan'),0]):
            with self.assertRaises(ValueError):delivered(value)

    def test_native_bridge_terminal_budget_t0_closure(self):
        for terminal in (3,8,None):
            b=backend();owned=[];make=factory(b,terminal,owned=owned)
            a,m=collect(make,b.rollout,490,'fit',settings=SMALL)
            result=verify_arrays(a,m)
            self.assertTrue(result['passed']);self.assertTrue(all(w.closed for w in owned))
            if terminal==3:
                self.assertEqual(len(m['branches']),len(a['tree/count']))
                self.assertTrue(all(r['suffix'] is None for r in m['branches']))
                self.assertTrue(all(len(r['a'])==0 for r in dataset_rows(a,m)))
            elif terminal==8:self.assertTrue(all(r['steps']==8 for r in m['branches']))
            else:self.assertTrue(all(r['steps']==150 and not r['success'] for r in m['branches']))
        b=backend();a,m=evaluate(factory(b,t0=True),b.rollout,931,'vanilla',None,settings=SMALL)
        self.assertEqual(verify_arrays(a,m)['successes'],[0]);self.assertEqual(m['branches'][0]['steps'],150)

    def test_saved_independent_corruption_and_roles(self):
        b=backend();a,m=collect(factory(b),b.rollout,490,'fit',settings=SMALL)
        with tempfile.TemporaryDirectory() as tmp:
            save(Path(tmp),a,m);_,_,v=load_verify(Path(tmp));self.assertTrue(v['physical_replay_checked'])
        for key,index in [('b0/action',(0,0)),('b0/state',(0,0)),('b1/dynamics',(0,0)),('b0/remaining',0),('tree/baseline',(0,0))]:
            wrong={k:v.copy() for k,v in a.items()};wrong[key][index]+=1
            with self.assertRaises((AssertionError,ValueError)):verify_arrays(wrong,m)
        wrong=copy.deepcopy(m);wrong['branches'][0]['suffix']=4
        with self.assertRaises((AssertionError,ValueError)):verify_arrays(a,wrong)
        wrong=copy.deepcopy(m);wrong['role']='final_development'
        with self.assertRaises(ValueError):verify_arrays(a,wrong)

    def test_eight_actual_observation_paths(self):
        fit=d192_fixture('fit',c.roles()['fit']);pre=Preprocessing.fit(fit)
        j=JointModel(996,212,192,preprocessing=pre);o=OrdinaryModel(996,212,192,preprocessing=pre)
        from bayes import BayesianRegression
        bayes=BayesianRegression(o).fit(fit);selector=Selector(j,o,bayes)
        results=[]
        for mode in c.CONTROLS:
            b=backend();a,m=evaluate(factory(b,success_at=18),b.rollout,931,mode,selector,settings=SMALL)
            self.assertTrue(verify_arrays(a,m)['passed']);results.append(m['branches'][0])
        self.assertTrue(all(r['steps']==18 for r in results))
        for mode in ('ordinary','bayesian','active','no_update'):
            row=results[c.CONTROLS.index(mode)];self.assertEqual(row['ledger']['integration_responses'],512)
        # Selector.after receives the observation from that very world's fifth
        # action, not a shared future trajectory. Spy across ordinary/active.
        seen=[];old=selector.after
        def spy(decision,tree,h,observed,ledger):seen.append(observed.copy());return old(decision,tree,h,observed,ledger)
        selector.after=spy
        for mode in ('ordinary','active'):
            b=backend();a,m=evaluate(factory(b,success_at=8),b.rollout,931,mode,selector,settings=SMALL)
            np.testing.assert_array_equal(seen[-1],a['b0/latent'][4])

    def test_auth_before_import_or_payload(self):
        with self.assertRaises(ValueError):load_backend(object())
        with tempfile.TemporaryDirectory() as tmp:
            a={'schema':'ACV0-execution-v1','authorized':False,'instruction':'', 'package_sha256':'missing',
               'grid_sha256':'missing','roles_sha256':'missing','inputs_sha256':'missing','run':'missing','no_retry':True,'research_caps':c.caps()}
            c.write(Path(tmp)/'approval.json',a)
            with self.assertRaises(PermissionError):c.Authorization(Path(tmp)/'approval.json','missing')

    def test_physical_replay_fault_preserved_and_closed(self):
        b=backend();owned=[];base=factory(b,owned=owned);calls=[];partials=[]
        def broken():
            env=base();calls.append(env)
            if len(calls)==2:
                original=env.step
                def fail(action):
                    if env.clock==2:raise RuntimeError('artificial native step fault')
                    return original(action)
                env.step=fail
            return env
        with self.assertRaises(RuntimeError):collect(broken,b.rollout,490,'fit',settings=SMALL,preserve=lambda a,m:partials.append((a,m)))
        self.assertTrue(all(w.closed for w in owned));self.assertEqual(len(partials),1)
        self.assertFalse(partials[0][1]['complete']);self.assertEqual(len(partials[0][0]['failed_branch/state']),2)
        self.assertEqual(len(partials[0][1]['completed_branches']),1)

    def test_same_samples_distinct_actual_future_inputs(self):
        from fitting import load_models
        models=load_models(c.ROOT/'completion-tests-v1');selector=Selector(*models)
        b=backend();a,m=collect(factory(b,success_at=8),b.rollout,490,'fit',settings=SMALL)
        from tree import Node,Tree,Ledger
        from policy import context
        nodes=tuple(Node(a['tree/prefix'][p],tuple(a['tree/suffix'][p,:n]),a['tree/predicted_prefix'][p],
                         tuple(a['tree/predicted_terminal'][p,:n]),tuple('stored' for _ in range(n))) for p,n in enumerate(a['tree/count']))
        tree=Tree(nodes,a['tree/baseline'],0);h=context([a['b0/initial_latent']],[],a['goal_latent'],0)
        samples={};original=selector.conditional
        def spy(x,aa,r,mode,ledger=None):
            samples.setdefault(mode,[]).append(r.copy());return original(x,aa,r,mode,ledger)
        selector.conditional=spy
        for mode in ('active','ordinary','bayesian','no_update'):selector.select(tree,h,Ledger(),mode)
        for mode in ('ordinary','bayesian','no_update'):
            for x,y in zip(samples['active'],samples[mode]):np.testing.assert_array_equal(x,y)
        # Artificial step-dependent images ensure later observations actually
        # differ; the execution path must pass EACH own fifth observation.
        seen=[];old=selector.after
        def after(decision,tree,h,z,ledger):seen.append(z.copy());return old(decision,tree,h,z,ledger)
        selector.after=after
        for offset,mode in [(2,'ordinary'),(9,'active')]:
            bb=backend();base=factory(bb,success_at=8)
            def distinct(base=base,offset=offset):
                env=base();info=env.world.info
                def changed(action):
                    info(action)
                    if env.world.clock>0:env.world.infos['pixels']=(env.world.infos['pixels']+offset).astype(np.uint8)
                env.world.info=changed
                return env
            aa,mm=evaluate(distinct,bb.rollout,931,mode,selector,settings=SMALL)
            np.testing.assert_array_equal(seen[-1],aa['b0/latent'][4]);verify_arrays(aa,mm)
        self.assertFalse(np.array_equal(seen[0],seen[1]))

    def test_model_seal_and_existing_receipts(self):
        from fitting import load_models,assert_roles
        root=c.ROOT/'completion-tests-v1'
        for kind in ('joint','ordinary'):
            r=c.read(root/('fit-'+kind)/'FIT.json');self.assertEqual(r['updates'],192)
            self.assertEqual([x['update'] for x in r['trace']],list(range(1,193)))
        loaded=load_models(root);self.assertEqual([m.parameter_count for m in loaded[:2]],[90795,106177])
        for role in ('fit','validation'):
            with np.load(root/(role+'-artificial-dataset.npz'),allow_pickle=False) as z:d={k:z[k] for k in z.files}
            assert_roles(d,c.roles()[role],role)
        for mode in c.CONTROLS:load_verify(root/('evaluate-'+mode))

    def test_archive_members_and_exclusive_writes(self):
        import tarfile
        from preserve import verify_tar,VOLUME
        self.assertEqual(VOLUME,'\\\\?\\Volume{0a2f1ba9-0000-0000-0000-100000000000}\\')
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);c.write(p/'data.json',{'artificial':True})
            with self.assertRaises(FileExistsError):c.write(p/'data.json',{})
            members={'run/data.json':{'bytes':(p/'data.json').stat().st_size,'sha256':c.sha(p/'data.json')}}
            with tarfile.open(p/'example.tar','w') as t:t.add(p/'data.json',arcname='run/data.json')
            verify_tar(p/'example.tar',members)
            members['run/data.json']['sha256']='0'*64
            with self.assertRaises(ValueError):verify_tar(p/'example.tar',members)

    def test_full_independent_aggregation_and_footprint(self):
        import analysis
        from fitting import load_models
        from supervise import LOG_CAP
        root=c.ROOT/'completion-tests-v1';models=load_models(root)
        with np.load(root/'footprint-collection/evidence.npz',allow_pickle=False) as z:collection={k:z[k] for k in z.files}
        cm=c.read(root/'footprint-collection/EVIDENCE.json')
        fixtures={mode:load_verify(root/('evaluate-'+mode)) for mode in c.CONTROLS}
        jobs=c.grid();records=[{'spec':j,'seconds':j['seconds'],'job':str(600000+i),'state':'COMPLETED','exit_code':'0:0'} for i,j in enumerate(jobs[:-1])]
        def fixture(path,**kwargs):
            key=Path(path).name;j=next(j for j in jobs if j['key']==key)
            if j['stage']=='collection':a=collection;m=copy.deepcopy(cm);m['reference']=j['reference'];m['role']=j['role']
            else:a,m,_=fixtures[j['control']];m=copy.deepcopy(m);m['reference']=j['reference']
            return a,m,verify_arrays(a,m)
        def read(path):
            if Path(path).name=='PRE-ANALYSIS-ACCOUNTING.json':return {'jobs':records}
            if Path(path).name=='TECHNICAL.json':return {'passed':True,'maximum_metadata_reserve':'x'*65536}
            raise AssertionError('Unexpected analysis read: '+str(path))
        with patching.patch.object(analysis,'load_verify',fixture),patching.patch.object(c,'verify_seal',lambda *x:None), \
             patching.patch.object(c,'read',read),patching.patch.object(c,'grid',lambda:jobs), \
             patching.patch.object(c,'roles',lambda:role_map),patching.patch('fitting.load_models',lambda *x:models):
            result=analysis.aggregate(root)
        self.assertEqual(np.array(result['binary_outcomes_by_source']).shape,(32,8))
        self.assertEqual(len(result['primary_comparisons']),3)
        self.assertEqual(len(result['chosen_branches_and_endpoints']),256)
        self.assertEqual(len(result['observed_prefix_predictive_diagnostics']),192)
        full_bytes=len(c.canonical(result))+100000
        self.assertLess(full_bytes,100_000_000)
        self.assertLess(339*2*LOG_CAP+full_bytes+30_000_000,500_000_000)
        receipt={'artificial_only':True,'all338_pre_analysis_jobs':True,
            'all256_cells':True,'all3_primaries':True,'serialized_analysis_with_seal_reserve':full_bytes,
            'max_worker_log_bytes':339*2*LOG_CAP,'combined_with30MBsource_models_and_fits':339*2*LOG_CAP+full_bytes+30_000_000}
        if (c.ROOT/'ANALYSIS-FOOTPRINT.json').exists():self.assertEqual(c.read(c.ROOT/'ANALYSIS-FOOTPRINT.json'),receipt)
        else:c.write(c.ROOT/'ANALYSIS-FOOTPRINT.json',receipt)

    def test_grid_gates_reservations_and_no_retry(self):
        jobs=c.grid();self.assertEqual(len(jobs),339)
        self.assertEqual(sum(j['seconds'] for j in jobs if j['gpu']),220800)
        self.assertEqual(sum(j['seconds'] for j in jobs if not j['gpu']),21600)
        self.assertEqual([j['updates'] for j in jobs if j['stage']=='fitting'],[192,192])
        events=[];gates=[]
        class Scheduler:
            def __init__(self,fail=None,ambiguous=None):self.calls=0;self.fail=fail;self.ambiguous=ambiguous
            def submit(self,j):
                self.calls+=1
                if self.calls==self.ambiguous:raise RuntimeError('network uncertain after sbatch')
                return str(500000+self.calls)
            def wait(self,job,j):return {'seconds':j['seconds'],'state':'FAILED' if self.calls==self.fail else 'COMPLETED','exit_code':'1:0' if self.calls==self.fail else '0:0'}
        s=Scheduler();r=execute(jobs,s,events.append,lambda j:None,lambda name,rows:gates.append((name,len(rows))),lambda:None)
        self.assertEqual(gates,[('technical',2),('models',82),('analysis',338)]);self.assertEqual(r['attempts'],339)
        for kind in ('fail','ambiguous'):
            events=[];s=Scheduler(**{kind:2})
            with self.assertRaises((RuntimeError,ValueError)):execute(jobs,s,events.append,lambda j:None,lambda *x:None,lambda:None)
            self.assertEqual(s.calls,2)
            if kind=='fail':self.assertEqual(events[-1]['gpu_seconds'],3600)
            else:self.assertEqual(events[-1]['reservation_retained'],1800)


role_map=c.roles()
if __name__=='__main__':unittest.main(verbosity=2)
