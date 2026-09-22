"""Known final-checker constructions, with one independent bank per source."""
import math
from dataclasses import dataclass


def probabilities(p):
    if len(p) != 8 or any(not math.isfinite(x) or not 0 <= x <= 1 for x in p):
        raise ValueError('Expected eight finite probabilities')


def point(p):
    probabilities(p)
    return max(range(8), key=lambda i: (p[i], -i))  # baseline wins a tied maximum


def baseline(_): return 0


class TablePredictor:
    """Saturated ordinary predictor for the declared discrete artificial contexts.

    Fits only artificial fitting sources; no calibration or evaluation outcomes.
    Full-branch and logged versions have identical capacity, different label count.
    """
    def __init__(self, rows, logged=False):
        self.counts = {}
        self.fit_ids = frozenset(r['id'] for r in rows)
        if len(self.fit_ids) != len(rows): raise ValueError('Repeated fitting source')
        for r in rows:
            slots = [r['logged_action']] if logged else range(8)
            for a in slots:
                n, y = self.counts.get((r['context'], a), (0, 0))
                self.counts[r['context'], a] = n+1, y+r['outcomes'][a]

    def predict(self, context):
        return tuple((self.counts.get((context, a), (0, 0))[1]+1) /
                     (self.counts.get((context, a), (0, 0))[0]+2) for a in range(8))


def split_quantile(scores, alpha):
    if not 0 < alpha < 1 or any(not math.isfinite(x) for x in scores):
        raise ValueError('Invalid quantile inputs')
    rank = math.ceil((len(scores)+1)*(1-alpha))
    return sorted(scores)[rank-1] if rank <= len(scores) else math.inf


@dataclass(frozen=True)
class Simultaneous:
    q: float

    @classmethod
    def calibrate(cls, records, alpha):
        scores = []
        for p, y in records:
            probabilities(p)
            if len(y) != 8: raise ValueError('Outcome association mismatch')
            scores.append(max((p[i]-p[0])-(y[i]-y[0]) for i in range(1,8)))
        return cls(split_quantile(scores, alpha))

    def bounds(self, p):
        probabilities(p)
        return (0.,) + tuple(p[i]-p[0]-self.q for i in range(1,8))

    def choose(self, p):
        b = self.bounds(p)
        return max(range(8), key=lambda i: (b[i], -i))


def binomial_cdf(k, n, p):
    """Log-sum-exp exact binomial tail, not a Gaussian approximation."""
    if not 0 <= k <= n or not 0 < p < 1: raise ValueError('Invalid binomial inputs')
    terms = [math.lgamma(n+1)-math.lgamma(j+1)-math.lgamma(n-j+1)+
             j*math.log(p)+(n-j)*math.log1p(-p) for j in range(k+1)]
    top = max(terms)
    return min(1., math.exp(top)*sum(math.exp(t-top) for t in terms))


def threshold_rule(p, threshold):
    a = point(p)
    return a if a != 0 and p[a]-p[0] > threshold else 0


@dataclass(frozen=True)
class LearnThenTest:
    threshold: float
    tests: tuple
    accepted: tuple

    @classmethod
    def calibrate(cls, records, thresholds, alpha=.05, delta=.05):
        if not thresholds or len(set(thresholds)) != len(thresholds): raise ValueError('Rule family')
        tests, accepted = [], []
        for t in thresholds:
            n = k = 0
            for p, y in records:
                a = threshold_rule(p, t)
                if a:
                    n += 1; k += int(y[a] < y[0])
            pv = binomial_cdf(k, n, alpha) if n else 1.
            tests.append(dict(threshold=t, overrides=n, harms=k, p_value=pv))
            if n and pv <= delta/len(thresholds): accepted.append(t)
        return cls(min(accepted) if accepted else math.inf, tuple(tests), tuple(accepted))

    def choose(self, p): return threshold_rule(p, self.threshold)


def metrics(records, choices):
    n = len(records)
    if n != len(choices) or not n: raise ValueError('Metric association')
    harm = gain = over = success = 0
    diff = expected = 0.
    for r, a in zip(records, choices):
        y, p = r['outcomes'], r['truth']
        over += a != 0; harm += y[a] < y[0]; gain += y[a] > y[0]
        success += y[a]; diff += y[a]-y[0]; expected += p[a]-p[0]
    return dict(independent_sources=n, selected_success=success/n,
                override_frequency=over/n, harmful_override_frequency=harm/n,
                conditional_harm=harm/over if over else None,
                successful_improvement_frequency=gain/n, sampled_outcome_difference=diff/n,
                known_expected_outcome_difference=expected/n)
