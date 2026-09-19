"""Synthetic final-backup namespace and member-verifier regression tests."""
import hashlib
import io
import tarfile
import tempfile
import unittest
from pathlib import Path, PureWindowsPath
from unittest.mock import patch

import lgp1_preserve as p


class FinalBackupPortability(unittest.TestCase):
    valid = ('/lustreFS/data/superworld/ckontzias/thesis/experiments/'
             'local-goal-proposals-20260918/run-b54a55b16bcb83a5/'
             'final-preservation/BACKUP-REQUEST.json')

    def test_native_namespace(self):
        p.validate_request(self.valid)

    def test_windows_host_posix_remote(self):
        with patch.object(p.c, 'ROOT', PureWindowsPath('/lustreFS/data/superworld/ckontzias/thesis')):
            p.validate_request(self.valid)

    def test_reject_other_namespace(self):
        for bad in [self.valid.replace('local-goal-proposals-20260918', 'other'),
                    self.valid.replace('b54a55b16bcb83a5', 'not-a-source'),
                    self.valid.replace('/final-preservation/', '/../final-preservation/'),
                    self.valid.replace('/', '\\'), self.valid+';echo bad',
                    self.valid.replace('/run-', '//run-'), self.valid.replace('BACKUP-REQUEST', 'REPORT')]:
            with self.subTest(path=bad), self.assertRaises(RuntimeError):
                p.validate_request(bad)

    def test_exact_archive_members_and_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'test.tar';payload=b'synthetic evidence'
            with tarfile.open(target,'x') as tar:
                info=tarfile.TarInfo('run/evidence.json');info.size=len(payload)
                tar.addfile(info,io.BytesIO(payload))
            expected={'run/evidence.json':dict(bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest())}
            self.assertEqual(p.verify_archive(target,expected)['files'],1)
            with self.assertRaises(RuntimeError):p.verify_archive(target,{})
            expected['run/evidence.json']['sha256']='0'*64
            with self.assertRaises(RuntimeError):p.verify_archive(target,expected)


if __name__=='__main__':unittest.main()
