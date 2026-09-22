# Artificial results — complete predeclared suite

18 case/seed combinations; 59,904 independent artificial source situations across four disjoint roles. Each combination has 512 fit, 256 learn, 512 calibration and 2,048 test sources. Three fixed seeds per case are all retained in ARTIFICIAL-RESULTS.json. This is not research efficacy, a reproduction of author experiments, or a finite Monte Carlo proof.

The table averages the three equal-size seed runs. Columns are probabilities/differences, not percentages. Conditional harm averages only runs with overrides; null means no overrides in any run. The known expected difference uses the artificial generator probabilities, unavailable on real tasks.

| Case | Method | Success | Override | Marginal harm | Conditional harm | Improvement | Sample diff | Known expected diff |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| shared_error | baseline | 0.5199 | 0.0000 | 0.0000 | null | 0.0000 | 0.0000 | 0.0000 |
| shared_error | point | 0.5622 | 0.6466 | 0.0000 | 0.0000 | 0.0423 | 0.0423 | 0.0437 |
| shared_error | point_logged | 0.5052 | 0.8247 | 0.0293 | 0.0349 | 0.0146 | -0.0146 | -0.0151 |
| shared_error | simultaneous | 0.5199 | 0.0000 | 0.0000 | null | 0.0000 | 0.0000 | 0.0000 |
| shared_error | ltt | 0.5622 | 0.6466 | 0.0000 | 0.0000 | 0.0423 | 0.0423 | 0.0437 |
| shared_error | pc_complete | 0.5334 | 0.1265 | 0.0000 | 0.0000 | 0.0135 | 0.0135 | 0.0119 |
| shared_error | pc_logged | 0.5155 | 0.1891 | 0.0072 | 0.0323 | 0.0028 | -0.0044 | -0.0034 |
| optimistic_search | baseline | 0.5231 | 0.0000 | 0.0000 | null | 0.0000 | 0.0000 | 0.0000 |
| optimistic_search | point | 0.5041 | 0.8473 | 0.0356 | 0.0421 | 0.0166 | -0.0190 | -0.0169 |
| optimistic_search | point_logged | 0.4971 | 0.8408 | 0.0392 | 0.0466 | 0.0132 | -0.0260 | -0.0235 |
| optimistic_search | simultaneous | 0.5231 | 0.0000 | 0.0000 | null | 0.0000 | 0.0000 | 0.0000 |
| optimistic_search | ltt | 0.5231 | 0.0000 | 0.0000 | null | 0.0000 | 0.0000 | 0.0000 |
| optimistic_search | pc_complete | 0.5094 | 0.6367 | 0.0256 | 0.0402 | 0.0119 | -0.0137 | -0.0119 |
| optimistic_search | pc_logged | 0.5021 | 0.6942 | 0.0311 | 0.0447 | 0.0101 | -0.0210 | -0.0196 |
| rare_override | baseline | 0.8003 | 0.0000 | 0.0000 | null | 0.0000 | 0.0000 | 0.0000 |
| rare_override | point | 0.7882 | 0.0179 | 0.0120 | 0.6702 | 0.0000 | -0.0120 | -0.0107 |
| rare_override | point_logged | 0.7101 | 0.1444 | 0.0902 | 0.6290 | 0.0000 | -0.0902 | -0.0866 |
| rare_override | simultaneous | 0.8003 | 0.0000 | 0.0000 | null | 0.0000 | 0.0000 | 0.0000 |
| rare_override | ltt | 0.8003 | 0.0000 | 0.0000 | null | 0.0000 | 0.0000 | 0.0000 |
| rare_override | pc_complete | 0.7882 | 0.0179 | 0.0120 | 0.6702 | 0.0000 | -0.0120 | -0.0107 |
| rare_override | pc_logged | 0.7882 | 0.0179 | 0.0120 | 0.6702 | 0.0000 | -0.0120 | -0.0107 |
| sparse_binary | baseline | 0.0132 | 0.0000 | 0.0000 | null | 0.0000 | 0.0000 | 0.0000 |
| sparse_binary | point | 0.0132 | 0.0586 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0001 |
| sparse_binary | point_logged | 0.0106 | 0.8563 | 0.0028 | 0.0032 | 0.0002 | -0.0026 | -0.0011 |
| sparse_binary | simultaneous | 0.0132 | 0.0000 | 0.0000 | null | 0.0000 | 0.0000 | 0.0000 |
| sparse_binary | ltt | 0.0132 | 0.0000 | 0.0000 | null | 0.0000 | 0.0000 | 0.0000 |
| sparse_binary | pc_complete | 0.0132 | 0.0187 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| sparse_binary | pc_logged | 0.0132 | 0.0449 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | -0.0000 |
| progress_conflict | baseline | 0.6991 | 0.0000 | 0.0000 | null | 0.0000 | 0.0000 | 0.0000 |
| progress_conflict | point | 0.7879 | 0.9103 | 0.0000 | 0.0000 | 0.0889 | 0.0889 | 0.0910 |
| progress_conflict | point_logged | 0.6966 | 0.6702 | 0.0505 | 0.0733 | 0.0480 | -0.0024 | -0.0005 |
| progress_conflict | simultaneous | 0.6991 | 0.0000 | 0.0000 | null | 0.0000 | 0.0000 | 0.0000 |
| progress_conflict | ltt | 0.7879 | 0.9103 | 0.0000 | 0.0000 | 0.0889 | 0.0889 | 0.0910 |
| progress_conflict | pc_complete | 0.7262 | 0.2889 | 0.0000 | 0.0000 | 0.0272 | 0.0272 | 0.0289 |
| progress_conflict | pc_logged | 0.7171 | 0.1875 | 0.0000 | 0.0000 | 0.0181 | 0.0181 | 0.0188 |
| sequential_shift | baseline | 0.5083 | 0.0000 | 0.0000 | null | 0.0000 | 0.0000 | 0.0000 |
| sequential_shift | point | 0.8068 | 1.0000 | 0.0000 | 0.0000 | 0.2985 | 0.2985 | 0.3000 |
| sequential_shift | point_logged | 0.6379 | 0.8341 | 0.0311 | 0.0371 | 0.1606 | 0.1296 | 0.1346 |
| sequential_shift | simultaneous | 0.5083 | 0.0000 | 0.0000 | null | 0.0000 | 0.0000 | 0.0000 |
| sequential_shift | ltt | 0.8068 | 1.0000 | 0.0000 | 0.0000 | 0.2985 | 0.2985 | 0.3000 |
| sequential_shift | pc_complete | 0.5828 | 0.2658 | 0.0000 | 0.0000 | 0.0745 | 0.0745 | 0.0797 |
| sequential_shift | pc_logged | 0.5632 | 0.2093 | 0.0021 | 0.0083 | 0.0570 | 0.0549 | 0.0539 |

## Coverage and degeneracy (per-seed ranges)

| Case | Simultaneous coverage | PC complete coverage | PC logged coverage | PC complete nonzero certificate | PC logged nonzero certificate |
|---|---:|---:|---:|---:|---:|
| shared_error | 0.9531–0.9653 | 0.9409–0.9727 | 0.9321–1.0000 | 0.0591–0.1313 | 0.0000–0.1309 |
| optimistic_search | 0.9541–0.9634 | 1.0000–1.0000 | 1.0000–1.0000 | 0.0000–0.0000 | 0.0000–0.0000 |
| rare_override | 0.9478–0.9883 | 0.9336–0.9854 | 0.9727–0.9868 | 0.0171–0.2681 | 0.0171–0.0801 |
| sparse_binary | 0.9932–0.9971 | 1.0000–1.0000 | 1.0000–1.0000 | 0.0000–0.0000 | 0.0000–0.0000 |
| progress_conflict | 0.9385–0.9668 | 0.9438–0.9595 | 0.9648–1.0000 | 0.1978–0.2456 | 0.0000–0.1382 |
| sequential_shift | 0.9351–0.9561 | 0.9526–0.9575 | 0.9575–0.9775 | 0.1841–0.2559 | 0.1260–0.2485 |

## Interpretation and limitations

- Simultaneous bounds made zero overrides in every run, including beneficial cases. This is valid abstention, not an improvement. LTT accepted useful rules in shared-error, progress-conflict and fixed-tail sequential cases; it accepted none in optimistic-search, rare-override or sparse-binary cases. Every threshold count/p-value is in the JSON.
- Rare overrides had roughly 60–73% conditional harmful-outcome frequency for point/PC despite low marginal frequency. A policy-coupled coverage certificate does not certify conditional override safety. Individual PC run coverage below .95 is retained: split-randomness and test variability matter, and three runs are too few to validate a theorem or detect a subtle implementation error.
- Binary PC certificates were identically zero for optimistic-search and sparse-binary cases. Zero certificates do not necessarily mean zero overrides: PC preserves its learned policy instead of switching to baseline during calibration. This contrasts with the explicitly baseline-preserving simultaneous rule.
- Shared-error uses a hidden bank-common perturbation and shared uniform outcome draws. Optimistic-search deliberately perturbs every method's prediction channel with independent candidate Gaussian errors. Rare-override injects a 2% optimism event. These are controlled artificial misspecifications, not claims that the fitted table is well specified in those channels. The saturated 16-context × 8-action table is an ordinary strong control for the observable discrete contexts; this does not establish sufficient capacity on Le-WM latents.
- Progress conflict uses short-progress winner 1 with true full-success probability .15 versus slot 2 at .80. The sequential test adds an explicit two-step probability tree: a useful single intervention followed by the fixed baseline tail has success .80, but repeating the override in the shifted state has success .10. This is arithmetic, not a physics simulation or evidence that any real verifier behaves this way.
- Logged PC uses one preassigned uniform fitting label per source; point-logged has the same restriction and capacity. Complete PC and the other full-bank controls receive the same complete fitting labels. Comparing logged PC directly to the full-bank point selector without this qualification would conflate information budgets.
- Mathematical tests compare ACID scaling, whole-bank residual algebra, rank indexing, exact binomial p-values, binary PC envelope and equations 4.2/4.5. Integration tests check native observation divergence, actual returned means, duplicate aliases, fixed banks and chunk success. They do not test research checkpoints, image encoders, GPU precision, real endpoint readers or simulator cloning.

## Calibration requirements

At 95% confidence and a 5% conditional-harm target, zero harms need 59 overrides for one fixed rule or 90 for this five-rule Bonferroni family. At 2% overrides, 90/.02=4,500 sources in expectation (not a guarantee). A finite 95% simultaneous rank requires 19 sources, which says nothing about positive bounds. Uniform 1/8 logging requires 152 sources in expectation for 19 matching actions; with 320 proposed calibration sources only 40 matches are expected. Binary sparsity can remain uninformative even beyond these minimum counts.

Arithmetic erratum retained transparently: ARTIFICIAL-RESULTS.json's `sources_expected_at_2pct_override_five_rules=4490` rounded the continuous logarithmic threshold before imposing the integer 90-override requirement. The discrete minimum expectation is 4,500, as used here and in the real-runtime proposal. The original result file is preserved; no scenarios were rerun to alter outcomes.
