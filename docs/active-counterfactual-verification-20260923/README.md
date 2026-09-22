# ACV0 implementation package

**Implemented and tested on artificial arrays and a vector mock; real runtime disabled and untested.** This package implements a neural active-feedback candidate, not another calibration-control variant. It does not establish novelty, robot efficacy, sample efficiency or a safety guarantee.

Preparation authority is the preserved `ACV0-INSTRUCTION.txt`. Separate branch/worktree: `active-counterfactual-verification-preparation-20260923`, based on accepted AV0/addendum `02a6157ecb11ff2a9cf6ced6ce0523b181805db0`. All additions are in this directory. AV0, its addendum, AV1's unlaunched status, closed LGP/CVL/BP1 records, continuation and E12 drafts remain unchanged.

## What is runnable

| Component | Implementation / evidence |
|---|---|
| Four-component neural model, joint Gaussian response / Bernoulli continuation likelihood, analytic backprop, Adam | `model.py`; exact recipe and losses in `TRAINING-AND-DECISION.md`; saved artificial checkpoints and complete histories in `neural-run-v1/` |
| Outcome-independent ≤4×4 matched tree and exact original baseline retention | `tree.py`; full N300/K30/J30 cost test, dedup and suffix-independence tests |
| Initial-only five / observe / ten / baseline-tail policy | `policy.py`; original150 clock, native termination and no post-terminal work |
| Static, passive, active, no-response, same-information ordinary, Bayesian controls | `policy.py`, `model.py`, `bayes.py`; exact artificial known-law oracle separately labeled |
| Unweakened separate early-replanning and vanilla CEM references | `runtime_adapter.py`; production search-budget tests, no fixed-tree claim for early replanning |
| Fresh replay branch collector and independent checks | `mock.py`, `checker.py`, `run_mock.py`; 48 independently checked episodes in `mock-run-v2/`; v1 preserved |
| Exact metadata-only source-disjoint pilot and finite grid | `DATA-ROLES-PROPOSED.json`, `RUNTIME-PINS.json`, `PILOT-PROPOSED.json`, `PILOT-PROTOCOL.md` |
| Primary-method fidelity and code-access limits | `FIDELITY.md`; no broad novelty conclusion |

Existing Python/NumPy only; no package installation. The trainable networks use explicitly differentiated NumPy MLPs, not tables presented as neural models. The supplied table-learning module remains a separate original implementation, and the Gaussian compression module remains an analytical reference; neither is substituted for the learned neural model.

The array policy adapter and injected frozen-rollout interface run end to end on mocks. Actual Le-WM image/tensor and native-physics binding is source-inspected, **not executed**. There is deliberately no enabled checkpoint/reference loader, physics factory or Slurm submission entry point. `real_runtime()` and `launch_real_pilot()` raise `PermissionError`. The real bridge must be reviewed, authenticated and frozen before any newly authorized technical tranche. This is a runnable local implementation plus one concrete proposed pilot, not a claim that the research integration has already passed.

## All seven neural artificial cases

Exact expected success under the unchanged artificial **test law**, not robot success estimates. One fixed neural fit per case on the original1,024-source seed24000 sample, verified against the supplied ACV0 ZIP source digests; no parameter/seed/scenario tuning. Training192 updates/model/case. Validation128/test256 whole sources at seeds94101/94102 support prediction reporting only. Complete decisions, predicted values, source digests, integration costs, loss histories and validation/test metrics are in `neural-run-v1/RESULTS.json` and case subdirectories.

| Case | A static | B passive | C active | D no update | E ordinary | Bayesian regression | Exact Bayes |
|---|---:|---:|---:|---:|---:|---:|---:|
| Informative contact | .5684 | .5400 | .7566 | .5626 | .7566 | .7566 | .7566 |
| Mostly known context | .8150 | .8150 | .8150 | .8150 | .8150 | .8150 | .8150 |
| Uninformative prefix | .5800 | .5800 | .5800 | .5800 | .5800 | .5800 | .5800 |
| Expensive prefix | .5800 | .5800 | .5800 | .5800 | .4900 | .5800 | .5800 |
| No decision-relevant uncertainty | .6200 | .6200 | .6200 | .6200 | .6200 | .6200 | .6200 |
| Unstable contact mode | .5684 | .5800 | .5684 | .5684 | .5000 | .5800 | .5800 |
| Unannounced sensor reversal | .5800 | .5400 | .2134 | .5626 | .2134 | .2134 | .7566 |

The original robust baseline plan's known expected success is .58 except .62 in the no-decision-relevant case; A is a learned static plan selector, not that fixed baseline. The exact Bayes reference is correctly specified for each test law, including reversal; it has disclosed law knowledge, not a hidden episode-mode input. Learned policies do not receive the scenario name or true law as features. Discrete original observations are embedded as residual vectors; the continuous Gaussian model is an intentionally imperfect neural approximation. Numerical integration samples need not equal the actual discrete response law. The unchanged source coupling and this model mismatch are disclosed, not tuned away.

In the informative case, C matches E and both Bayesian references: the evidence supports working observation-conditioned selection, **not a differentiated advantage**. Reversal is an explicit failure (.2134 vs .58 robust baseline); unstable contact has a small C regression (.5684 vs .58). E's costly/unstable failures are retained, not used to claim a universal mixture advantage. No Gaussian contrast-sufficiency or robot-safety conclusion follows.

## Original reproduction and tests

Original ZIP SHA256 `9d843e842aae5318e55d65520a21b782cbb0f1c34c50875375fad6aa46cd95b2`, copied unchanged as `ORIGINAL-PROTOTYPE.zip`. All16 internal manifest entries retain exact bytes; manifest is also preserved. The supplied15 unit tests and main experiment ran once. Reproduction retains all1,470 rows /49 summaries /210 fits; all values/configuration/source digests match exactly (only elapsed runtime differs). See `prototype-reproduction/` and `VERIFICATION.json`. The main table's informative equality with exact Bayes and reversal failure are preserved.

All supplied compression and sensitivity files were read and authenticated. The Gaussian output reports64 cases /1,024 conditional means, max mean discrepancy6.18e−13; it is an analytical component, not a trained neural treatment. All196 method summaries in28 sensitivity configurations were inspected, including the supplied2,550-cell analytical grid. **No sensitivity sweep was rerun.** Original sources/outputs are untouched in `prototype/`.

Focused implementation suite:25 tests, including finite-difference gradients for every neural parameter tensor, same-information inputs, posterior/ranking changes, checkpoint/preprocessing identity, exact/permuted/deduplicated candidates, suffix-independent response law, full tree/early-replan budgets, clock/ownership/RNG boundaries, early success/truncation, common-history mismatch rejection, all-terminal records, no deployment optimization/branch callbacks and real-runtime refusal.

The independent mocked end-to-end smoke covers four contract fixtures (prefix success, prefix truncation, tail success, budget exhaustion), not new efficacy scenarios:40 collection episodes /2,712 actual mock steps,12 updates for each small fit, checkpoint restoration, eight held-out control episodes and48 independent episode checks. Its deliberately reduced N8/K2/J2 search is disclosed as a contract smoke; separate tests exercise full production N300/K30/J30 costs. Actual native endpoint geometry is checked independently on supplied artificial state arrays; no physics environment was launched.

Instrumentation audit added explicit CEM-solve, fixed-prefix-solve, learned-module-forward and prior-candidate counters. Earlier `outcome_queries` counted conditional predictions, not the additional prior predictions. `AUDIT-CORRECTIONS.json` supplies those missing accounting fields for the **unchanged** neural results; no neural efficacy fit was rerun. The same mock contract smoke was run into exclusive `mock-run-v2/` after this correction; v1 remains intact. Learned parameters, losses, decisions and physical traces are bit-identical across the two mock receipts. Each receipt's48 checks are not48 independent scientific sources. Numerical accounting includes both runs and the failed ZIP-audit attempt.

Every numerical/metadata attempt is retained in `EXECUTION-LOG.json`, including one failed authentication-script attempt: it incorrectly addressed ZIP members without their enclosing directory. The import had already authenticated the archive correctly. Only that audit path was corrected; the second audit passed with zero numerical differences. No model fitting, artificial main experiment or sensitivity grid was repeated for that tooling error. Maximum observed numerical process-group memory is about116MB; affinity limited to four CPUs with numerical thread counts1 and GPU disabled. Preparation limits remain14,400 cumulative scripted seconds /8GiB /1GB. Resource totals and preservation elapsed time are in execution/delivery receipts; this is not whole-machine RAM or CPU accounting.

## Run/read entry points

Already-run outputs are exclusive and will not be overwritten. Inspect those receipts first. In this package directory, the focused suite is `python -m unittest test_acv0 test_extended -v`; `run_mock.py` and `run_synthetic.py` write exclusive versioned outputs and should **not** be relaunched over accepted outputs. `build_pilot.py` constructs a proposal, never submits a job. `plan_metadata.py` reads identity metadata only. Use `bounded_run.py <new-unique-attempt-label> <existing-python> <script-or-arguments>` for any separately requested local execution; do not rerun on an automatic schedule.

For this preparation the existing interpreter was `C:/Users/Chris/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`. The bounded runner reuses only the accepted AV0 Windows process-limit helper, read-only. The new-package backup does not duplicate AV0 or any historical archive; the helper dependency remains available in the pinned base repository.

## ACV0 instruction traceability

1. Import/read/preserve/reproduce: original ZIP+manifest, `prototype/`, reproduction and `VERIFICATION.json`; table/Gaussian/neural distinctions above.
2. Initial execution object: `policy.py`, `runtime_adapter.py`, H75/150/five+ten+135 protocol; continuation unchanged.
3. Explicit tree: `tree.py`, exact baseline, fixed-prefix construction, exact dedup/missing slots, deterministic ties and charged rollouts.
4. Joint learned model: `model.py`, pre-fit `CONTRACT.json`/recipe, losses/source reductions, finite checks, checkpoints and actual gradients; no contrast compression.
5. Two-stage decision: shared finite integration, unconditional terminal decomposition, actual prefix evidence, own-suffix-only decisions; terminal mock/schema tests.
6. Controls: A–F, ordinary equal-information input audit, exact artificial Bayes / explicitly approximate real Bayesian regression, full separate early replanning.
7. Actual implementation tests:25 focused tests and mock collect→fit→restore→deploy→independent report; all negative original cases retained.
8. Legitimate data: identity-only registry projection, whole-source64/16/32 proposal excluding prior320+RB2 512,656 left unassigned, fresh prefix-replay coupling, no old-label reuse.
9. Narrow prior art: primary-source method/code-access fidelity table; IMPLY full-text access update; no novelty/safety/superiority assertion.
10. Executable preparation and costed pilot: runnable NumPy/vector modules, fixed339-job **proposal**, exact model/runtime/source metadata pins, technical tranche490/545, finite physical/search/resource/storage caps, no retries/replacement, preservation and review gates.

## Delivery and next boundary

Commit/push and exact remote readback are required before the exclusive small backup. `DELIVERY.json`, when present, records the actual package commit, SSD identity, per-member bytes/SHA256/readback and receipt. Only this new package is copied to `D:/THESIS-BACKUPS/active-counterfactual-verification-20260923/preparation-v1`; no historical archives are retransmitted.

The next decision is review of this single developmental pilot—not automatic collection, benchmark, production integration, model promotion, additional tuning or another stage. AV1 remains unlaunched. Scientific history and E12 remain unchanged.
