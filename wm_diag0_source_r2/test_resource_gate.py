import unittest
from .resource_gate import reservation,require_within_original_limits


class ResourceGate(unittest.TestCase):
    def test_failed_source_requires_more_than_existing_physical_maxima(self):
        r={'failed_physical_work':{'controller_actions':44,'world_resets':1,'Reacher_dm_steps':88}}
        rows=reservation(r)
        self.assertEqual(rows['all_controller_steps_max']['charged_failed_plus_full_future'],386924)
        self.assertEqual(rows['world_resets_max']['charged_failed_plus_full_future'],6401)
        self.assertEqual(rows['source_frames_max']['charged_failed_plus_full_future'],5445)
        self.assertEqual(rows['reacher_dm_steps_max']['charged_failed_plus_full_future'],386968)
        with self.assertRaisesRegex(RuntimeError,'NOT AUTHORIZED'):require_within_original_limits(r)

    def test_unknown_failed_frame_count_cannot_be_assumed_zero(self):
        with self.assertRaises(ValueError):
            reservation({'failed_physical_work':{'controller_actions':43,'world_resets':1,'Reacher_dm_steps':86}})


if __name__=='__main__':unittest.main()
