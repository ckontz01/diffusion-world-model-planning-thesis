import unittest
import numpy as np
from verify_diffusion_branch import physical,midranks,rank_correlation
from diffusion_bottleneck import IntegrityError

class PhysicalVerifierTests(unittest.TestCase):
    def test_midranks_ties(self):
        np.testing.assert_array_equal(midranks([3,1,1,2]),[3,.5,.5,2])
    def test_constant_ranking_undefined(self):
        self.assertIsNone(rank_correlation([1,1],[2,3]))
    def test_joint_position_not_separate_norms(self):
        states=np.zeros((1,7));states[0,[0,2]]=15
        r=physical(states,np.zeros((1,2),bool),np.zeros(7))
        self.assertFalse(r['success']);self.assertGreater(r['closest_margin'],1)
    def test_success_same_step(self):
        s=np.zeros((2,7));s[0,4]=1;s[1,0]=40
        self.assertFalse(physical(s,np.zeros((2,2),bool),np.zeros(7))['success'])
    def test_step_after_terminal_refused(self):
        with self.assertRaises(IntegrityError):physical(np.zeros((2,7)),np.ones((2,2),bool),np.zeros(7))
    def test_terminal_success(self):
        self.assertTrue(physical(np.zeros((1,7)),np.array([[True,False]]),np.zeros(7))['success'])

if __name__=='__main__':unittest.main()
