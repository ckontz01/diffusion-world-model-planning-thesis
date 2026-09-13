"""Synthetic checks; these are not new scientific evaluation episodes."""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np

import diffusion_bottleneck as d
import diffusion_bottleneck_traces as r


class TensorTests(unittest.TestCase):
    def setUp(self):
        self.x = np.zeros((8, 2, 3, 6), dtype=np.uint8)

    def test_valid_shape(self):
        self.assertEqual(d.validate_tensor(self.x).shape, (8, 2, 3, 6))

    def test_bad_shape(self):
        with self.assertRaises(d.IntegrityError):
            d.validate_tensor(np.zeros((8, 3, 2, 6)))

    def test_wrong_n(self):
        with self.assertRaises(d.IntegrityError):
            d.validate_tensor(self.x, 9)

    def test_single_reference(self):
        with self.assertRaises(d.IntegrityError):
            d.validate_tensor(self.x[:1])

    def test_missing(self):
        x = self.x.astype(float); x[0, 0, 0, 0] = np.nan
        with self.assertRaises(d.IntegrityError):
            d.validate_tensor(x)

    def test_nonbinary(self):
        self.x[0, 0, 0, 0] = 2
        with self.assertRaises(d.IntegrityError):
            d.validate_tensor(self.x)

    def test_object_array(self):
        with self.assertRaises(d.IntegrityError):
            d.validate_tensor(self.x.astype(object))

    def test_unsigned_subtraction(self):
        self.x[..., 1] = 1
        names, metrics = d.cluster_metrics(self.x)
        self.assertEqual(metrics[:, names.index('vad_continuation-minus-vad_greedy_300/overall')].mean(), -1)

    def test_horizon_interaction(self):
        self.x[:, 1, :, 0] = 1
        names, values = d.cluster_metrics(self.x)
        self.assertTrue(np.all(values[:, names.index('vad_continuation-minus-vad_greedy_300/h150_minus_h75')] == 1))

    def test_reference_cluster_se_not_seed_trial_se(self):
        self.x[:4, :, :, 0] = 1
        result = d.outcome_diagnostics(self.x)
        row = result['metrics']['vad_continuation-minus-vad_greedy_300/overall']
        expected = np.std([1] * 4 + [0] * 4, ddof=1) / np.sqrt(8) * 100
        self.assertAlmostEqual(row['reference_cluster_se_pp'], expected)

    def test_pair_four_categories(self):
        result = d.paired_counts(np.array([1, 1, 0, 0]), np.array([1, 0, 1, 0]))
        for key in ('both_success', 'left_only', 'right_only', 'both_failure'):
            self.assertEqual(result[key], 1)
        self.assertEqual(result['nondeployable_whole_planner_oracle_success'], .75)

    def test_pair_wrong_shape(self):
        with self.assertRaises(d.IntegrityError):
            d.paired_counts(np.zeros(3), np.zeros(4))

    def test_all_pairs_covered(self):
        result = d.outcome_diagnostics(self.x)
        self.assertEqual(len(result['method_pairs']), 15)
        self.assertEqual(result['paired_measurements'], self.x.size)
        for pair in result['method_pairs'].values():
            self.assertEqual(pair['reference_net_ties'], 8)

    def test_fixed_seed_rates_shape(self):
        self.x[..., 1, 0] = 1
        result = d.outcome_diagnostics(self.x)
        self.assertEqual(result['per_fixed_block_success']['vad_continuation'], [[0, 1, 0], [0, 1, 0]])

    def test_bootstrap_repeatability(self):
        self.x[:4, :, :, 0] = 1
        _, values = d.cluster_metrics(self.x)
        self.assertEqual(d.cluster_intervals(values, 100, 2), d.cluster_intervals(values, 100, 2))

    def test_bootstrap_constant_column(self):
        result = d.cluster_intervals(np.ones((8, 1)), 100, 2)
        self.assertEqual(result['lower_pp'], [100])
        self.assertEqual(result['upper_pp'], [100])
        self.assertFalse(result['sequentially_valid_confirmation'])

    def test_bootstrap_invalid_count(self):
        with self.assertRaises(d.IntegrityError):
            d.cluster_intervals(np.ones((8, 1)), -1, 2)

    def test_bootstrap_output_not_primary(self):
        result = d.outcome_diagnostics(self.x, 100)
        self.assertIn('exploratory', result['bootstrap']['method'])
        self.assertNotIn('reject_this_look', result['metrics'])


class TrajectoryTests(unittest.TestCase):
    def setUp(self):
        self.goal = np.zeros(7)
        self.states = np.zeros((3, 7))

    def test_excludes_initial_success(self):
        self.states[1:, 0] = 25
        self.assertFalse(d.trajectory_diagnostics(self.states, self.goal)['success'])

    def test_success_after_action(self):
        self.states[0, 0] = 25
        self.assertEqual(d.trajectory_diagnostics(self.states, self.goal)['first_success_step'], 1)

    def test_joint_not_individual_position_threshold(self):
        self.states[1:, 0] = 15; self.states[1:, 2] = 15
        result = d.trajectory_diagnostics(self.states, self.goal)
        self.assertFalse(result['success'])
        self.assertTrue(result['ever_individual_positions_both_within_20_but_joint_outside'])

    def test_position_boundary_is_strict(self):
        self.states[1:, 0] = 20
        self.assertFalse(d.trajectory_diagnostics(self.states, self.goal)['success'])

    def test_angle_boundary_is_strict(self):
        self.states[1:, 4] = np.pi / 9
        self.assertFalse(d.trajectory_diagnostics(self.states, self.goal)['success'])

    def test_angle_wrap(self):
        self.goal[4] = 2 * np.pi - .01
        self.states[:, 4] = .01
        self.assertTrue(d.trajectory_diagnostics(self.states, self.goal)['success'])

    def test_noncanonical_angle_rejected(self):
        self.states[1, 4] = 2 * np.pi + .1
        with self.assertRaises(d.IntegrityError):
            d.trajectory_diagnostics(self.states, self.goal)

    def test_no_separate_minima_success(self):
        self.states[1, 4] = 1
        self.states[2, 0] = 25
        result = d.trajectory_diagnostics(self.states, self.goal)
        self.assertFalse(result['success'])
        self.assertGreater(result['closest_joint_margin'], 1)

    def test_block_component_is_only_supplement(self):
        self.states[1:, 0] = 40
        result = d.trajectory_diagnostics(self.states, self.goal)
        self.assertTrue(result['ever_block_pose_within_component_thresholds'])
        self.assertEqual(result['terminal_category'], 'joint_position_only_miss')
        self.assertFalse(result['success'])

    def test_empty_action_trace(self):
        result = d.trajectory_diagnostics(self.states[:1], self.goal)
        self.assertEqual(result['terminal_category'], 'no_action')
        self.assertFalse(result['success'])

    def test_nonfinite_state_rejected(self):
        self.states[2, 6] = np.inf
        with self.assertRaises(d.IntegrityError):
            d.trajectory_diagnostics(self.states, self.goal)

    def test_wrong_goal_shape(self):
        with self.assertRaises(d.IntegrityError):
            d.trajectory_diagnostics(self.states, self.goal[:5])

    def test_both_terminal_failures(self):
        self.states[1:, 0] = 25; self.states[1:, 4] = 1
        self.assertEqual(d.trajectory_diagnostics(self.states, self.goal)['terminal_category'], 'both_miss')


class IntegrityTests(unittest.TestCase):
    def test_sha_detects_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'file'; path.write_text('before')
            digest = d.sha256(path); path.write_text('after')
            with self.assertRaises(d.IntegrityError): d.require_sha(path, digest)

    def test_reject_absolute_child(self):
        with self.assertRaises(d.IntegrityError): d.checked_child(Path('/tmp'), '/etc/passwd')

    def test_reject_parent_child(self):
        with self.assertRaises(d.IntegrityError): d.checked_child(Path('/tmp'), '../other')

    def test_reject_windows_separator(self):
        with self.assertRaises(d.IntegrityError): d.checked_child(Path('/tmp'), '..\\other')

    def test_reject_symlink_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'input'; root.mkdir()
            (root / 'link').symlink_to(Path(tmp) / 'outside')
            with self.assertRaises(d.IntegrityError): d.checked_child(root, 'link')

    def test_allow_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(d.checked_child(Path(tmp), 'results/file.json'), Path(tmp) / 'results/file.json')

    def test_output_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'out.json'; path.write_text('sentinel')
            with self.assertRaises(FileExistsError): d.write_report(path, {}, ())
            self.assertEqual(path.read_text(), 'sentinel')

    def test_output_not_inside_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(d.IntegrityError): d.write_report(Path(tmp) / 'out.json', {}, (Path(tmp),))

    def test_reject_json_nan(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'bad.json'; path.write_text('{"x": NaN}')
            with self.assertRaises(d.IntegrityError): d.read_json(path)

    def test_registry_only_exposed_first_look(self):
        tasks = r.expected_tasks()
        self.assertEqual(len(tasks), 450)
        self.assertEqual(tasks[-1], dict(task=449, arm='sage', seed=7203, begin=1536, end=1600))
        coverage = {}
        for task in tasks:
            key = (task['arm'], task['seed'])
            coverage.setdefault(key, []).extend(range(task['begin'], task['end']))
        self.assertEqual(len(coverage), 18)
        self.assertTrue(all(v == list(range(1600)) for v in coverage.values()))

    def test_completeness_barrier_does_not_open_result_json(self):
        tasks = r.expected_tasks()
        def fake_read(path):
            if path.name == 'INPUT-LOCK.json': return {'config_sha256': 'a'*64, 'registry_sha256': 'b'*64, 'source_manifest_sha256': 'c'*64}
            if path.name == 'CONFIG.json': return {'arms': list(d.ARMS), 'training_seed_blocks': list(d.SEEDS), 'horizons': [75, 150]}
            if path.name == 'REGISTRY.json': return {'stages': [tasks, 'MUST_NOT_READ_PAYLOADS', 'MUST_NOT_READ_PAYLOADS']}
            if path.name == 'DONE.json':
                index = int(path.parent.name.split('-')[1])
                return {'task': tasks[index], 'config_sha256': 'a'*64, 'source_manifest_sha256': 'c'*64, 'result_sha256': 'd'*64}
            raise AssertionError('Unexpected payload read: ' + str(path))
        with mock.patch.object(r, 'read_json', side_effect=fake_read), mock.patch.object(r, 'require_sha'):
            files, _ = r.sealed_stage(Path('/synthetic'))
        self.assertEqual(len(files), 450)

    def test_missing_done_blocks_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(r, 'require_sha'):
                with self.assertRaises(OSError): r.sealed_stage(Path(tmp))

    def test_cli_summary_refuses_bootstrap(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stderr(io.StringIO()):
            code = d.main(['--summary', str(Path(tmp)/'absent'), '--out', str(Path(tmp)/'out'), '--bootstrap', '100'])
            self.assertEqual(code, 2)
            self.assertFalse((Path(tmp)/'out').exists())

    def test_cli_bad_archive_emits_no_result(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stderr(io.StringIO()):
            out = Path(tmp) / 'out'
            code = d.main(['--archive', str(Path(tmp) / 'absent'), '--out', str(out)])
            self.assertEqual(code, 2)
            self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
