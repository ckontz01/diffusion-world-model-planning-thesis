"""Established paired binary improvement test; not HCPI or action-wise safety."""
from dataclasses import dataclass
from fractions import Fraction
import math
from pathlib import Path
import sys

AV0 = Path(__file__).resolve().parent.parent / 'action-verification-testbed-20260922'
sys.path.insert(0, str(AV0))
from controls import probabilities, threshold_rule

THRESHOLDS = (0., .05, .10, .20, .40)
CRITICAL = Fraction(1, 100)  # .05 / five fixed hypotheses, exact comparison


def upper_tail(gains, losses):
    """Exact conditional sign/McNemar tail, including the all-ties convention."""
    if type(gains) is not int or type(losses) is not int or min(gains, losses) < 0:
        raise ValueError('Gains/losses must be nonnegative integer source counts')
    n = gains + losses
    return Fraction(sum(math.comb(n, k) for k in range(gains, n+1)), 2**n) if n else Fraction(1)


@dataclass(frozen=True)
class PairedImprovement:
    threshold: float | None
    accepted: tuple
    tests: tuple

    @classmethod
    def calibrate(cls, records):
        """One (source_id, prediction[8], binary_outcomes[8]) row per iid source.

        Predictions/five rules must already be fixed independently of these
        calibration outcomes. No test outcomes or risk-level argument accepted.
        """
        records = tuple(records)
        if not records: raise ValueError('Empty calibration population')
        ids = [r[0] for r in records]
        if len(set(ids)) != len(ids): raise ValueError('Repeated source; count test not applicable')
        for _, p, y in records:
            probabilities(p)
            if len(y) != 8 or any(type(v) is not int or v not in (0,1) for v in y):
                raise ValueError('Requires binary draws, not averaged repeated outcomes')
        tests, accepted = [], []
        for threshold in THRESHOLDS:
            gains = losses = overrides = success = baseline_success = 0
            for _, p, y in records:
                a = threshold_rule(p, threshold)
                gains += int(y[a] == 1 and y[0] == 0)
                losses += int(y[a] == 0 and y[0] == 1)
                overrides += int(a != 0)
                success += y[a]; baseline_success += y[0]
            pv = upper_tail(gains, losses)
            passed = pv <= CRITICAL
            if passed: accepted.append(threshold)
            tests.append(dict(threshold=threshold, sources=len(records), gains=gains, losses=losses,
                              discordant=gains+losses, ties=len(records)-gains-losses,
                              p_value=float(pv), accepted=passed, critical_value=float(CRITICAL),
                              selected_success=success/len(records), baseline_success=baseline_success/len(records),
                              overrides=overrides, sampled_net_difference=(gains-losses)/len(records)))
        return cls(min(accepted) if accepted else None, tuple(accepted), tuple(tests))

    def choose(self, p):
        probabilities(p)
        return threshold_rule(p, self.threshold) if self.threshold is not None else 0
