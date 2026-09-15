import unittest
import numpy as np
import diagnose as d


class DiagnosisTests(unittest.TestCase):
    def test_original_index_ties(self):
        self.assertEqual(d.choose([1, 1, 0], [7, 2, 1]), 1)

    def test_concordance_ties_and_undefined(self):
        self.assertIsNone(d.concordance(np.ones(3), np.zeros(3)))
        self.assertEqual(d.concordance(np.ones(3), np.arange(3)), .5)
        self.assertEqual(d.concordance(np.arange(3), np.arange(3)), 1.)

    def test_cross_draw(self):
        y = np.array([[1, 0], [0, 1], [0, 0]])
        m = d.draw_metrics(y, [5, 2, 1], 2)
        self.assertEqual(m['cross0_effect'], 0.)
        self.assertEqual(m['cross1_effect'], 0.)
        self.assertEqual(m['candidate_disagreement'], 2/3)
        self.assertEqual(m['cross0_selection_success'], 1.)

    def test_final_tail_agreement_does_not_imply_no_candidate_variation(self):
        m = d.draw_metrics(np.array([[1, 1], [0, 0], [1, 1]]), [7, 3, 1], 1)
        self.assertEqual(m['candidate_disagreement'], 0.)
        self.assertEqual(m['cross0_maximum_ties'], 2)
        self.assertEqual(m['cross_mean_effect'], 1.)

    def test_equal_reference_horizon_anchor_weights(self):
        rows = [dict(reference=1, horizon=75, metrics={'x': 1., 'c': None}),
                dict(reference=1, horizon=75, metrics={'x': 1., 'c': None}),
                dict(reference=1, horizon=150, metrics={'x': 0., 'c': .8}),
                dict(reference=2, horizon=75, metrics={'x': 0., 'c': .2}),
                dict(reference=2, horizon=150, metrics={'x': 0., 'c': None})]
        r = d.reduce_rows(rows)
        self.assertEqual(r['means']['x'], .25)
        self.assertEqual(r['means']['c'], .5)
        self.assertEqual(r['defined_banks']['c'], 2)

    def test_binary_brier_not_majority(self):
        p = np.array([.5, .1]); y = np.array([[1, 0], [0, 0]])
        _, m = d.score_metrics(p, y, [3, 5], 1)
        self.assertAlmostEqual(m['brier'], .13)
        self.assertEqual(m['selected_success'], .5)

    def test_gain_loss_identity(self):
        p = np.array([.1, .8]); y = np.array([[1, 0], [0, 1]])
        scores = {k: p for k in d.LEARNED}
        m = d.decompose(p, y, [3, 5], 0, scores)
        self.assertEqual(m['gain'], .5); self.assertEqual(m['loss'], .5)
        self.assertEqual(m['empirical_advantage'], 0.)
        self.assertEqual(m['departure'], 1.)
        self.assertEqual(m['seed_winner_disagreement'], 0.)


if __name__ == '__main__':
    unittest.main()
