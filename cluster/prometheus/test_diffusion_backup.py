"""Backup tests use synthetic bytes, not scientific trajectory fixtures."""
import json
from pathlib import Path
import tempfile
import unittest

import diffusion_bottleneck as d
import diffusion_bottleneck_traces as r
import verify_diffusion_backup as b


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.task = r.expected_tasks()[0]
        self.key = 'stage-0/task-0000'
        results = self.root / self.key / 'results'; results.mkdir(parents=True)
        names = ['RESULT.json'] + [f'episode-{i:05d}-h{h}.{ext}' for i in range(64) for h in (75, 150) for ext in ('json', 'npz')]
        for name in names: (results / name).write_bytes(b'synthetic opaque payload')
        (results / 'sha256.txt').write_text(''.join(d.sha256(results / name) + '  ' + name + '\n' for name in names))
        done = {'task': self.task, 'result_sha256': d.sha256(results / 'RESULT.json')}
        done_path = results.parent / 'DONE.json'; done_path.write_text(json.dumps(done))
        self.record = {'path': self.key, 'done_sha256': d.sha256(done_path), 'result_sha256': done['result_sha256']}
        (self.root / 'COMPLETED-SHARD-BACKUP.json').write_text(json.dumps({'study': b.STUDY, 'shards': {self.key: self.record}}))

    def tearDown(self): self.temp.cleanup()

    def test_rehashes_indexed_entry(self):
        result = b.recheck(self.root)
        self.assertEqual(result['rehashed_shards'], 1)
        self.assertEqual(result['errors'], {})
        self.assertFalse(result['complete_local_shard_copy'])
        self.assertFalse(result['complete_source_matched_backup'])
        self.assertEqual(len(result['missing_shards']), 449)

    def test_finds_corruption_despite_index(self):
        (self.root / self.key / 'results' / 'episode-00000-h75.npz').write_bytes(b'changed')
        result = b.recheck(self.root)
        self.assertIn(self.key, result['errors'])
        self.assertEqual(result['rehashed_shards'], 0)

    def test_missing_checksum_entry_is_not_valid(self):
        p = self.root / self.key / 'results' / 'sha256.txt'
        p.write_text('\n'.join(p.read_text().splitlines()[1:]) + '\n')
        self.assertIn(self.key, b.recheck(self.root)['errors'])

    def test_duplicate_checksum_entry_is_not_valid(self):
        p = self.root / self.key / 'results' / 'sha256.txt'
        p.write_text(p.read_text() + p.read_text().splitlines()[0] + '\n')
        self.assertIn(self.key, b.recheck(self.root)['errors'])

    def test_no_outcome_payload_parsing(self):
        # Payloads are deliberately non-JSON/non-NPZ: only their bytes are checked.
        self.assertEqual(b.recheck(self.root)['rehashed_shards'], 1)

    def test_read_only(self):
        before = {p.relative_to(self.root): d.sha256(p) for p in self.root.rglob('*') if p.is_file()}
        b.recheck(self.root)
        after = {p.relative_to(self.root): d.sha256(p) for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)


if __name__ == '__main__': unittest.main()
