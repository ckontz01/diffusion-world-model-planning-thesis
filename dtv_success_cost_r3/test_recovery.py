"""Exact lazy-constructor reset and full multi-lineage acceptance tests; no physics."""
import copy,inspect,json,os,tempfile,types,unittest,importlib.util
from pathlib import Path
from unittest.mock import patch
import numpy as np
from dtv_success_cost.common import *
from dtv_success_cost import native as oldnative,worker as oldworker,analysis as oldanalysis
from dtv_success_cost_r1.test_recovery import Recovery as R1Tests
from dtv_success_cost_r2 import worker as r2worker,render
from dtv_success_cost_r3 import common,campaign,worker,native,accept,analysis_entry,preserve

class Recovery(unittest.TestCase):
    def fixture_modules(self):
        gym=types.ModuleType('gymnasium');gym.registry={}
        gym.register=lambda name,entry_point:gym.registry.__setitem__(name,entry_point)
        class Cube:
            def __init__(self):self.calls=[];self._model=types.SimpleNamespace(nq=2)
            @property
            def observation_space(self):
                self.reset()  # installed ManipSpaceEnv's lazy constructor callback
                return 'artificial-space'
            def reset(self,seed=None,options=None):
                self.calls.append(('base_reset',seed,options));return ('native-bootstrap',{'construction':True})
            def set_state(self,qpos,qvel):self.calls.append(('set_state',qpos.tolist(),qvel.tolist()))
            def pre_step(self):self.calls.append(('pre_step',))
            def post_step(self):self.calls.append(('post_step',))
            def set_target_pos(self,*a):self.calls.append(('target',a))
            def compute_observation(self):return 'exact-saved-state-observation'
            def get_reset_info(self):return {'saved-state':True}
        cube=types.ModuleType('stable_worldmodel.envs.ogbench.cube_env');cube.CubeEnv=Cube
        swm=types.ModuleType('stable_worldmodel')
        class World:
            def __init__(self,**kw):
                self.kw=kw;self.native=gym.registry[kw['env_name']]();self.space=self.native.observation_space
            def reset(self,seed=None,options=None):return self.native.reset(seed=seed,options=options)
        swm.World=World
        return {'gymnasium':gym,'stable_worldmodel':swm,'stable_worldmodel.envs.ogbench.cube_env':cube}
    def data(self):
        return dict(qpos=np.array([1.,2.]),qvel=np.array([3.,4.])),dict(privileged_block_0_pos=[5.,6.,7.],privileged_block_0_quat=[0.,0.,0.,1.])
    def test_original_lazy_constructor_fault_reproduced_without_physics(self):
        data,target=self.data()
        with patch.dict(__import__('sys').modules,self.fixture_modules()):
            with self.assertRaises(TypeError):oldnative.environment('cube',data,target,17)
    def test_constructor_none_options_returns_native_bootstrap_and_never_applies_saved_state(self):
        data,target=self.data()
        with patch.dict(__import__('sys').modules,self.fixture_modules()):
            world,reset=native.environment('cube',data,target,17)
            self.assertEqual(world.native.calls,[('base_reset',None,None)])
            self.assertEqual(world.kw['max_episode_steps'],100);self.assertTrue(world.kw['terminate_at_goal'])
    def test_explicit_episode_reset_retains_exact_state_target_order_seed_and_return(self):
        data,target=self.data()
        with patch.dict(__import__('sys').modules,self.fixture_modules()):
            world,reset=native.environment('cube',data,target,17)
            result=reset();calls=world.native.calls[1:]
            self.assertEqual(calls[0][0:2],('base_reset',17));self.assertEqual(calls[1],('set_state',[1.,2.],[3.,4.]))
            self.assertEqual([x[0] for x in calls],['base_reset','set_state','pre_step','target','post_step'])
            self.assertEqual(calls[3][1],(0,target['privileged_block_0_pos'],target['privileged_block_0_quat']))
            self.assertEqual(result,('exact-saved-state-observation',{'saved-state':True}))
    def test_native_copy_has_only_the_constructor_none_guard_no_target_or_model_change(self):
        old=inspect.getsource(oldnative.environment)
        expected=old.replace("                super().reset(seed=seed,options=options)",
                            "                base_result=super().reset(seed=seed,options=options)\n                if options is None:return base_result  # native lazy observation-space bootstrap, not an evaluation reset")
        self.assertEqual(expected.strip(),inspect.getsource(native.environment).strip())
        for obj in ('read_source','Decoder','Adapter'):
            self.assertEqual(inspect.getsource(getattr(oldnative,obj)),inspect.getsource(getattr(native,obj)))
        self.assertEqual(inspect.getsource(worker.gpu_job),inspect.getsource(r2worker.gpu_job).replace('from dtv_success_cost.native import read_source,Adapter','from dtv_success_cost_r3.native import read_source,Adapter'))
        self.assertIs(analysis_entry.analyze,oldanalysis.analyze)
    def test_exact_remaining_grid_caps_rendering_namespace_and_gate(self):
        c=load(DOC/'BINDINGS.json');jobs=campaign.commands(c,Path('/old'),Path('/r3'),Path('/run'),Path('/r1'),Path('/r2'))
        self.assertEqual(len(jobs),2875);self.assertEqual(jobs[0]['id'],'cube-3506-6101')
        self.assertEqual(sum(x['gpu'] for x in jobs),2874)
        self.assertEqual(campaign.reservations(c,dict(gpu=395,cpu=178),jobs),dict(gpu=862595,cpu=7378))
        for j in jobs[:-1]:
            self.assertIn('MUJOCO_GL=egl',j['command'][-1]);self.assertIn('dtv_success_cost_r3.worker',j['command'][-1])
            self.assertIn('/run/recovery-r3/workers/'+j['id'],j['command'][-1])
        self.assertEqual([i for i in range(len(jobs)) if campaign.gate_record(i)],[2])
        for i in range(6):self.assertNotIn(c['jobs'][i]['id'],[j['id'] for j in jobs])
    def test_actual_multi_history_projection_excludes_failed_first_attempt_of_carried_reacher(self):
        c=load(DOC/'BINDINGS.json');l=load(common.LINEAGE);history=[[],[]];future=[];old=[]
        def rows(task,allocation,elapsed=1,state='COMPLETED'):
            cpu=task in ('analysis','preflight');res='cpu=4,mem=8G'+('' if cpu else ',gres/gpu=1')
            code='0:0' if state=='COMPLETED' else '1:0'
            return [dict(event='submission_intent',task=task),dict(event='submitted',task=task,allocation_id=allocation),
                    dict(event='scheduler',allocation_id=allocation,returncode=0,stdout=f'{allocation}|dtveff1-{task}|{state}|{code}|{elapsed}|{res}|gpu09'),
                    dict(event='terminal',task=task,allocation_id=allocation,state=state,exit=code,elapsed_seconds=elapsed),dict(event='accepted',task=task)]
        old=[dict(event='submission_intent',task='preflight'),dict(event='submission_response',task='preflight'),
             dict(event='submitted',task='preflight',allocation_id='312920'),dict(event='scheduler',allocation_id='312920')]
        for i,j in enumerate(c['jobs']):
            if i<6:
                supplier=l['carried'][i];history[i//3]+=rows(j['id'],supplier['allocation_id'],supplier['elapsed_seconds'])
            else:
                future+=rows(j['id'],str(900000+i))
                if i==8:future.append(dict(event='technical_tranche_passed',included_workers=9))
        history[0]+=rows('reacher-4374-6101','312924',19,'FAILED')[:-1]
        history[1]+=rows('cube-3506-6101','312928',19,'FAILED')[:-1]
        future+=rows('analysis','999999')
        carry=dict(event='carried_history_accepted',gpu_seconds=395,cpu_seconds=178,allocations=['312920']+common.CARRIED_IDS,
            failed_allocations=['312924','312928'],lineage_sha256='a'*64,resolution_sha256='a'*64)
        with patch.object(accept,'verify_resolution'),patch.object(accept,'authenticate_history',return_value=tuple(history)),patch.object(accept,'sha',return_value='a'*64),patch.object(accept,'events',side_effect=[old,[carry]+future]),patch.object(accept,'load',side_effect=[{},l]):
            result=accept.accounting(Path('/fixture'),c,True)
        self.assertEqual(result['unique_tasks'],2882);self.assertEqual(result['actual_attempts'],2884)
        self.assertEqual(result['gpu_allocation_seconds'],395+2874);self.assertEqual(result['failed_gpu_allocation_seconds'],38)
        self.assertEqual(sum(x['task']=='reacher-4374-6101' for x in result['allocations']),1)
    def test_actual_transport_compiles_and_current_archive_adapter_preserves_all_roots(self):
        path=common.HERE/'transport.py';spec=importlib.util.spec_from_file_location('r3transport',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        for body in (module.STAGE,module.LAUNCH,module.OBSERVE):compile(module.BASE.replace('IDENTITY_PLACEHOLDER','{}')+'\n'+body,str(path),'exec')
        self.assertIn('dtv_success_cost_r3.accept',inspect.getsource(preserve.archive))
    def test_unknown_stop_and_false_capability_stop_instead_of_restarting(self):
        with tempfile.TemporaryDirectory() as d:
            run=Path(d);common.location(run).mkdir();write(common.location(run)/'STOP-R3.json',{})
            with self.assertRaisesRegex(RuntimeError,'unresolved'):common.verify_resolution(run,{})
            path=run/'approval.json';write(path,dict(study='DTV-EFF1-R3',execute=False))
            with self.assertRaisesRegex(RuntimeError,'disabled'):common.recovery_gate(path)
if __name__=='__main__':unittest.main()
