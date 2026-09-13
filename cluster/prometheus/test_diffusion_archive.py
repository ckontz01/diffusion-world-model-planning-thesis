import hashlib
import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import archive_diffusion_bottleneck_backup as a

class ArchiveTests(unittest.TestCase):
    def fixture(self,folder,corrupt=False,extra=False):
        payload=b'opaque, not JSON or NPZ'
        seal=hashlib.sha256(payload).hexdigest().encode()+b'  RESULT.json\n'
        path=Path(folder)/'backup.tar'
        expected={'stage-0/task-0000/results/RESULT.json':hashlib.sha256(payload).hexdigest(),
                  'stage-0/task-0000/results/sha256.txt':hashlib.sha256(seal).hexdigest()}
        with tarfile.open(path,'w') as tar:
            for name,content in [('stage-0/task-0000/results/RESULT.json',b'changed' if corrupt else payload),
                                 ('stage-0/task-0000/results/sha256.txt',seal)]+([('../escape',payload)] if extra else []):
                info=tarfile.TarInfo(name);info.size=len(content);tar.addfile(info,io.BytesIO(content))
        return path,expected
    def test_opaque_member_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            path,expected=self.fixture(tmp)
            with patch.object(a,'inventory',return_value=expected):self.assertTrue(a.verify({},path)['all_passed'])
    def test_corrupt_payload_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path,expected=self.fixture(tmp,corrupt=True)
            with patch.object(a,'inventory',return_value=expected),self.assertRaises(ValueError):a.verify({},path)
    def test_extra_member_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path,expected=self.fixture(tmp,extra=True)
            with patch.object(a,'inventory',return_value=expected),self.assertRaises(ValueError):a.verify({},path)

if __name__=='__main__':unittest.main()
