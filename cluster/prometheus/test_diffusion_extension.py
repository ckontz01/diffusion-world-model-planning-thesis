import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch
from diffusion_extension_control import REFS,allowed,command,PRIOR_ALLOCATION_SECONDS
from verify_diffusion_extension import effects

class ExtensionTests(unittest.TestCase):
    def test_failed_preflight_allocation_retained(self):
        self.assertEqual(PRIOR_ALLOCATION_SECONDS,11)

    def test_login_python36_subprocess_compatibility(self):
        with patch('diffusion_extension_control.subprocess.check_output',return_value='123\n') as call:
            self.assertEqual(command('sbatch','--parsable'),'123')
            call.assert_called_once_with(('sbatch','--parsable'),universal_newlines=True)

    def test_exact_identifier_selection(self):
        ns='diffusion-bottleneck-v1|development-selection|2026-09-13'
        self.assertEqual(tuple(sorted(range(1600),key=lambda i:(hashlib.sha256(f'{ns}|{i}'.encode()).hexdigest(),i))[:32]),REFS)
        self.assertEqual(len(set(REFS[4:])),28)

    def test_only_two_runner_changes(self):
        root=Path(__file__).parent
        old=(root/'diffusion_bottleneck_branch.py').read_text()
        new=(root/'diffusion_bottleneck_extension_runner.py').read_text()
        expected=old.replace('PILOT=(1269,582,525,722)','PILOT=('+','.join(map(str,REFS))+')')
        expected=expected.replace('tuple(ordered[:4])==PILOT','tuple(ordered[:32])==PILOT')
        self.assertEqual(new,expected)

    def test_cost_reservation(self):
        self.assertTrue(allowed(6900,936_000_000))
        self.assertFalse(allowed(6901,0));self.assertFalse(allowed(0,936_000_001))
        self.assertFalse(allowed(-1,0))

    def test_equal_horizon_reference_effect(self):
        rows=[]
        for h,t,value in ((75,0,1),(75,30,3),(150,0,10)):
            base={'success':False,'closest_margin':20}
            q={'success':True,'closest_margin':20-value}
            rows.append({'reference':1,'horizon':h,'anchor':t,'available':True,
                'selected':{'baseline':{'first_chunk':base,'committed_two_chunk':base},
                            **{c:{'committed_two_chunk':q} for c in ('state','latent','joint')}},
                'greedy64_first_chunk':q})
        r=effects(rows,(1,))
        self.assertEqual(r['reference_effects'][0]['contrasts']['state']['margin_improvement'],6)
        self.assertEqual(r['summary']['state']['success_difference_pp']['mean'],100)
        self.assertEqual(r['summary']['state']['margin_improvement']['n_references'],1)

if __name__=='__main__':unittest.main()
