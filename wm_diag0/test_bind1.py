"""BIND1 amendments, solely artificial arrays and role metadata."""
import unittest
import json
import tempfile
from pathlib import Path
import numpy as np
from .readout import fit_artificial, task_margin
from .test_components import contract
from .roles_plan import propose
from .phase import seal_artificial, join_artificial_outcomes
from .core import Features, native_terminal_score
from .test_components import bank, ridge

class BindingTests(unittest.TestCase):
    def test_cohort_rows_match_live_authenticated_metadata(self):
        doc=Path(__file__).resolve().parents[1]/'docs/world-model-diagnostic-20261004'
        receipt=json.loads((doc/'test-receipts/METADATA-BIND1-002.json').read_text())
        self.assertEqual(receipt['returncode'],0)
        live=json.loads(receipt['stdout']);prepared=propose()['SOURCE-ROWS-PROPOSED.json']
        for task in ('pusht','reacher'):
            self.assertEqual(live['tasks'][task]['master_sha256'],prepared['tasks'][task]['master_sha256'])
            for a,b in zip(live['tasks'][task]['entries'],prepared['tasks'][task]['entries']):
                for key,value in a.items():self.assertEqual(value,b[key])
    def test_native_patch_output_reservation_arithmetic(self):
        # Array shapes account for BOTH predicted and realized full patches;
        # no representation pooling or precision downgrade to fit the cap.
        consequence_bytes=2*16*5*256*384*4
        goal_bytes=256*384*4
        readout_bytes=(256*384*6+2*256*384+6)*8
        action_endpoint_hash_allowance=300000
        self.assertLess(consequence_bytes+goal_bytes+readout_bytes+action_endpoint_hash_allowance,70000000)
        fit_validation_bytes=(256+96)*256*384*4
        self.assertLess(fit_validation_bytes+readout_bytes+300000,200000000)
    def test_phase_seal_precedes_outcome_access_and_binds_source(self):
        b=bank();c=contract();r=ridge(c);values=np.zeros((16,5,6))
        p=Features(values,c,b.identity,'parent-a','predicted');o=Features(values,c,b.identity,'parent-a','realized')
        calls=[]
        def outcome():
            calls.append('read')
            return {'source_id':'parent-a','bank_id':b.identity,'draws':[9301,9302],'success':np.zeros((16,2),int)}
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'phase'
            seal=seal_artificial(path,b,p,o,np.zeros(6),native_terminal_score,r,oracle_prefix_id='prefix-only',
                                 oracle_draw=9401,evaluation_draws=(9301,9302),domain='artificial')
            self.assertEqual(calls,[])
            body,y=join_artificial_outcomes(path,seal,outcome)
            self.assertEqual(calls,['read']);self.assertEqual(body['candidate_count'],16)
            bad=lambda:dict(outcome(),source_id='parent-b')
            with self.assertRaises(ValueError):join_artificial_outcomes(path,seal,bad)
            calls.clear()
            with (path/'action-0.npy').open('ab') as f:f.write(b'tamper')
            with self.assertRaises(ValueError):join_artificial_outcomes(path,seal,outcome)
            self.assertEqual(calls,[])
            with self.assertRaises(FileExistsError):seal_artificial(path,b,p,o,np.zeros(6),native_terminal_score,r,
                oracle_prefix_id='prefix-only',oracle_draw=9401,evaluation_draws=(9301,9302),domain='artificial')
    def test_reacher_raw_chart_cut_and_full_turn_not_wrapped(self):
        goal=np.array([np.pi-.01,0.])
        candidate=np.array([[-np.pi+.01,0.]])
        self.assertAlmostEqual(task_margin('reacher',candidate,goal)[0],(2*np.pi-.02)/.05)
        self.assertAlmostEqual(task_margin('reacher',np.array([[2*np.pi,0.]]),np.zeros(2))[0],2*np.pi/.05)
        self.assertAlmostEqual(task_margin('reacher',np.array([[.01,-.02]]),np.zeros(2))[0],.4)
        with self.assertRaises(ValueError):task_margin('reacher',np.zeros((1,4)),np.zeros(4))
    def test_identical_visual_inputs_cannot_recover_raw_winding(self):
        x=np.zeros((2,6));y=np.array([[0.,0.],[2*np.pi,0.]])
        r=fit_artificial(x,y,['fit']*2,(['fit'],['validation'],['diagnostic']),contract(),'reacher',domain='artificial')
        prediction=r.decode(x)
        np.testing.assert_array_equal(prediction[0],prediction[1])
        self.assertAlmostEqual(prediction[0,0],np.pi)
        self.assertAlmostEqual(np.abs(prediction-y)[:,0].mean(),np.pi)
        self.assertEqual(r.weights.shape,(6,2))
        # This is unavoidable ambiguity, NOT a success/accuracy criterion.
    def test_reused_roles_never_assign_unused_parents(self):
        proposal=propose();roles=proposal['ROLE-PROPOSAL.json'];pool=proposal['EXPOSED-POOL-METADATA.json']
        self.assertFalse(roles['unused_parent_allocation'])
        for task in ('pusht','reacher'):
            chosen=set(sum([roles[task][r] for r in ('diagnostic','fit','validation')],[]))
            self.assertEqual(len(chosen),60);self.assertTrue(chosen<=set(pool['parents'][task]))
            for x in proposal['SOURCE-ROWS-PROPOSED.json']['tasks'][task]['entries']:
                self.assertEqual(x['source_step'],min(200,(x['length']-25)//2))
                self.assertEqual(x['readout_rows'],[x['episode_offset']+s for s in x['readout_steps']])

if __name__=='__main__':unittest.main(verbosity=2)
