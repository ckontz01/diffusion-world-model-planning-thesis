"""Synthetic only: no real feature, label, checkpoint, simulator or GPU reads."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]/'cluster/prometheus'))
spec = importlib.util.spec_from_file_location('objective_capacity_study', HERE/'study.py')
s = importlib.util.module_from_spec(spec); spec.loader.exec_module(s)
import candidate_value_learning as c
from candidate_value_models import normalize_fit, transform
torch.set_num_threads(1)


def bank(ref=1, h=75, t=0, base=2):
    rng = np.random.default_rng(ref*100+h+t)
    ids = [19, 7, 41, 3, 24, 12, 61, 2]
    return dict(reference=ref, horizon=h, anchor=t, slot=0, base=base, ids=ids,
                continuation_index=ids[base], x=rng.normal(size=(8, 619)).astype(np.float32),
                y=np.array([[1, 0], [0, 0], [0, 1], [1, 1], [0, 1], [0, 0], [1, 0], [0, 1]], np.int64))


class StudyTests(unittest.TestCase):
    def test_paired_same_draw_labels_and_zeros(self):
        b = bank(); x, bx, y, w, keys = s.table([b], True)
        self.assertEqual(len(y), 14)
        self.assertNotIn(b['ids'][b['base']], [k[3] for k in keys])
        for n, k in enumerate(keys):
            i, d = b['ids'].index(k[3]), k[4]
            self.assertEqual(y[n], b['y'][i, d]-b['y'][b['base'], d])
            np.testing.assert_array_equal(x[n], b['x'][i])
            np.testing.assert_array_equal(bx[n], b['x'][b['base']])
        self.assertGreater(int(np.sum(y == 0)), 0)
        self.assertEqual(set(y), {-1., 0., 1.})
        np.testing.assert_allclose(w, np.full(14, 1/14))

    def test_absolute_retains_both_binary_draws(self):
        b = bank(); _, _, y, w, keys = s.table([b])
        np.testing.assert_array_equal(y, b['y'].reshape(-1))
        self.assertEqual(len(keys), 16)
        np.testing.assert_allclose(w, 1/16)

    def test_baseline_identity_fails_closed(self):
        b = bank(); b['continuation_index'] = 999
        with self.assertRaises(AssertionError): s.table([b], True)

    def test_invalid_labels_not_rounded(self):
        b = bank(); b['y'] = b['y'].astype(float); b['y'][0, 0] = .5
        with self.assertRaises(AssertionError): s.table([b])

    def test_hierarchical_normalization_both_objectives(self):
        bs = [bank(1, 75), bank(1, 75, 30), bank(1, 150), bank(2, 75), bank(2, 150)]
        for relative in (False, True):
            _, _, _, w, keys = s.table(bs, relative)
            self.assertAlmostEqual(float(w.sum()), 1., places=6)
            for r in (1, 2):
                self.assertAlmostEqual(sum(float(v) for k, v in zip(keys, w) if k[0] == r), .5, places=6)
                for h in (75, 150):
                    self.assertAlmostEqual(sum(float(v) for k, v in zip(keys, w) if k[:2] == (r, h)), .25, places=6)

    def test_new_and_historical_exact_ties(self):
        ids = [9, 1, 4]; p = [1., 1., 1.]
        self.assertEqual(s.choose(p, ids, baseline=0), 0)
        self.assertEqual(s.choose(p, ids), 1)
        self.assertEqual(s.choose([0., 1., 1.], ids, baseline=0), 1)
        self.assertEqual(s.choose([1., np.nextafter(1., 2.), 0.], ids, baseline=0), 1)

    def test_identifier_only_folds(self):
        refs = c.allocation()['train']; fs = s.folds(refs)
        self.assertEqual(fs, s.folds(list(reversed(refs))))
        self.assertEqual(sorted(sum(fs, [])), sorted(refs))
        for i, f in enumerate(fs):
            self.assertEqual(len(f), 24)
            fitting = set(refs)-set(f)
            self.assertEqual(len(fitting), 72)
            self.assertFalse(fitting & set(f))
            self.assertTrue(all(not set(f) & set(g) for j, g in enumerate(fs) if j != i))

    def test_scaler_is_training_only_and_common(self):
        train = [bank(1), bank(2)]
        a = s.fit_preprocessing(train, [1, 2])
        held = bank(3); held['x'] *= 1e6
        b = s.fit_preprocessing(train, [1, 2])
        for x, y in zip(a, b): np.testing.assert_array_equal(x, y)
        with self.assertRaises(AssertionError): s.fit_preprocessing(train+[held], [1, 2])
        x, _, _, w, _ = s.table(train)
        for z, expected in zip(a, normalize_fit(x, w)): np.testing.assert_array_equal(z, expected)

    def test_parameter_counts(self):
        self.assertEqual(sum(p.numel() for p in s.Model(False).parameters()), 87681)
        self.assertEqual(sum(p.numel() for p in s.Model(True).parameters()), 19873)

    def test_relative_baseline_zero_and_ensemble_arithmetic(self):
        b = bank(); models = [s.Model(True) for _ in range(3)]
        norm = (np.zeros(619, np.float32), np.ones(619, np.float32))
        single, ensemble = s.scores(models, 'compact_relative', b['x'], b['base'], *norm)
        np.testing.assert_array_equal(single[:, b['base']], 0.)
        self.assertEqual(ensemble[b['base']], 0.)
        np.testing.assert_allclose(ensemble, single.mean(0), rtol=1e-6, atol=1e-7)
        _, m = s.metrics(ensemble, b, False, True)
        self.assertIsNone(m['brier']); self.assertIsNone(m['log_loss'])

    def test_original_bce_optimizer_matches_original_on_synthetic_data(self):
        bs = [bank(r) for r in c.allocation()['train'][:24]]
        norm = s.fit_preprocessing(bs, [b['reference'] for b in bs])
        x, _, y, _, keys = s.table(bs)
        original = c.fit(transform(x, *norm), y, keys, model_seed=8201, epochs=1)
        new, receipt = s.fit(bs, 'original_bce', 8201, *norm, epochs=1)
        self.assertEqual(receipt['optimizer_steps'], 2)
        for k, v in original.state_dict().items():
            torch.testing.assert_close(v, new.state_dict()[k], rtol=0, atol=0)

    def test_relative_optimizer_is_finite_on_zeros(self):
        b = bank(); b['y'][:] = 0
        norm = s.fit_preprocessing([b], [1])
        model, receipt = s.fit([b], 'compact_relative', 8202, *norm, epochs=1)
        self.assertEqual(receipt['zero_targets'], 14)
        self.assertTrue(all(not p.requires_grad and torch.isfinite(p).all() for p in model.parameters()))

    def test_gain_loss_and_reducer(self):
        b = bank(); p = np.arange(8, dtype=float)
        _, m = s.metrics(p, b, False, True)
        self.assertEqual(m['gain']-m['loss'], m['effect'])
        rows = [dict(reference=1, horizon=75, metrics={'effect': 1.}),
                dict(reference=1, horizon=75, metrics={'effect': 1.}),
                dict(reference=1, horizon=150, metrics={'effect': 0.}),
                dict(reference=2, horizon=75, metrics={'effect': 0.}),
                dict(reference=2, horizon=150, metrics={'effect': 0.})]
        self.assertEqual(s.reduce_rows(rows)['means']['effect'], .25)

    def test_training_only_recommendation_ties_and_none(self):
        def report(values): return {'models': {k: {'means': {'effect': v}} for k, v in zip(s.CONFIGS, values)}}
        self.assertEqual(s.recommend(report([.1]*4))['configuration'], 'compact_bce')
        self.assertIsNone(s.recommend(report([0, -.1, -.2, 0]))['configuration'])
        self.assertFalse(s.recommend(report([.1, 0, .2, .3]))['validation_used'])

    def test_output_exclusive_and_size_reservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = s.Output(Path(tmp)/'results')
            out.json('one.json', {'a': 1})
            with self.assertRaises(FileExistsError): out.json('one.json', {'a': 2})
            out.bytes = s.ARTIFACT_CAP
            with self.assertRaises(AssertionError): out.json('two.json', {})

    def test_validation_requires_frozen_models_before_reader(self):
        with patch.object(s, 'RUN', Path('/nonexistent')):
            with self.assertRaises(AssertionError): s.read_saved('validation', [], None)

    def test_complete_workload_reservation_and_timeout(self):
        with patch.object(s.signal, 'signal'), patch.object(s.signal, 'setitimer'):
            budget = s.Budget()
            self.assertEqual(s.FIT_COUNT*s.FIT_CAP+s.OVERHEAD_CAP, 7100)
            budget.started -= 1101
            with self.assertRaises(AssertionError): budget.check()
        with self.assertRaises(TimeoutError): s.Budget.timeout()


if __name__ == '__main__': unittest.main()
