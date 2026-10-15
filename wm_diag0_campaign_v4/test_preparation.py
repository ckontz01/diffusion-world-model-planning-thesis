"""New narrow import repair and generated-control syntax checks only."""
import ast,json,unittest
from pathlib import Path
from .common import ROOT,DOC,identity
from wm_diag0_native_v3.common import DOC as OLD_DOC

class Preparation(unittest.TestCase):
    def test_only_optional_initializer_changes(self):
        old=json.loads((OLD_DOC/'CONTRACT.json').read_text());new=json.loads((DOC/'source-import-r1/CONTRACT.json').read_text())
        differences=[n for n,x in old['staged_members'].items() if x!=new['staged_members'][n]]
        self.assertEqual(differences,['stable_worldmodel/__init__.py'])
        self.assertEqual(new['root_plan_sha256'],old['root_plan_sha256'])
        self.assertEqual(new['source_attempts_max'],120)
    def test_initializer_contains_no_constructors_or_data_import(self):
        t=ast.parse((ROOT/'wm_diag0_campaign_v4/native_init.py').read_text())
        self.assertFalse(any(isinstance(n,ast.Call) for n in ast.walk(t)))
        self.assertEqual([a.name for n in t.body if isinstance(n,ast.ImportFrom) for a in n.names],['utils','spaces'])
    def test_new_source_compiles_and_control_literals_parse(self):
        count=0
        for p in (ROOT/'wm_diag0_campaign_v4').glob('*.py'):
            t=ast.parse(p.read_text());compile(t,str(p),'exec')
            for n in ast.walk(t):
                if isinstance(n,ast.Constant) and isinstance(n.value,str) and n.value.lstrip().startswith(('import json','import hashlib')):
                    ast.parse(n.value,feature_version=(3,6));count+=1
        self.assertGreaterEqual(count,3)

if __name__=='__main__':unittest.main()
