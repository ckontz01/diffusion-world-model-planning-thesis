# Preparatory design/feasibility history

Work initiated2026-09-05 and completed after the local date rolled to2026-09-06.
Branch `e18-confirmation-design-feasibility`; parent286088e. This is a new
preparatory package, not a change to any historical result or a confirmation
freeze. No model, initializer, driver, solver, checkpoint or historical decision
file was edited. The three unrelated untracked E12 drafts were not modified,
staged or included in the commit.

## Availability audit

- Bounded metadata-only script uses the global allowed partition registry and
  explicit exposure sources, outputs counts and exposure-set hashes only, and
  excludes P3/P4 wholesale. No protected outcome or membership manifest is read.
- Remote staging:
  `/lustreFS/data/superworld/ckontzias/thesis/staging/e18-design-feasibility-20260905`.
- Metadata attemptv1 stopped on an overly narrow inventory-path count assertion
  before writing output. Attemptv2 covered128-less-two earlier stores plus four
  pools; two additional P2 smoke paths under `repro` were identified and included
  in finalv3. All128 earlier P2 stores plus four pool stores are now checked.
  Including the two smoke stores does not change the final82-episode capacity.
  This was an audit-inventory correction, not data selection based on outcomes.
- All three remote attempt directories are preserved under
  `/lustreFS/data/superworld/ckontzias/thesis/experiments/e18-design-feasibility/metadata-20260905-v{1,2,3}`.
  Only finalv3 is carried in the package. Superseded duplicate local working
  copies were removed; the remotev2 evidence remains recoverable.
- Final count: P2 1,930; length>=151 453; recorded episode-exposure exclusions371;
  metadata-qualified maximum82. SAGE roles73train/9validation/0test. Exact LeWM
  episode training membership unknown for all82. No protected-allocation release
  certificate exists in this package; a count-only request is provided unsent.

## Historical planning and simulation

- Verified adjacent sealed E18 analysis and identifier-only E19 overlap audits.
  Read the authorized old E18 PushT outcomes only for the statistical analysis:
  360 rows,12 distinct episodes, both horizons, three fixed training seeds.
- Episode contrasts have means1/9 each; variance0.07239057/0.10269360,
  covariance0.05218855. All leave-one-episode fits and20,000 exploratory episode
  bootstrap draws are recorded. These are uncertain old-interface inputs.
- 20,000 simulation replicates per N/scenario/null configuration. Actual paired
  Student statistics, one-sided Bonferroni0.025 each, constrained six-binary-run
  episode-pair support, explicit global/partial-null checks. Six covariance
  scenarios and Ns82/400/600/800; larger Ns labelled currently infeasible.
- No empirical effect-size selection, observed-five-point gate or seed/start
  pseudoreplication. No model fitted to prospective observations.

## Regression and resource probe

- Added model-free deterministic full-budget tests using the actual unchanged
  scheduled policy and fresh driver, both H, one/three slots, all chunks, both
  schedule cycles, post-budget rejection and new episode after completion.
- Bounded A6000 job**300309**, gpu09, `COMPLETED`, exit0:0, elapsed55s.
  Input: stored exposed8908/53 R1 record only.80 actual solver calls, including
 20 warmups, zero evaluated episodes. Model tensors remained hash-identical.
- Run:
  `/lustreFS/data/superworld/ckontzias/thesis/experiments/e18-design-feasibility/timing-job-300309`.
  Both outputs' adjacent checksums passed. Remote swm006 lifecycle tests:
  **4 passed in14.72s**, four generic Gymnasium array-coercion warnings.
- Local combined fresh-driver/verifier/full-budget/planning/E18-spec/runtime/
  closed-loop regression suite: **36 passed in36.43s**, nine generic array
  coercion warnings. A separate targeted design regression run passed7 tests.
  Assertions check accepted source bytes against parent286088e.
- Resource estimates distinguish the measured batch1 planner timings from
  unmeasured native-step/I/O assumptions.82 episodes x30 runs=2,460 runs,
  full-budget central1.70 allocated GPU-hours, conservative envelope4.93h.
  Proposed allowance6h is not granted or consumed by this package.

## Disposition

No-go for claiming adequate five-point sensitivity with the currently allowed
pool. One feasible maximum-coverage N<=82 option is documented for explicit
lower-sensitivity approval; no sample size approved. Larger designs require
new certified availability, not fabricated independent seeds or starts.
No confirmation was frozen/launched, no SAGE grid reopened, no author contacted,
and no protected outcome or prospective model evaluation was accessed.
