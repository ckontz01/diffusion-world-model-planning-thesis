"""Metadata and full artificial component-chain checks, no science access."""
import json
import tempfile
from pathlib import Path
import unittest
import numpy as np
from .core import Features, aligned_realized, select_four, native_terminal_score
from .readout import check_roles
from .analysis import estimate
from .resource_plan import counts
from .test_components import bank, contract, ridge
from .preserve_preparation import build_archive, verify_archive

ROOT=Path(__file__).resolve().parents[1]
DOC=ROOT/'docs/world-model-diagnostic-20261004'

class PackageTests(unittest.TestCase):
    def test_preparation_archive_whole_members_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'new.zip'
            members={'wm_diag0/artificial.txt':b'artificial-only'}
            expected=build_archive(p,'1'*40,members)
            self.assertEqual(len(verify_archive(p,expected)),2)
            with self.assertRaises(FileExistsError):build_archive(p,'1'*40,members)
            expected['wm_diag0/artificial.txt']=b'changed'
            with self.assertRaises(ValueError):verify_archive(p,expected)
    def test_roles_and_rows_are_proposals(self):
        roles=json.loads((DOC/'ROLE-PROPOSAL.json').read_text())
        rows=json.loads((DOC/'SOURCE-ROWS-PROPOSED.json').read_text())
        self.assertEqual(rows['payload_reads'],0)
        self.assertEqual(rows['status'],'PROPOSED_NOT_ALLOCATED')
        for task in ('pusht','reacher'):
            r=roles[task]; check_roles(r['fit'],r['validation'],r['diagnostic'])
            for role,n in (('fit',16),('validation',12),('diagnostic',32)):
                selected=[x for x in rows['tasks'][task]['entries'] if x['role']==role]
                self.assertEqual([x['parent'] for x in selected],r[role]);self.assertEqual(len(selected),n)
                for x in selected:
                    self.assertEqual(x['partition'],'P2')
                    self.assertEqual(x['goal_step']-x['source_step'],24)
                    self.assertLessEqual(x['replay_actions'],200)
                    self.assertEqual(x['source_row'],x['episode_offset']+x['source_step'])
                    self.assertEqual(x['goal_row'],x['episode_offset']+x['goal_step'])
    def test_finite_complete_workload(self):
        c=counts()
        self.assertEqual(c['fresh_worlds'],6272)
        self.assertEqual(c['physical_controller_steps_upper'],1510400)
        self.assertEqual(c['predicted_transitions_upper'],190090240)
        self.assertEqual(c['gpu_allocation_seconds_cap'],468000)
        self.assertEqual(c['successful_logical_tasks'],134)
    def test_selection_precedes_outcome_join_artificial_chain(self):
        b=bank();c=contract();r=ridge(c);g=np.zeros(6)
        values=np.zeros((16,5,6))
        p=Features(values,c,b.identity,'diagnostic','predicted')
        observed=np.arange(26)[:,None]*np.ones((1,6))
        o=Features(np.stack([aligned_realized(observed,c.positions)]*16),c,b.identity,'diagnostic','realized')
        selection=select_four(b,p,o,g,native_terminal_score,r)
        seal=selection.identity
        # All fail is a valid accepted discovery result. No oracle-win assertion.
        result=estimate(['artificial-parent'],np.zeros((1,16,2),int),np.array([selection.choices]),[0],
                        local_progress=np.ones((1,16,2)))
        self.assertEqual(selection.identity,seal)
        self.assertEqual(result['cells'],dict(P0=0.,P1=0.,O0=0.,O1=0.))
        self.assertEqual(result['n_independent_parents'],1)
    def test_research_authorization_remains_disabled(self):
        a=json.loads((DOC/'AUTHORIZATION.json').read_text())
        for key in ('execute','research_inference','research_fitting','simulator','new_payload_reads','slurm','monitoring'):
            self.assertFalse(a[key])
        for module in ('core.py','readout.py','branches.py','adapters.py'):
            text=(ROOT/'wm_diag0'/module).read_text()
            self.assertNotIn('import torch',text)
            self.assertNotIn('import h5py',text)
            self.assertNotIn('import gym',text)

if __name__=='__main__':unittest.main(verbosity=2)
