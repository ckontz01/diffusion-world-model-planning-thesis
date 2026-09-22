# Candidate mechanism: no differentiated treatment yet

The proposed comparative/conformal verifier currently reduces to the implemented reference constructions. No additional treatment is justified by this preparation, and no new method name is assigned.

The computation is: predict full-tail success for the baseline and each bank alternative; form h_i=p_i-p_0; optionally subtract a fitted optimism correction; calibrate whole-bank residuals; accept the maximum positive lower bound, otherwise retain baseline. A correction m_i changes h_i to h_i-m_i, which is simply another advantage predictor. Baseline fallback and paired branch observations are established design choices, not an independent algorithmic increment.

```text
h[i] = shared_predictor(candidate[i]) - shared_predictor(baseline)
q = conformal_rank(max_i(h_cal[i] - observed_advantage_cal[i]))
choose argmax([0] + [h[i] - q for i != baseline])
```

The strongest applicable controls address different limitations: the ordinary selector directly maximizes a learned outcome estimate; simultaneous calibration controls a bank-wide realized event but can abstain everywhere; LTT directly tests conditional harm for fixed acceptance rules; PC-RACP couples certificates to a separately learned policy. None of these automatically proves repeated-policy superiority. That gap is a change of estimand and data distribution, not evidence of a new mechanism here.

Same-information, same-risk test: with identical frozen predictions, bank, calibration sources and simultaneous risk target, the pseudocode must return exactly `Simultaneous.choose`. An optimism learner must also be supplied to the ordinary point and calibrated controls, with the same fit labels and capacity. Comparisons to LTT or PC must retain their different risk statements rather than claiming equal alpha means equal guarantees.

Analytic distinction **that is absent**: if h=(0,.4,.2) and q=.3, both this proposal and the standard bound rule select the .4 alternative; if q=.5, both choose baseline. Subtracting any identical correction from both predictors cannot create a treatment difference. The artificial suite's abstention and rare-override examples illustrate limitations of guarantees, not novelty of the proposed construction.

Component ablation: remove the alleged new component while leaving predictor, calibration and decision rule fixed. At present there is nothing distinct to remove; the ablation is an identity. A genuinely different component would require a predeclared computation and an isolated same-information comparator before a research launch.

Falsifier: exact agreement with the known control across all tested banks, or an apparent gain that disappears when that control receives the same features, branches, fit budget and risk objective, contradicts a differentiated-treatment claim. The working testbed is the deliverable; no speculative mechanism search was conducted.
