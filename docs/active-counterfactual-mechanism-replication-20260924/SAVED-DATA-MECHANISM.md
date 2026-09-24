# ACV0 saved-data mechanism report — 24 September 2026

Post-hoc, CPU-only description of the completed, preserved ACV0 pilot. Original result commit: `5d8666754ad8aa0507730f86cf3ee6caa32c105a`. No old estimate or controller is changed. No new final-source outcomes are assigned to the added control.

## Actual paired choices on all32 final-development sources

Active and no_update have byte-identical candidate trees, selected prefixes, and actual first-five action/state/latent/dynamics/pixel-hash/flag histories on all32 sources. Their suffix choice differs on20 sources. Among these:13 both fail,6 both succeed,1 active-only success (847),0 no_update-only successes. On the12 unchanged-suffix sources there are3 joint successes and9 joint failures. Thus feedback frequently changes actions, but changes native binary success only once in these paired executions. Action changes with equal endpoints are not evidence of equivalence or proof of benefit.

The160 deployed static/passive/active/no_update/ordinary decisions were reproduced from saved candidate features and the unchanged small predictors, including original prefix scores and actual-response suffix selection. Bayesian decisions below are authenticated saved choices, not newly replayed predictions. Vanilla and early replanning have no fixed-tree suffix index; their original endpoints remain in the machine-readable report.

Active and static selected different prefixes on 12 sources: 931, 623, 847, 175, 5, 1236, 1160, 784, 1247, 1031, 1005 and 1598. This is the observed decision-level distinction between anticipated-feedback selection and committed selection. The new control's old-final outcomes remain unassigned: these prefix differences do not supply its missing suffix/outcome observations.

Cells below are `prefix/suffix; native success`. Indices only compare within a source; exact action arrays/hashes and every arm’s endpoint/steps are in `SAVED-DATA-MECHANISM.json`.

| Source | Static | Passive | Active | No update | Ordinary | Bayesian | Suffix changed |
|---|---|---|---|---|---|---|---|
| 931 | 3/2; 0 | 0/1; 0 | 0/1; 0 | 0/1; 0 | 2/0; 0 | 2/0; 0 | False |
| 643 | 2/3; 0 | 0/1; 0 | 2/0; 0 | 2/3; 0 | 2/2; 0 | 2/2; 0 | True |
| 1000 | 3/1; 0 | 0/3; 0 | 3/0; 0 | 3/1; 0 | 3/2; 0 | 3/2; 0 | True |
| 146 | 0/0; 0 | 0/0; 0 | 0/0; 0 | 0/0; 0 | 0/0; 0 | 0/0; 0 | False |
| 672 | 0/2; 1 | 0/3; 1 | 0/3; 1 | 0/2; 1 | 0/2; 1 | 0/2; 1 | True |
| 623 | 3/2; 0 | 0/2; 0 | 0/2; 0 | 0/2; 0 | 3/0; 0 | 3/3; 0 | False |
| 847 | 3/3; 1 | 0/3; 1 | 0/3; 1 | 0/0; 0 | 0/0; 0 | 0/2; 0 | True |
| 175 | 3/3; 0 | 0/0; 0 | 0/0; 0 | 0/0; 0 | 3/3; 0 | 3/3; 0 | False |
| 553 | 0/3; 0 | 0/3; 0 | 0/3; 0 | 0/3; 0 | 2/2; 0 | 1/2; 0 | False |
| 1334 | 1/2; 0 | 0/3; 0 | 1/1; 0 | 1/2; 0 | 0/3; 0 | 0/3; 0 | True |
| 1570 | 0/1; 0 | 0/1; 0 | 0/1; 0 | 0/1; 0 | 3/2; 0 | 3/0; 0 | False |
| 361 | 0/3; 0 | 0/3; 0 | 0/3; 0 | 0/3; 0 | 2/1; 0 | 0/3; 0 | False |
| 658 | 0/2; 1 | 0/2; 1 | 0/2; 1 | 0/2; 1 | 2/0; 1 | 0/2; 1 | False |
| 1219 | 3/3; 1 | 0/0; 1 | 3/1; 1 | 3/3; 1 | 0/0; 1 | 3/3; 1 | True |
| 5 | 3/1; 1 | 0/1; 1 | 0/1; 1 | 0/0; 1 | 3/1; 1 | 0/0; 1 | True |
| 1234 | 1/0; 1 | 0/0; 1 | 1/0; 1 | 1/0; 1 | 3/1; 0 | 1/1; 0 | False |
| 592 | 0/0; 0 | 0/3; 0 | 0/3; 0 | 0/0; 0 | 3/0; 0 | 3/3; 0 | True |
| 1236 | 3/2; 0 | 0/0; 0 | 0/0; 0 | 0/3; 0 | 3/2; 0 | 3/2; 0 | True |
| 1160 | 3/1; 0 | 0/0; 0 | 0/0; 0 | 0/2; 0 | 0/0; 0 | 2/2; 0 | True |
| 1393 | 0/0; 0 | 0/2; 0 | 0/2; 0 | 0/0; 0 | 2/1; 0 | 2/1; 0 | True |
| 784 | 1/1; 0 | 0/3; 1 | 0/3; 1 | 0/2; 1 | 1/3; 0 | 3/3; 0 | True |
| 213 | 0/3; 0 | 0/2; 0 | 0/2; 0 | 0/3; 0 | 0/0; 0 | 0/0; 0 | True |
| 1391 | 0/3; 0 | 0/0; 0 | 0/0; 0 | 0/3; 0 | 1/3; 0 | 1/3; 0 | True |
| 1247 | 1/3; 0 | 0/2; 1 | 0/2; 1 | 0/3; 1 | 0/0; 0 | 0/0; 0 | True |
| 1031 | 3/1; 0 | 0/3; 0 | 1/2; 0 | 1/2; 0 | 3/0; 0 | 1/2; 0 | False |
| 880 | 1/3; 0 | 0/3; 0 | 1/0; 0 | 1/3; 0 | 0/3; 0 | 0/3; 0 | True |
| 911 | 0/0; 0 | 0/0; 0 | 0/0; 0 | 0/0; 0 | 1/0; 0 | 1/1; 0 | False |
| 1005 | 1/3; 0 | 0/0; 0 | 0/0; 0 | 0/3; 0 | 0/3; 0 | 0/3; 0 | True |
| 662 | 2/1; 0 | 0/2; 0 | 2/2; 0 | 2/1; 0 | 0/1; 0 | 1/2; 0 | True |
| 1493 | 3/2; 1 | 0/3; 1 | 3/0; 1 | 3/2; 1 | 1/2; 0 | 2/2; 1 | True |
| 1598 | 2/1; 0 | 0/0; 0 | 0/0; 0 | 0/2; 0 | 3/2; 0 | 3/2; 0 | True |
| 1326 | 1/2; 1 | 0/0; 0 | 1/2; 1 | 1/2; 1 | 1/2; 1 | 1/3; 1 | False |

## Predicted prefix-value decomposition

For prefix p, terminal probabilities are S_p,F_p,A_p and unconditional suffix predictions are q̄_pj. Define j*=argmax_j q̄_pj with original content-based ties. Committed active value C_p=A_p q̄_pj*. Terminal-prefix contribution T_p=S_p (terminal failure contributes zero). The unchanged finite-integration score is V_p=S_p+A_p Σw_r max_j q_pj(r). Anticipated feedback increment B_p=A_p[Σw_r max_j q_pj(r)−q̄_pj*]. Exactly V_p=T_p+C_p+B_p; total committed outcome is T_p+C_p.

B_p also splits into nonnegative same-draw feedback gain A_p Σw_r[max_j q_pj(r)−q_pj*(r)] and signed quadrature correction A_p[Σw_r q_pj*(r)−q̄_pj*]. The latter must not be interpreted as a benefit of observing feedback. All original128 component-stratified antithetic responses/seed94021 are retained, not increased or optimized.

| Role / prefixes summarized | Terminal T | Committed-active C | Anticipated B | Same-draw gain | Quadrature correction | Active V |
|---|---:|---:|---:|---:|---:|---:|
| final_development / 128 | 0.172891 | 0.265960 | 0.003318 | 0.003409 | -0.000092 | 0.442169 |
| validation / 64 | 0.168024 | 0.285654 | 0.002390 | 0.002267 | 0.000123 | 0.456069 |
| actual active-selected /32 | 0.172926 | 0.275347 | 0.007305 | 0.007374 | -0.000070 | 0.455577 |

These are predicted native-success values, not observed causal components. All32 actual active/no_update prefixes remained nonterminal; nonzero predicted terminal contributions are model outputs, not observed prefix successes. Across-source prefix changes bundle physical effects, observation changes and different suffix sets; they do not isolate information gathering. The JSON contains every prefix’s components, probabilities, selected committed suffix and action identity for both roles.

## Sixteen validation banks: same candidates, separate role

All saved suffix outcomes are used on each active prefix, with physical prefix replay checked. Prefix metrics average over suffixes, then prefixes within source, then the16 sources; branch rows are not independent observations. No fitting-data bank was decoded. Validation remains report-only and is not pooled with the32 final-development sources. Scores use identical saved candidates and actual responses, avoiding selected-branch population differences.

| Predictor | Same-candidate BCE | Same-candidate Brier |
|---|---:|---:|
| joint_conditional | 0.994135 | 0.268940 |
| joint_prior | 0.580993 | 0.196480 |
| ordinary_conditional | 3.124009 | 0.462367 |

On these banks, the joint conditional predictor scores worse than its own unconditional prior, although better than this fixed ordinary predictor. This is descriptive, not universal calibration dominance, and does not invalidate the ordinary comparator.

| Validation source | Static | Committed feedback (new) | No update | Active | Ordinary |
|---|---|---|---|---|---|
| 1579 | 2/3; 0 | 2/0; 0 | 0/0; 0 | 0/0; 0 | 0/0; 0 |
| 1440 | 0/2; 0 | 0/0; 0 | 0/2; 0 | 0/0; 0 | 3/3; 0 |
| 1459 | 0/0; 0 | 0/0; 0 | 0/0; 0 | 0/0; 0 | 2/2; 0 |
| 1022 | 2/1; 0 | 2/0; 0 | 2/1; 0 | 2/0; 0 | 0/0; 0 |
| 1388 | 1/1; 0 | 1/1; 0 | 1/1; 0 | 1/1; 0 | 1/1; 0 |
| 169 | 1/3; 0 | 1/3; 0 | 0/1; 0 | 0/1; 0 | 0/0; 0 |
| 455 | 0/3; 0 | 0/0; 0 | 0/3; 0 | 0/0; 0 | 0/2; 0 |
| 322 | 3/2; 0 | 3/2; 0 | 0/0; 0 | 0/0; 0 | 2/1; 0 |
| 852 | 0/3; 0 | 0/2; 0 | 0/3; 0 | 0/2; 0 | 1/0; 0 |
| 585 | 2/3; 0 | 2/3; 0 | 2/3; 0 | 2/3; 0 | 2/2; 0 |
| 830 | 0/2; 0 | 0/3; 0 | 0/2; 0 | 0/3; 0 | 0/2; 0 |
| 1476 | 3/3; 0 | 3/2; 0 | 3/3; 0 | 3/2; 0 | 2/1; 0 |
| 1381 | 3/1; 0 | 3/1; 0 | 0/2; 0 | 0/0; 0 | 0/2; 0 |
| 930 | 1/3; 0 | 1/2; 0 | 1/3; 0 | 1/2; 0 | 2/3; 0 |
| 1328 | 1/1; 0 | 1/0; 1 | 1/1; 0 | 1/0; 1 | 0/1; 0 |
| 49 | 1/3; 0 | 1/2; 0 | 0/0; 0 | 0/2; 0 | 1/1; 0 |

Totals out of16: active=1, committed_feedback=1, no_update=0, ordinary=0, static=0.
This table applies fixed predictors/rules to already-executed validation branches; it is not a newly executed final evaluation or evidence of training-seed robustness. No unexecuted old-final source/control outcome is inferred, even if a new rule might choose a previously seen branch.

## Conclusion and audit boundary

The existing evidence supports response-dependent action changes and one observed final-cohort endpoint gain versus no_update. It does not establish that anticipated feedback is a robust reason to choose the prefix. The new control completes the missing comparison needed to examine that question prospectively. The same-candidate validation diagnostics also caution against equating conditional updates with uniformly better predictions. No robotics mechanism, novelty, safety guarantee, model promotion or general superiority is established.

The one saved-data computation took 24.422s wall / 27.141s process CPU. Four-thread ceiling;0 Le-WM forwards,0 physics steps,0 fits,0 reference-payload reads,0 GPU jobs. Selected members were authenticated against the existing verified SSD request; no archive/backup cycle was repeated. Original REPORT SHA: `28fe9fa78fd6b6e4dad4059abb15092ad78d5f502d2c2470974cf594412bfacf`.
