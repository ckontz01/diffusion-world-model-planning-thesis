"""New artificial checks only; no previous A2/V1 suite, models or simulators."""
import hashlib
from pathlib import Path
import tempfile
import unittest
import warnings
import zipfile
from .capacity import reconcile
from .prepare import pickle_inventory


class PreparationChecks(unittest.TestCase):
    def inventory(self, raw, duplicate=False, bad_hash=False):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'artificial.zip'
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', UserWarning)
                with zipfile.ZipFile(path, 'w') as archive:
                    archive.writestr('artificial/data.pkl', raw)
                    if duplicate: archive.writestr('artificial/data.pkl', raw)
            encoded = path.read_bytes()
            return pickle_inventory(path, dict(name='artificial', bytes=len(encoded),
                sha256='0'*64 if bad_hash else hashlib.sha256(encoded).hexdigest()))

    def test_inventory_does_not_import_global(self):
        # A nonexistent global is inventoried, never imported/deserialized.
        row = self.inventory(b'cwm_nonexistent_module\nNeverExecute\n.')
        self.assertEqual(row['global_references'], ['wm_nonexistent_module NeverExecute'])
        self.assertFalse(row['deserialized'])

    def test_stack_global_is_reported_unresolved(self):
        row = self.inventory(b'\x80\x04\x8c\x01m\x8c\x01n\x93.')
        self.assertEqual(row['unresolved_stack_global_count'], 1)

    def test_changed_hash_rejected(self):
        with self.assertRaises(ValueError): self.inventory(b'N.', bad_hash=True)

    def test_duplicate_member_rejected(self):
        with self.assertRaises(ValueError): self.inventory(b'N.', duplicate=True)

    def test_large_pickle_metadata_rejected(self):
        with self.assertRaises(ValueError): self.inventory(b'N.' + b'0'*2_000_000)

    def test_malformed_pickle_rejected(self):
        with self.assertRaises(ValueError): self.inventory(b'\xff')

    def test_capacity_no_pc_double_charge(self):
        r = reconcile(11_555_606_036, 4_000_000_000, 410_653_018,
                      3_139_002_368, 2_058_354_358, 1_512_400_813, 4_862_451_499)
        self.assertEqual(r['cluster_runtime_bytes'], 5_197_356_726)
        self.assertEqual(r['candidate_live_reservation_bytes'], 12_342_309_744)
        self.assertEqual(r['retained_preparation_full_future_bytes'], 2_374_852_312)
        self.assertEqual(r['topology_using_candidate_live_reservation_bytes'], 42_717_162_056)
        self.assertEqual(r['proposed_full_topology_bytes'], 43_374_852_312)
        self.assertFalse(r['current_caps_fit'])

    def test_invalid_byte_counts_rejected(self):
        with self.assertRaises(ValueError): reconcile(True, 0, 0, 0, 0, 0, 0)
        with self.assertRaises(ValueError): reconcile(10, 11, 0, 0, 0, 0, 11)
        with self.assertRaises(ValueError): reconcile(10, 8, 3, 0, 0, 0, 8)


if __name__ == '__main__': unittest.main()
