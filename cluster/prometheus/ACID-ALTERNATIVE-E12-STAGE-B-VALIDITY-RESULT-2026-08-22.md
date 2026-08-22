# E12 matched-PRISM Stage-B validity result

Date completed: 2026-08-22

Native Stage-A array: `298550` (`12/12` completed, all exit `0:0`)

PRISM-DP Stage-B array: `298505` (`9/9` completed, all exit `0:0`)

PriorHead Stage-B array: `298504` (`18/18` terminated with complete summaries)

Validity-audit job: `298552` (completed `0:0` in `00:00:05`)

Frozen decision: **`blocked_by_stage_b_validity_failure`**

Stage C authorized: **false**

Stage D authorized: **false**

D4 generated or consumed: **no**

## Frozen verdict

E12 stopped at its preregistered P1 validity gate. All nine disclosed
PRISM-DP reconstruction models passed their frozen checks, and both Gaussian
PriorHead variants passed for every PushT and Cube seed. Both PriorHead
variants failed the required 15% validation-MSE improvement on every Reacher
seed. The final audit therefore recorded:

- `status = blocked`;
- `stage_b_passed = false`;
- `stage_c_authorized = false`; and
- `stage_d_authorized = false`.

Section 9 of the frozen protocol requires any learned-component validity
failure to be reported without consuming D4. No Stage-C efficiency curve,
Stage-D closed-loop arm, D4 manifest, or D4 result was produced. Removing
Reacher, weakening the 15% threshold, selecting a different checkpoint, or
continuing with only the components that passed would be a post-outcome
rescue and is prohibited for E12.

This is a **pre-evaluation validity failure**, not evidence that velocity
diffusion beats PRISM, that PRISM beats velocity diffusion, or that PRISM
fails in general.

## Provenance and integrity

- Frozen protocol:
  `ACID-ALTERNATIVE-E12-PRISM-MATCHED-UNTOUCHED-D4-PROTOCOL-2026-08-20.md`.
- Protocol SHA-256:
  `08cbe26c3186f06d6731defc8fc66f63c2a55c1102f6d089f1e286176f9ed927`.
- Immutable Stage-B training snapshot:
  `/lustreFS/data/superworld/ckontzias/thesis/snapshots/gdp-cem-e12-stage-b-e2faf062f3eec188`.
- Training source-manifest SHA-256:
  `e2faf062f3eec188b8b78d167f6e75de29b5ff64446843c04696ed53d4bd856b`.
- Final audit:
  `/lustreFS/data/superworld/ckontzias/thesis/results/acid-alternative/gdp-cem-e12/stage-b/STAGE-B-AUDIT.json`.
- Final audit checksum file:
  `/lustreFS/data/superworld/ckontzias/thesis/results/acid-alternative/gdp-cem-e12/stage-b/STAGE-B-AUDIT.sha256`.
- The audit found exactly 27 expected artifacts and audited all 27. Twenty-one
  were valid and six were invalid.
- All nine PRISM-DP `summary.json`, `best.pt`, `training.jsonl`, and
  `provenance.txt` files passed their recorded SHA-256 checks. The final audit
  JSON passed its recorded checksum.
- Every training and audit Slurm element exited `0:0`; no validity failure was
  inferred from a crash, timeout, missing output, or non-finite value.
- Every recorded runtime used `gpu09.cluster` with an NVIDIA RTX 6000 Ada.
- The audit records `d3_outcomes_read = false`, `d4_outcomes_read = false`,
  and `protected_p4_c1_i1_read = false`.

The implementation corrections made before this final execution are recorded
separately in
`ACID-ALTERNATIVE-E12-IMPLEMENTATION-CHANGELOG-1-2026-08-20.md`. None changed
a task, seed, model recipe, checkpoint rule, validity threshold, claim gate,
or evaluation budget.

## Stage A: native public-artifact sanity

Stage A used the official pinned PRISM PushT and Cube bundles, K=128, 30 MPPI
iterations, seeds `{0, 1, 42}`, and 50 episodes per cell. All 12 final cells,
their starts, statuses, source/protocol hashes, and output checksums passed.

| Task | Mode | E12 seed rates | E12 mean | Released mean | Difference |
|---|---|---|---:|---:|---:|
| PushT | Vanilla MPPI | 66%, 54%, 64% | 61.3% | 57.0% | +4.3 pp |
| PushT | PRISM-PoG-MPPI | 90%, 92%, 88% | 90.0% | 88.7% | +1.3 pp |
| Cube | Vanilla MPPI | 48%, 40%, 44% | 44.0% | 44.0% | 0.0 pp |
| Cube | PRISM-PoG-MPPI | 86%, 78%, 70% | 78.0% | 79.3% | -1.3 pp |

These values are close to the released sanity figures and support correct
integration of the pinned native artifacts. They are **not matched claim
data**: the released bundles, model/data split, and checkpoints differ from
E11, and Reacher has no corresponding released bundle in this test.

## Stage B: matched P1 validity

The three methods were trained separately for PushT, Reacher, and Cube with
model seeds `6101`, `6102`, and `6103`.

| Learned component | PushT | Reacher | Cube | Overall |
|---|---:|---:|---:|---:|
| PRISM PriorHead, horizon-25 goal | 3/3 pass | **0/3 pass** | 3/3 pass | 6/9 pass |
| PRISM PriorHead, episode-end goal | 3/3 pass | **0/3 pass** | 3/3 pass | 6/9 pass |
| Disclosed PRISM-DP reconstruction | 3/3 pass | 3/3 pass | 3/3 pass | 9/9 pass |
| **All artifacts** | **9/9 pass** | **3/9 pass** | **9/9 pass** | **21/27 pass** |

### Reacher PriorHead failure

The failing models were finite, produced nonconstant sigmas above the floor,
and wrote complete checkpoints and traces. They failed only the frozen
requirement that validation mean MSE improve by at least 15% over the initial
model:

| Variant | Seed 6101 | Seed 6102 | Seed 6103 | Required |
|---|---:|---:|---:|---:|
| Horizon-25 goal | 4.188% | 4.176% | 4.236% | at least 15% |
| Episode-end goal | 0.982% | 0.932% | 0.750% | at least 15% |

The failure repeats across both goal-label conventions and all three model
seeds. PushT and Cube passed for both conventions and every seed. The pinned
official PRISM source remained at commit
`baa0eb95efb812196b68796c258b1f0cf10b7625`, so this outcome is not explained
by silently switching upstream versions.

### PRISM-DP reconstruction validity

All nine DP reconstructions passed the fixed finiteness, P1 episode-disjoint,
documented-parameter-count, and minimum 5% validation-improvement rules.

| Task | Relative validation-MSE improvements across seeds |
|---|---|
| PushT | 98.252%, 98.458%, 98.160% |
| Reacher | 72.583%, 75.776%, 70.650% |
| Cube | 93.383%, 93.062%, 93.103% |

The public PRISM repository omits the DP model, scheduler, and policy files.
Consequently these models remain a disclosed reconstruction rather than an
official PRISM-DP reproduction, even though they passed E12's internal
validity checks.

## Failure classification

The six invalid PriorHeads are treated as a **frozen model/data validity
outcome**, not an execution failure eligible for an identical rerun. The
result is replicated across seeds, isolated to Reacher, shared by both goal
conventions, and accompanied by valid finite artifacts. The audit and
changelog contain no evidence of a missing file, corrupt hash, data-overlap
violation, source-version mismatch, or failed numerical-parity check that
would authorize an implementation correction.

This classification matters: rerunning from another initialization, relaxing
the threshold, changing labels, enlarging the architecture, or deleting the
task after seeing these values would tune to Stage-B outcomes.

## Scientific interpretation

E12 established three useful facts:

1. The official native PRISM artifact stack was integrated successfully on
   PushT and Cube.
2. The disclosed PRISM-DP reconstruction trained validly on all three matched
   tasks and seeds.
3. The published-equation Gaussian PriorHead recipe did not meet E12's
   predeclared matched-data validity requirement on Reacher, under either goal
   convention.

It did **not** produce an efficacy comparison between the E11 velocity model
and PRISM-DP or PRISM-PoG. There are no E12 success rates, confidence
intervals, latency contrasts, or superiority results from P2 or D4. The
positive E11 untouched-D3 result remains unchanged, but its direct comparison
with the closest PRISM-style competitors remains unresolved.

For publication, E12 belongs in the reproducibility/limitations record: the
native artifact integration reproduced closely, a matched DP comparator was
constructed successfully, and the broader conjunctive comparison stopped
before evaluation because one comparator family was invalid on one required
task. It must not be presented as evidence favorable to the proposed method.

Any later DP-only comparison, revised Reacher prior, task-set change, or new
holdout experiment requires a separately frozen protocol and cannot be called
a continuation or rescue of E12.
