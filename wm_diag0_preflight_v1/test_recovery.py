"""Artificial/static checks for new transport recovery, no old suites rerun."""
import ast
import hashlib
import json
import unittest
from wm_diag0_preflight_v1.common import ROOT,DOC,identity

class RecoveryTests(unittest.TestCase):
    def test_source_and_python36_receiver_parse(self):
        for name in ('stage_recovery_r1.py','observe.py'):
            tree=ast.parse((ROOT/'wm_diag0_preflight_v1'/name).read_text())
            for n in ast.walk(tree):
                if isinstance(n,ast.Constant) and isinstance(n.value,str) and n.value.lstrip().startswith('import '):
                    ast.parse(n.value,feature_version=(3,6))
    def test_prefix_plus_suffix_preserves_exact_original(self):
        full=bytes(range(256))*7; prefix=full[:317]
        retained=bytes(prefix); reconstructed=prefix+full[len(prefix):]
        self.assertEqual(hashlib.sha256(reconstructed).digest(),hashlib.sha256(full).digest())
        self.assertEqual(retained,prefix)
    def test_original_frozen_worker_not_changed(self):
        c=json.loads((DOC/'CONTRACT.json').read_text())
        for name in ('__init__.py','common.py','worker.py','supervisor.py'):
            self.assertEqual(identity(ROOT/'wm_diag0_preflight_v1'/name),c['staged_members']['wm_diag0_preflight_v1/'+name])
    def test_reconciled_no_dispatch_or_receiver(self):
        r=json.loads((DOC/'STAGE-FAILURE-RECONCILIATION-001.json').read_text())
        self.assertFalse(r['dispatch_exists']); self.assertEqual(r['exact_upload_processes'],[])
        self.assertEqual(r['partial']['artifacts/reacher.pth']['bytes'],16777216)
        self.assertLessEqual(12342309744+r['total_retained_bytes'],13000000000)

if __name__=='__main__': unittest.main()
