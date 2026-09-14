"""Infrastructure-only regressions; no research inputs, simulator or model."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import candidate_value_contract as ct
from candidate_value_dispatch import copy_evidence,prior_costs


class TechnicalRepairTests(unittest.TestCase):
    def test_symlink_view_stability_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);root=p/'environment';root.mkdir()
            (root/'regular').write_bytes(b'fixed dependency')
            target=p/'container-python';link=root/'python';link.symlink_to(target)
            (root/'python3').symlink_to('python')
            absent=ct.tree_hash(root)
            target.write_bytes(b'container-owned executable')
            self.assertEqual(absent,ct.tree_hash(root))
            # The actual container is independently byte-pinned by authorize;
            # these links must not depend on host availability of its paths.
            link.unlink();link.symlink_to(p/'other-python')
            changed=ct.tree_hash(root);self.assertNotEqual(absent,changed)
            (root/'regular').write_bytes(b'changed dependency')
            self.assertNotEqual(changed,ct.tree_hash(root))

    def test_content_copy_does_not_copy_xattrs_or_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);src=p/'src';dst=p/'dst';src.write_bytes(b'preserved evidence')
            with patch('shutil.copystat',side_effect=PermissionError('lustre.lov')) as metadata:
                copy_evidence(src,dst);metadata.assert_not_called()
            self.assertEqual(ct.sha(src),ct.sha(dst))
            with self.assertRaises(FileExistsError):copy_evidence(src,dst)

    def test_prior_failed_allocation_is_charged_and_validated(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'approval.json'
            row=dict(job='301159',gpu=True,seconds=45,state='FAILED')
            ct.json_write(p,dict(prior_allocations=[row]))
            self.assertEqual(prior_costs(p),([row],45,0))
            for invalid in ([row,row],[dict(row,seconds=-1)],[dict(row,state='RUNNING')]):
                with patch.object(ct,'json_read',return_value=dict(prior_allocations=invalid)):
                    with self.assertRaises(RuntimeError):prior_costs(p)


if __name__=='__main__':unittest.main()
