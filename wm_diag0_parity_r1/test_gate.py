import ast,json,unittest
from pathlib import Path
from .operations import STAGE,OBSERVE
from .reconcile import PROGRAM
from .common import DOC

class Gate(unittest.TestCase):
    def test_remote_programs_and_controller_python36(self):
        for code in (STAGE,OBSERVE,PROGRAM,(Path(__file__).parent/'supervisor.py').read_text()):ast.parse(code,feature_version=(3,6))
        for p in Path(__file__).parent.glob('*.py'):compile(p.read_bytes(),str(p),'exec')
    def test_no_predictor_physics_score_or_optimizer_probe(self):
        tree=ast.parse((Path(__file__).parent/'probe.py').read_text())
        attributes={n.func.attr for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)}
        self.assertFalse(attributes&{'predict','rollout','get_cost','costs','step','reset','fit','solve'})
        self.assertNotIn('wm_diag0_campaign_v4.submit',STAGE)
        self.assertIn("'--time=3'",STAGE)
        self.assertIn("'--qos=normal-a6000'",STAGE)
    def test_reconciled_no_live_and_all_successes_retained(self):
        z=json.loads((DOC/'RECONCILIATION-001.json').read_text())
        self.assertEqual(z['queue'],'');self.assertEqual(z['GPU_charged_seconds'],236)
        self.assertEqual(len(z['accepted']),5);self.assertEqual(z['failed_bank_shape'],[16,25,2])
        self.assertLessEqual(236+180+127*3600,468000)

if __name__=='__main__':unittest.main()
