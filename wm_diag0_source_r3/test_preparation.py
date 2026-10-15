import ast,json,unittest
from pathlib import Path
from .build import additions,bounds
from .common import DOC,R2

class Preparation(unittest.TestCase):
    def test_exact_one_retry_bound(self):
        a=json.loads((DOC/'AUTHORITY.json').read_text());r=json.loads((R2/'RECONCILIATION-001.json').read_text())
        self.assertEqual(bounds(a,r)['all_controller_steps_max'],386924)
        a['genuinely_failed_replacements_max']=2
        with self.assertRaises(ValueError):bounds(a,r)
    def test_only_two_existing_source_changes_and_frozen_writer(self):
        b=additions();self.assertEqual(set(b),{'wm_diag0_native_v3/entry.py','wm_diag0_native_v3/supervisor.py','wm_diag0_source_r2/writer.py','wm_diag0_source_r2/__init__.py'})
        self.assertIn(b'original+\':\'+original+\':ro\'',b['wm_diag0_native_v3/supervisor.py'])
        for n,raw in b.items():compile(raw,n,'exec')
        ast.parse(b['wm_diag0_native_v3/supervisor.py'],feature_version=(3,6))
    def test_new_control_programs_are_python36(self):
        for p in Path(__file__).parent.glob('*.py'):
            t=ast.parse(p.read_text());compile(t,str(p),'exec')
            for n in ast.walk(t):
                if isinstance(n,ast.Constant) and isinstance(n.value,str) and n.value.lstrip().startswith(('import json','import base64','import hashlib')):ast.parse(n.value,feature_version=(3,6))

if __name__=='__main__':unittest.main()
