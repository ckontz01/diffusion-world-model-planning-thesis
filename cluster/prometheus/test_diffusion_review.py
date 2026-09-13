"""Independent endpoint and pinned identifier-selection review tests."""
import hashlib
import json
import math
from pathlib import Path
import unittest
import numpy as np
from diffusion_bottleneck_traces import independent_physical_success
from diffusion_bottleneck import trajectory_diagnostics

class ReviewTests(unittest.TestCase):
    def test_four_coordinate_ball_not_two_balls(self):
        s=np.zeros((2,7));s[1,[0,2]]=15
        self.assertFalse(independent_physical_success(s,np.zeros(7)))
    def test_initial_only_does_not_count(self):
        s=np.zeros((2,7));s[1,0]=21
        self.assertFalse(independent_physical_success(s,np.zeros(7)))
    def test_different_steps_not_combined(self):
        s=np.zeros((3,7));s[1,4]=1;s[2,0]=21
        self.assertFalse(independent_physical_success(s,np.zeros(7)))
    def test_wrap_both_directions(self):
        for a,b in ((.01,2*math.pi-.01),(2*math.pi-.01,.01)):
            s=np.zeros((2,7));s[:,4]=a;g=np.zeros(7);g[4]=b
            self.assertTrue(independent_physical_success(s,g))
    def test_joint_boundary(self):
        s=np.zeros((2,7));s[1,0]=20
        self.assertFalse(independent_physical_success(s,np.zeros(7)))
    def test_angular_boundary(self):
        # A value definitely outside avoids masking binary rounding at pi/9.
        s=np.zeros((2,7));s[1,4]=math.pi/9+1e-12
        self.assertFalse(independent_physical_success(s,np.zeros(7)))
    def test_independent_finite_random_cases(self):
        rng=np.random.default_rng(20260914)
        for _ in range(1000):
            s=rng.uniform(-30,30,(8,7));s[:,4]=rng.uniform(0,2*math.pi,8)
            g=np.zeros(7);g[4]=rng.uniform(0,2*math.pi)
            self.assertEqual(independent_physical_success(s,g),trajectory_diagnostics(s,g)['success'])
    def test_committed_selection(self):
        p=Path(__file__).resolve().parents[2]/'docs/bottleneck/BRANCH-PILOT-SELECTION.json'
        m=json.loads(p.read_text());namespace=m['namespace']
        order=sorted(range(1600),key=lambda i:(hashlib.sha256(f'{namespace}|{i}'.encode()).hexdigest(),i))
        self.assertEqual(order[:32],m['development_reference_indices'])
        self.assertEqual(order[:4],[1269,582,525,722])

if __name__=='__main__':unittest.main()
