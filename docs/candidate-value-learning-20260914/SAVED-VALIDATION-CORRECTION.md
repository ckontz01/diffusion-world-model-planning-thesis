# CVL-1 focused saved-label correction

Researcher conditional approval received for scientific base
`b44fc4c096fd2a84967ea3c11dbb239653a27b63`. Its package, immutable snapshot,
capsule and PREPARATION-RECEIPT remain preserved. This is a separately frozen
pre-launch correction, not an in-place patch or scientific redesign.

## Two corrected validation gaps

1. `candidate_value_data.validate_saved_trajectory` uses the authenticated
   selected-reference goal and saved post-action states. It independently
   reconstructs physical success using the unchanged historical combined
   four-coordinate Euclidean norm **strictly <20**, circular angle **strictly
   <pi/9**, and existing angle-domain/endpoint handling. It checks every success
   flag, terminal behavior, action/state counts and saved target. No initial-state
   success is counted and no value is silently relabelled. Native truncation cannot
   manufacture an early endpoint: the frozen World limit is 300, while H75's
   driver budget can stop at 150 without a native truncation flag. Existing
   requested-state comparison tolerance remains exactly 1e-10.
2. `checked_decoded_bank` recomputes bank actions with the pinned float32
   multiply-then-add decoder. `validate_candidate_delivery` compares the actual
   saved first-chunk actions at anchor t to sampled candidate i exactly. A shorter
   chunk must already have passed the physical/native termination checks.

Collection checks saved bytes after writing each trajectory. Before any fit,
the CPU training loader re-authenticates selected records and validates all saved
training trajectories and candidate/action associations. Ranking validates its
entire saved collection before scoring. Final reporting independently validates
all closed-loop trajectories against their authenticated goals before aggregation.
Runtime assertions, independent saved-file validation and synthetic regression
evidence are distinct; none substitutes for the others.

## Regression evidence

The suite retains 25 prior CVL tests and 22 historical single-anchor regressions,
and adds five focused tests: **52 tests total**. The extended end-to-end fixture
also corrupts a closed-loop trajectory after successful reporting and verifies
that final analysis rejects it despite a renewed valid checksum seal.

Adversarial fixtures include a physically false positive with mutually consistent
flags/target, and the wrong delivered chunk under a valid sampled index. Tests
first verify their ordinary checksum/provenance seal passes, then require the new
semantic check to reject them. False positives are rejected before fitting and
before ranking scores. Positive tests retain first-action/first-chunk success,
final-budget success at both horizons, the exact 2pi observation endpoint, and
strict position/angular boundaries. Fabricated early truncation and action-count
drift are rejected.

Artificial trajectories now contain physically consistent goal-reaching states,
matching flags and correctly decoded candidate actions. They remain geometric
fixtures, not simulator runs or evidence about planner efficacy. Negative branches
run to the original budget instead of using fabricated early truncation.

The attached approval refers to a separate source-review reproducer, but only
the approval text was supplied in its attachment directory. This was requested
asynchronously. The explicitly described rejection cases were reproduced locally;
no unavailable external reproducer is claimed to have been run.

## Unchanged scientific contract and authorized sequence

PROTOCOL.md, RESOURCE-PLAN.md, allocation, sampling, training/evaluation seeds,
model/loss/preprocessing, endpoints, advancement criteria and all job/resource
limits are unchanged. Model code changes only pass the authenticated capsule to
the saved-data validator; no fitting operation or parameter was modified.

After relevant and exported-source tests pass and the new source/capsule hashes
are bound to the researcher's conditional approval: run the two registered real
preflights, then references 1444,1314,767,1481 at H75/H150 as the eight-job technical
tranche inside the allocation. Continue only through the existing technical,
sparse-support and ranking-promise gates. No automatic retry, replacement,
additional job, larger cap, confirmation, GMM extension or SAGE benchmark.

All real failures retain their artifacts and charged resources. A real technical
mismatch or resource overrun must be reported, not patched into a running snapshot.
Launch identities and stage decisions will be recorded separately once executed.
