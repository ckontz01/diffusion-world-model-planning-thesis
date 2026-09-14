"""Adversarial saved-label regressions; synthetic data only, no simulator."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import candidate_value_contract as ct
import candidate_value_learning as c
from candidate_value_data import (collect,read_npz,load_record,validated_banks,
    validate_saved_trajectory,validate_candidate_delivery,checked_decoded_bank)
from candidate_value_models import train
from candidate_value_analyze import validation
from test_candidate_value_pipeline import SyntheticBackend,synthetic_record,synthetic_capsule,save_report


def overwrite_fixture(path,arrays):
    # Only test-created temporary artifacts are deliberately corrupted.
    with Path(path).open('wb') as f:np.savez_compressed(f,**arrays)


class SavedValidationTests(unittest.TestCase):
    def fixtures(self,root,role):
        allocation=ct.allocation();allocation[role]=allocation[role][:1]
        capsule=synthetic_capsule(root,allocation);ref=allocation[role][0]
        for offset,h in enumerate((75,150)):
            p=root/('%s-%d'%(role,offset));p.mkdir()
            record,environment_seed=load_record(capsule,ref,h,role)
            save_report(p,role,offset,collect(SyntheticBackend(),record,environment_seed,ref,h,p))
        return allocation,capsule

    def corrupt_label(self,root,role,kind):
        p=root/(role+'-0');report=ct.json_read(p/'REPORT.json')
        row=next(x for x in report['banks'][0]['labels'] if x['candidate']==(1 if kind=='false_positive' else 0))
        path=p/row['trace_file'];trace=read_npz(path)
        if kind=='false_positive':
            # Flags and target stay mutually consistent and positive. Only the
            # physical trajectory reveals that success never actually occurred.
            trace['states'][-1]=synthetic_record()['state']
        else:
            decoded=checked_decoded_bank(read_npz(p/'bank-0.npz'))
            trace['actions'][:15]=decoded[2]  # valid actions, wrong sampled index
        overwrite_fixture(path,trace)
        (p/'sha256.txt').unlink();ct.seal(p)
        ct.check_report(p,role,0,'src','cap')  # checksum/provenance alone passes

    def test_physically_false_positive_rejected_before_fit(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);allocation,capsule=self.fixtures(root,'train')
            self.corrupt_label(root,'train','false_positive')
            with patch.object(ct,'allocation',return_value=allocation),patch.object(c,'fit') as fit:
                with self.assertRaises(AssertionError):train(root,root/'unused','src','cap',capsule)
                fit.assert_not_called()

    def test_wrong_candidate_chunk_rejected_despite_valid_seal_and_label(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);allocation,capsule=self.fixtures(root,'train')
            self.corrupt_label(root,'train','wrong_candidate')
            with patch.object(ct,'allocation',return_value=allocation):
                with self.assertRaises(AssertionError):list(validated_banks(root,'train','src','cap',capsule))

    def test_false_positive_rejected_before_ranking_scores(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);allocation,capsule=self.fixtures(root,'validation')
            self.corrupt_label(root,'validation','false_positive')
            with patch.object(ct,'allocation',return_value=allocation),patch('candidate_value_analyze.Predictor') as predictor:
                with self.assertRaises(AssertionError):validation(root,root/'unused','src','cap',capsule)
                predictor.assert_not_called()

    def trajectory(self,n,h,success=True):
        record=synthetic_record();states=np.tile(record['state'],(n,1))
        flags=np.zeros((n,2),bool)
        if success:states[-1]=record['goal_state'];flags[-1,0]=True
        if n==300:flags[-1,1]=True
        bank=SyntheticBackend().episode(record,h,0,0,bank_times=c.anchors(h))['banks'][0]
        decoded=checked_decoded_bank(bank)
        actions=np.tile(decoded[0],((n+14)//15,1))[:n].copy()
        trace=dict(states=states,actions=actions,flags=flags,initial=record['state'].copy(),
                   dynamics=np.zeros((n,10),np.float64))
        return trace,record,decoded

    def test_first_chunk_and_final_budget_success_and_exact_angle_endpoint(self):
        for h in (75,150):
            for n in (1,15,2*h):
                trace,record,decoded=self.trajectory(n,h)
                result=validate_saved_trajectory(trace,record,h)
                self.assertEqual(result['success'],1);self.assertEqual(result['steps'],n)
                self.assertEqual(result['first_chunk_success'],n<=15)
                validate_candidate_delivery(trace,decoded,0,0)
                if n==2*h:
                    final=validate_saved_trajectory(trace,record,h,anchor=2*h-15)
                    self.assertTrue(final['first_chunk_success']);self.assertEqual(final['steps'],15)
                    validate_candidate_delivery(trace,decoded,2*h-15,0)
        trace,record,_=self.trajectory(1,75)
        record['goal_state'][4]=0.;trace['states'][-1,4]=2*np.pi
        self.assertEqual(validate_saved_trajectory(trace,record,75)['success'],1)

    def test_strict_combined_norm_angular_threshold_and_terminal_rejections(self):
        for boundary in ('position','angle'):
            trace,record,_=self.trajectory(150,75,False)
            trace['states'][:]=record['goal_state']
            if boundary=='position':trace['states'][:,:4]+=10.  # combined norm exactly20
            else:record['goal_state'][4]=0.;trace['states'][:,4]=np.pi/9
            self.assertEqual(validate_saved_trajectory(trace,record,75)['success'],0)
        trace,record,_=self.trajectory(15,75,False);trace['flags'][-1,1]=True
        with self.assertRaises(RuntimeError):validate_saved_trajectory(trace,record,75)
        trace,record,_=self.trajectory(1,75);trace['actions']=np.tile(trace['actions'],(2,1))
        with self.assertRaises(RuntimeError):validate_saved_trajectory(trace,record,75)
        trace,record,_=self.trajectory(15,75);trace['states'][0]=record['goal_state']
        with self.assertRaises(AssertionError):validate_saved_trajectory(trace,record,75)


if __name__=='__main__':unittest.main()
