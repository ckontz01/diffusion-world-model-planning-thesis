from fractions import Fraction
import itertools
import unittest
from paired_improvement import PairedImprovement, THRESHOLDS, CRITICAL, upper_tail

P=(.1,.9)+(.05,)*6


def data(g, l, ties=0):
    ys=[(0,1)+(0,)*6]*g+[(1,0)+(0,)*6]*l+[(1,1)+(0,)*6]*ties
    return [(str(i),P,y) for i,y in enumerate(ys)]


class Tests(unittest.TestCase):
    def test_small_sample_exhaustive_enumeration(self):
        for n in range(11):
            draws=list(itertools.product((0,1),repeat=n))
            for g in range(n+1):
                expected=Fraction(sum(sum(v)>=g for v in draws),2**n)
                self.assertEqual(upper_tail(g,n-g),expected)

    def test_all_ties(self):
        self.assertEqual(upper_tail(0,0),1)
        c=PairedImprovement.calibrate(data(0,0,100))
        self.assertFalse(c.accepted);self.assertIsNone(c.threshold);self.assertEqual(c.choose(P),0)
        self.assertTrue(all(t['p_value']==1 for t in c.tests))

    def test_gains_only(self):
        for g in range(1,13):self.assertEqual(upper_tail(g,0),Fraction(1,2**g))
        c=PairedImprovement.calibrate(data(7,0,93))
        self.assertEqual(c.accepted,THRESHOLDS);self.assertEqual(c.threshold,0)
        self.assertEqual(c.choose(P),1)

    def test_losses_only(self):
        for l in range(1,13):self.assertEqual(upper_tail(0,l),1)
        self.assertFalse(PairedImprovement.calibrate(data(0,100)).accepted)

    def test_family_correction_not_nominal_point05(self):
        self.assertLess(upper_tail(6,0),Fraction(5,100))
        self.assertGreater(upper_tail(6,0),CRITICAL)
        self.assertFalse(PairedImprovement.calibrate(data(6,0)).accepted)
        self.assertTrue(PairedImprovement.calibrate(data(7,0)).accepted)

    def test_denominator_all_sources(self):
        c=PairedImprovement.calibrate(data(7,1,92))
        for t in c.tests:
            self.assertEqual(t['sources'],100);self.assertEqual(t['discordant'],8)
            self.assertEqual(t['sampled_net_difference'],.06)

    def test_pvalue_orientation(self):
        self.assertEqual(upper_tail(3,1),Fraction(5,16))
        self.assertEqual(upper_tail(1,3),Fraction(15,16))

    def test_fixed_family_type_and_single_source_guard(self):
        for counts in ((-1,2),(1.5,2),(True,2)):
            with self.assertRaises(ValueError):upper_tail(*counts)
        with self.assertRaises(ValueError):PairedImprovement.calibrate([])
        with self.assertRaises(ValueError):PairedImprovement.calibrate(data(1,0)*2)
        with self.assertRaises(ValueError):PairedImprovement.calibrate([('a',P,(.5,)*8)])

    def test_boundary_threshold_and_prediction_ties(self):
        p=(.1,.3)+(.01,)*6
        rows=[(str(i),p,(0,1)+(0,)*6) for i in range(7)]
        c=PairedImprovement.calibrate(rows)
        self.assertEqual(c.accepted,(0.,.05,.1));self.assertEqual(c.threshold,0.)
        self.assertEqual(c.choose((.5,)*8),0)

    def test_analytic_shared_uniform_example(self):
        # Enumerate 1000 equally spaced U midpoints: exact probabilities for .1/.2.
        u=[Fraction(2*i+1,2000) for i in range(1000)]
        d=[int(x<Fraction(2,10))-int(x<Fraction(1,10)) for x in u]
        self.assertEqual(sum(d),100);self.assertEqual(d.count(0),900)
        self.assertEqual(Fraction(sum(d),len(d)),Fraction(1,10))
        # A positive lower bound for this discrete realized D covers only 10%.
        self.assertEqual(Fraction(sum(v>0 for v in d),len(d)),Fraction(1,10))


if __name__=='__main__':unittest.main(verbosity=2)
