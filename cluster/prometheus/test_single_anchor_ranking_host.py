"""Host-only synthetic validation: no third-party imports or scheduler calls."""
import ast
import json
from pathlib import Path
import tempfile
import unittest
import single_anchor_ranking_host as host
import single_anchor_ranking_dispatch as dispatch


class HostTests(unittest.TestCase):
    def test_import_closure_is_standard_library(self):
        allowed = {'argparse', 'json', 'subprocess', 'time', 'pathlib', 'hashlib', 're',
                   'single_anchor_ranking_host', 'diffusion_extension_control'}
        for name in ('single_anchor_ranking_host', 'single_anchor_ranking_dispatch', 'diffusion_extension_control'):
            tree = ast.parse(Path(__file__).with_name(name+'.py').read_text())
            for node in ast.walk(tree):
                names = ([a.name for a in node.names] if isinstance(node, ast.Import)
                         else [node.module] if isinstance(node, ast.ImportFrom) else [])
                self.assertTrue(set(names) <= allowed, (name, names))

    def test_approval_conditions_identical_to_worker(self):
        def expression(name):
            tree = ast.parse(Path(__file__).with_name(name+'.py').read_text())
            fn = next(x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == 'check_approval')
            call = next(x for x in ast.walk(fn) if isinstance(x, ast.Call) and isinstance(x.func, ast.Name) and x.func.id == 'require')
            return ast.dump(call.args[0])
        self.assertEqual(expression('single_anchor_ranking_host'), expression('single_anchor_ranking'))
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'approval.json'
            good = dict(researcher_approved=True, experiment='single-anchor-ranking-20260914',
                        source_manifest_sha256='a'*64, protocol_sha256='b'*64,
                        repeats=2, gpu_seconds=14400, job_seconds=900, storage_bytes=2000000000)
            p.write_text(json.dumps(good))
            self.assertEqual(host.check_approval(p, 'a'*64, 'b'*64), good)
            for field in good:
                bad = dict(good);bad[field] = None;p.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):host.check_approval(p, 'a'*64, 'b'*64)

    def test_manifest_and_path_guards(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp);p=root/'file';p.write_bytes(b'original')
            manifest=root/'SOURCE-MANIFEST.sha256'
            manifest.write_text(host.sha256(p)+'  file\n')
            digest=host.sha256(manifest);host.verify_source(root,digest)
            p.write_bytes(b'changed')
            with self.assertRaises(ValueError):host.verify_source(root,digest)
            for bad in ('../escape','/absolute','bad\\name','.'):
                with self.assertRaises(ValueError):host.checked_child(root,bad)
            with self.assertRaises(ValueError):host.require_sha(p,'not-a-hash')

    def test_unchanged_ids_and_reservations(self):
        self.assertEqual(len(host.REFS),32)
        self.assertEqual(host.REFS[:4],(1269,582,525,722))
        self.assertTrue(all(0 <= r < 1600 for r in host.REFS))
        self.assertTrue(dispatch.allowed(13500,1936000000))
        self.assertFalse(dispatch.allowed(13501,0))
        self.assertFalse(dispatch.allowed(0,1936000001))
        self.assertFalse(dispatch.allowed(13500,0,1))


if __name__ == '__main__':unittest.main()
