"""Artificial archive-only checks; no model, data, GPU or scheduler calls."""
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from finalize import sha, verify_archive, safe_name


class PreservationTests(unittest.TestCase):
    def build(self, directory, names=('source/fixture.txt', 'run/job/SEAL.json')):
        archive_path = Path(directory)/'fixture.tar'
        files = []
        with tarfile.open(archive_path, 'w') as archive:
            for name in names:
                body = ('artificial '+name).encode()
                import hashlib
                files.append(dict(path=name, bytes=len(body), sha256=hashlib.sha256(body).hexdigest()))
                member = tarfile.TarInfo(name)
                member.size = len(body)
                archive.addfile(member, io.BytesIO(body))
        return archive_path, dict(archive_bytes=archive_path.stat().st_size,
                                 archive_sha256=sha(archive_path), archive_members=len(files), files=files)

    def test_complete_whole_and_members(self):
        with tempfile.TemporaryDirectory() as directory:
            path, request = self.build(directory)
            result = verify_archive(path, request)
            self.assertTrue(result['whole_archive_verified'] and result['every_member_verified'])

    def test_truncated_whole_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path, request = self.build(directory)
            with path.open('r+b') as stream:
                stream.truncate(100)
            with self.assertRaises(RuntimeError):
                verify_archive(path, request)

    def test_tampered_whole_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path, request = self.build(directory)
            with path.open('r+b') as stream:
                stream.seek(600)
                stream.write(b'altered')
            with self.assertRaises(RuntimeError):
                verify_archive(path, request)

    def test_wrong_member_digest_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path, request = self.build(directory)
            request['files'][0]['sha256'] = '0'*64
            with self.assertRaises(RuntimeError):
                verify_archive(path, request)

    def test_missing_member_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path, request = self.build(directory)
            request['files'].pop()
            with self.assertRaises(RuntimeError):
                verify_archive(path, request)

    def test_duplicate_members_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path, request = self.build(directory, ('source/a', 'source/a'))
            with self.assertRaises(RuntimeError):
                verify_archive(path, request)

    def test_unsafe_paths_rejected(self):
        for name in ('../secret', '/absolute', 'source/../secret', 'source\\secret', './source/a', ''):
            with self.subTest(name=name), self.assertRaises(RuntimeError):
                safe_name(name)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(PreservationTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    receipt = dict(artificial_preservation_only=True, tests_run=result.testsRun,
                   failures=len(result.failures), errors=len(result.errors),
                   research_data_opened=False, gpu_allocations=0)
    with (Path(__file__).parent/'PRESERVATION-TESTS.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
    raise SystemExit(0 if result.wasSuccessful() else 1)
