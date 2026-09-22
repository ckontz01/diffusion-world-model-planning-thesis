# AV0 — matched action-verification testbed

Implemented and CPU-tested; **no research launch**. LGP1/RB1/RB2 remain closed and unchanged. Continuation remains the working system. This branch is a separate development testbed, not a replacement or a new-method efficacy claim.

## Deliverables

- [Comparator code/paper fidelity](FIDELITY.md): native vanilla CEM and in-search ACID; ordinary point selector; simultaneous bank bounds; finite-family LTT; separately labeled logged and complete-branch PC-RACP binary specializations.
- [Target and guarantee boundaries](TARGET-AND-GUARANTEES.md): paired fixed-tail success, conditional versus marginal harm, and repeated-policy limitations.
- [Complete artificial results](ARTIFICIAL-RESULTS.md), [machine-readable outputs](ARTIFICIAL-RESULTS.json), [all attempt logs](EXECUTION-LOG.json): 18 predeclared case/seed runs, including unfavorable/degenerate cases. Final unit suite has22 tests. No failed test or timeout so far.
- [Data reuse inventory](DATA-REUSE.md), [exact proposed roles](DATA-ROLES-PROPOSED.json), [canonical role cross-check](ROLE-CROSSCHECK.json):832 excluded,768 remaining; metadata only.
- [Candidate mechanism](CANDIDATE-MECHANISM.md): **no differentiated treatment yet**. Ordinary advantage prediction, baseline fallback and conformal calibration are controls, not renamed inventions.
- [One staged real-runtime proposal](REAL-RUNTIME-PROPOSAL.md): included four-source technical tranche first, explicit models/labels/caps; repeated-policy stage needs a separate direction. No launcher or enabled research approval exists here.

## Run the artificial unit tests

Requires only an existing Python standard library. On this Windows host, from the worktree root:

```powershell
$avPython = 'C:/Users/Chris/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $avPython docs/action-verification-testbed-20260922/bounded_run.py unit-local $avPython test_av0.py
```

The bounded runner uses the package directory as working directory and retains all attempt records. `suite.py` executes all cases in CONTRACT.json and exclusive-creates ARTIFICIAL-RESULTS.json; running it again in this preserved package deliberately fails instead of overwriting evidence. For a new synthetic reproduction, use a separately named copy of the implementation/contract without existing outputs, still charge it to the cumulative four-hour authorization. No dependency installation is needed. `planning.py` exposes CEM, shortlist, native/checker paths and a frozen-latent callback port; `controls.py` and `pc_racp.py` expose independently testable decision/calibration APIs.

## Implemented versus untested

Implemented: artificial CEM/ACID search and fixed-bank interfaces, shared fitted categorical predictor, standard calibration controls, genuine PC policy-learning/set-calibration separation, known logged propensities, duplicate handling, source split reconciliation and full artificial reporting. Twenty-two unit tests and the fixed18-case suite pass execution checks; Monte Carlo outputs are not pass/fail proof of statistical guarantees.

Still untested: production image/tensor adapter, actual Le-WM checkpoint inference, FP32/BF16 parity, actual simulator cloning/action delivery and native endpoints, real-data fitting, real calibrator usefulness, native ACID efficacy and repeated-policy outcomes. The future ACID reconstruction fit is explicit in the proposal because no authenticated reusable IDM checkpoint was established by this metadata inspection. Do not silently substitute an artificial residual for a real ACID comparator.

The artificial evidence contains an explicitly documented arithmetic erratum: the original JSON gives4,490 expected calibration sources using an unrounded continuous count; requiring the integer90 zero-harm overrides gives4,500. Original outputs are retained; no scientific scenario/seed was changed. One local patch application failed to match a document line; it made no changes and was reapplied correctly. That editing error is not a test attempt or research failure.

Preservation and remote authentication are recorded in `DELIVERY.json` after the package is committed/pushed and copied to a fresh THESIS_SSD namespace. No historical archive is copied or reopened for AV0.
