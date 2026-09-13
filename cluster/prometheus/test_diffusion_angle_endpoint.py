import unittest
import numpy as np
from diffusion_bottleneck import trajectory_diagnostics,IntegrityError

class EndpointTests(unittest.TestCase):
    def result(self,angle,goal=0.):
        states=np.zeros((2,7),np.float64);states[:,4]=angle
        target=np.zeros(7,np.float64);target[4]=goal
        before=states.tobytes(),target.tobytes()
        result=trajectory_diagnostics(states,target)
        self.assertEqual(before,(states.tobytes(),target.tobytes()))
        return result
    def test_native_tiny_negative_rounds_to_endpoint(self):
        value=float(-1e-20%(2*np.pi));self.assertEqual(value,2*np.pi)
        self.assertTrue(self.result(value)['success'])
    def test_exact_and_inside_endpoints(self):
        for angle in (0.,np.nextafter(0.,np.inf),np.nextafter(2*np.pi,0.),2*np.pi):
            self.assertTrue(self.result(angle)['success'])
    def test_outside_neighbors_and_nonfinite_rejected(self):
        for angle in (np.nextafter(0.,-np.inf),np.nextafter(2*np.pi,np.inf),np.nan,np.inf,-np.inf):
            with self.subTest(angle=angle),self.assertRaises(IntegrityError):self.result(angle)
    def test_goal_contract_not_broadened(self):
        with self.assertRaises(IntegrityError):self.result(0.,2*np.pi)
        self.assertTrue(self.result(0.,np.nextafter(2*np.pi,0.))['success'])
    def test_historical_threshold_operations_preserved_both_directions(self):
        threshold=np.pi/9
        for d in (np.nextafter(threshold,0.),threshold,np.nextafter(threshold,np.inf)):
            for state,goal in ((d,0.),(0.,d),(2*np.pi,d),(d,np.nextafter(2*np.pi,0.))):
                raw=abs(state-goal)
                expected=min(raw,2*np.pi-raw)<threshold
                self.assertEqual(self.result(state,goal)['success'],expected)

if __name__=='__main__':unittest.main()
