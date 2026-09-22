# AV0 addendum — established paired-improvement testing control

This adds one **known paired-improvement testing control**, not our new method, a full HCPI reproduction or an individual-action safety guarantee. Accepted AV0 `ca0a05d5ec1c9ab66d723529ac227c98de5b73e1` is unchanged. **No differentiated treatment yet.** AV1 remains unlaunched; no automatic follow-up runs are scheduled or authorized.

## Test and estimand

The predictor and strict threshold rules {0,.05,.10,.20,.40} are exactly AV0's. For each fixed rule on the 512 calibration sources, let G count selected=1/baseline=0 and L count selected=0/baseline=1. Test H0: E[Y_selected−Y_baseline] <= 0 with the exact upper tail `P[Binomial(G+L,.5) >= G]`; no discordant pairs gives p=1. Accept at p<=.01 (.05/5), choose the smallest accepted threshold, otherwise baseline. No test labels determine thresholds. Integer combinatorial arithmetic and rational comparisons avoid approximate tails or numerical significance rounding.

For an i.i.d. paired binary source, expected difference is P(gain)−P(loss). Under the null, conditional on discordance, the gain probability is at most 1/2; conditioning on the discordant count yields the stated conservative null test. Bonferroni controls the probability of accepting any non-improving rule at .05 for the fixed family. This is a test of expected population improvement, not a positive confidence bound on every realized difference or every action's value.

Assumptions: fixed predictor/family, calibration independent of fitting, and one paired binary outcome per i.i.d. source from the target context/tail law. Dependence between the two outcomes within a pair is allowed. Duplicate-source IDs and averaged nonbinary outcomes are rejected by the API, but statistical independence cannot be established by an ID check. Do not reuse this count test unchanged for repeated anchors, horizons, tail draws, correlated source clusters or shifted repeated-policy states.

Always report `(G−L)/N` using **all N sources**, not G+L. Both calibration and test denominators are explicit in the outputs. The adaptively chosen rule's calibration performance is selection-affected; fresh test results are separate. Real-data expected values are not directly observed; the extra known-expectation column is possible only in these artificial fixtures.

## Different targets, not a safety ranking

| Control | Target | What acceptance does not establish |
|---|---|---|
| Added paired-improvement test | Positive expected population native-success difference, with familywise error control | Individual-action safety, bounded conditional harm or repeated-policy superiority |
| Unchanged conditional-harm LTT | Conditional probability of a harmful override <=.05, with familywise confidence | Positive expected improvement |
| Unchanged simultaneous bounds | Marginal coverage of the whole realized paired-advantage bank | Positive expected improvement or low harm conditional on overriding |
| Unchanged PC-RACP | Realized utility coverage coupled to its fixed learned policy | Baseline improvement or conditional override safety |

Equal numerical .05 values do not make these guarantees comparable. Expected gains can outweigh frequent losses; the added control does not enforce LTT's conditional-harm criterion. All original controls and outputs remain untouched.

## Analytical example: perfect prediction need not give a positive realized bound

Let U be uniform on [0,1], Y0=1[U<.1], Y1=1[U<.2]. Then D=Y1−Y0 equals 1 with probability .1 and 0 with probability .9, so E[D]=.1. Even with perfect success-probability predictions, any fixed strictly positive lower bound on D is satisfied on only 10% of draws, not 95%. The useful 95% lower bound on this realized binary difference therefore remains 0. For the AV0 residual construction, perfect h=.1 gives residual .1 with probability .9 and −.9 with probability .1; its population 95% quantile is .1 and the lower bound is h−q=0. Finite calibration randomness does not remove this target distinction.

Across independent calibration sources the added control instead accumulates evidence for positive expected gain: with no losses its p-value is 2^(−G), requiring at least 7 gains for this five-rule .01 cutoff. The estimated success gain is G/N, not 100% among discordances. This illustrates different targets, not universal superiority or a new robotics mechanism.

## Results and execution

[Complete results](RESULTS.md) and [raw evidence](RESULTS.json) report every one of the 18 cases, all 90 rule tests, accepted thresholds, gains/losses and all requested calibration/test metrics. All 18 original source digests match; all 25 original AV0 files remain byte-identical. AV0 did not save prediction vectors: its original sufficient statistics were restored from the identical artificial fitting fixtures, and its unchanged prediction method/perturbations were replayed without optimizer steps or new fitting choices. Original point metrics, LTT rule tests and simultaneous quantiles match exactly; new prediction hashes are retained.

The control accepts rules in **9/18 cases**: all seeds for shared-error, progress-conflict and the fixed-tail sequential example. It declines all optimistic-search, rare-override and sparse-binary cases. Its deployed rule matches conditional-harm LTT in **all 18 cases**; only the accepted family differs once (shared-error 92203 additionally accepts .10, but still deploys 0). Thus it fills an expected-improvement target gap but does **not** improve decisions over LTT under these fixtures. Simultaneous bounds remain baseline-only; that contrast is not a claim of superior safety.

Ten unit tests pass, including exhaustive binary-tail enumeration for n=0…10 (66 exact tails), ties, gains/losses only, family correction, all-source denominators and the analytical example. Finite artificial outcomes are not a theorem validation. The three bounded scripted testing/analysis runs took **14.829 cumulative wall-seconds**, with a peak job-memory measurement of **70,057,984 bytes**, four-CPU affinity and no failures or timeouts. All measurements are retained in [EXECUTION-LOG.json](EXECUTION-LOG.json); the addendum ceiling is one cumulative hour, four CPUs, 8 GiB and 250 MB. Preservation is separately timed in its receipt. No GPU, research checkpoint, reference payload, simulator, production adapter, model training, new allocation or dependency change is part of this addition.

Run tests from this worktree with the existing standard-library Python:

```powershell
$addPython = 'C:/Users/Chris/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $addPython docs/action-verification-paired-improvement-addendum-20260922/bounded_run.py unit-local $addPython test_addendum.py
```

`evaluate_addendum.py` and `report_addendum.py` exclusive-create outputs; they are not instructions to rerun this preserved package. The addendum relies on the read-only accepted AV0 modules in the sibling directory. Only new files are backed up; [DELIVERY.json](DELIVERY.json) identifies their committed source and verified SSD bytes. Historical science, E12 drafts and all AV1 launch restrictions remain unchanged.
