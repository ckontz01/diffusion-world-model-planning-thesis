"""Paper-equation binary-utility specialization of PC-RACP (not ordinary LCB).

Utility u(a,y)=y, 0<p(a)<1. Exact piecewise optimization replaces a beta grid.
Eq.3.3: only (t=max p,theta=1) and (t=1,theta=0) can maximize.
Policy learning Eq.4.1 fixes a(x) BEFORE calibration. Eq.4.2/4.3 or exact
finite-label Eq.4.4/4.5 then calibrates sets without changing a(x).
Ties choose larger t, then baseline/lowest slot. No population optimality claim
under binary ties. Known propensities are required, never estimated or clipped.
"""
from bisect import bisect_left
import math
from controls import probabilities


def curve(p):
    probabilities(p)
    if any(not 0 < v < 1 for v in p):
        raise ValueError('Binary specialization requires interior probabilities')
    m = max(p)
    return m, 1./(1.-m), p.index(m)


def g(p, beta):
    m, crossing, a = curve(p)
    return (1., 0., 0) if beta >= crossing else (m, 1., a)


class BinaryPCRACP:
    def __init__(self, learn_predictions, alpha=.05):
        if not learn_predictions or not 0 < alpha < 1: raise ValueError('Learn split/alpha')
        self.alpha = alpha
        curves = [curve(p) for p in learn_predictions]
        coverage = sum(c[0] for c in curves)
        self.beta_hat = 0.
        for m, crossing, _ in sorted(curves, key=lambda c: c[1]):
            if coverage/len(curves) >= 1-alpha: break
            coverage += 1-m; self.beta_hat = crossing
        self.learn_count = len(curves)
        self._calibrated = False

    def action(self, p): return g(p, self.beta_hat)[2]

    def calibrate(self, records, *, complete_branch=False):
        """records: (prediction, outcomes, logged_slot, known_propensity_vector).

        Complete-branch adaptation uses the fixed-policy branch for EVERY source,
        weight=1, not eight independent observations. Separate labeled variant.
        """
        self.variant = 'complete-branch-adaptation' if complete_branch else 'known-logged-paper-equations'
        self.complete_branch = complete_branch
        success_weight, failures = 0., []
        used = 0
        for p, outcomes, logged, propensity in records:
            chosen = self.action(p)
            if not complete_branch and logged != chosen: continue
            if complete_branch:
                weight = 1.
            else:
                probabilities(propensity)
                if abs(sum(propensity)-1) > 1e-12 or any(v <= 0 for v in propensity):
                    raise ValueError('Known positive behavior probabilities required')
                weight = 1/propensity[logged]
            y = outcomes[chosen]
            if y not in (0,1): raise ValueError('Binary utility required')
            used += 1
            if y: success_weight += weight
            else: failures.append((curve(p)[1], weight))
        self.used = used
        self.total = success_weight + sum(w for _, w in failures)
        self.breakpoints = [0.]
        self.numerators = [success_weight]
        for beta, weight in sorted(failures):
            if beta == self.breakpoints[-1]:
                self.numerators[-1] += weight
            else:
                self.breakpoints.append(beta); self.numerators.append(self.numerators[-1]+weight)
        self._calibrated = True
        return self

    def _beta(self, wtest, test_y=None, test_crossing=None):
        target = (1-self.alpha)*(self.total+wtest)
        # Exact finite-label full conformal: test outcome contributes at its
        # nested-score breakpoint; never use the actual unknown outcome.
        if test_y is not None:
            events = dict(zip(self.breakpoints, self.numerators))
            events.setdefault(test_crossing, self.numerators[max(0, bisect_left(self.breakpoints, test_crossing)-1)])
            for beta in sorted(events):
                j = bisect_left(self.breakpoints, beta)
                if j == len(self.breakpoints) or self.breakpoints[j] != beta: j -= 1
                numerator = self.numerators[j] + (wtest if test_y or beta >= test_crossing else 0.)
                if numerator + 1e-12 >= target: return beta
            return math.inf
        j = bisect_left(self.numerators, target-1e-12)
        return self.breakpoints[j] if j < len(self.breakpoints) else math.inf

    def predict(self, p, propensity=(.125,)*8, *, full=True):
        if not self._calibrated: raise RuntimeError('Calibrate after learning')
        chosen = self.action(p)
        probabilities(propensity)
        if any(v <= 0 for v in propensity) or abs(sum(propensity)-1) > 1e-12:
            raise ValueError('Invalid behavior probabilities')
        wtest = 1. if self.complete_branch else 1/propensity[chosen]
        crossing = curve(p)[1]
        if full:
            betas = [self._beta(wtest, y, crossing) for y in (0,1)]
            chosen_set = tuple(y for y, b in zip((0,1),betas) if y >= (0 if b >= crossing else 1))
            other_beta = max(betas)
        else:
            other_beta = self._beta(wtest)
            chosen_set = (0,1) if other_beta >= crossing else (1,)
        t = g(p, other_beta)[0]
        # Eq.4.3/4.4 raises the learned action's certificate to theta.
        # Preserve the learned action among max-min ties (NOT a new argmax).
        sets = tuple(chosen_set if a == chosen else ((1,) if t <= p[a] else (0,1)) for a in range(8))
        if min(sets[chosen]) < max(map(min, sets)):
            raise AssertionError('Policy-preserving set construction failed')
        return dict(action=chosen, sets=sets, certificate=min(chosen_set),
                    beta_hat=self.beta_hat, calibration_sources=self.used,
                    variant=self.variant, exact_finite_label=full)
