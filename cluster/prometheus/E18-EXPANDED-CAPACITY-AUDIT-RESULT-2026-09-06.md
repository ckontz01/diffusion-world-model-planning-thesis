# Expanded PushT capacity audit — 6 September 2026

## Decision

The authorized metadata-only audit is complete. The current recorded inventory
supports **300 additional potential P4 episodes**, **zero additional P3 episodes**,
and the previously established **82 P2 episodes**: **382 in total**.

These are capacity counts, not released allocations or a selected confirmation
set. No episode membership list, selected start, image, physical state, action,
model output, or protected outcome is emitted. No allocation was released and
no experiment, model inference, simulation, or Slurm job was launched.

The user rejected a smaller/lower-sensitivity study. This audit does not approve
an N=82 or N=382 fallback. It establishes the available-data constraint for
planning a larger study.

## Counts and incremental exclusions

An episode is length-compatible when its registered length is at least 151,
allowing a common start with inclusive endpoints at start+75 and start+150.
All counts below refer to distinct source episodes, not repeated runs or starts.

| Partition | Length-compatible | Exclusions applied | Remaining potential capacity |
|---|---:|---|---:|
| P2 | 453 | 357 earlier execution-store episodes; 1 earlier development; 7 later development; 6 SAGE paper episodes | 82 |
| P3 | 406 | 19 D2; 126 D3; 97 D4; 164 additional earlier execution-store episodes | 0 |
| P4 | 386 | 16 locked C1; 43 locked I1; 9 earlier P4 query-allocation episodes; 18 SAGE paper episodes | 300 |
| **Total** | **1,245** | Ordered union exclusions, without double counting | **382** |

D2/D3/D4 here denote previously used study memberships. C1/I1 are preserved
locked allocations. Earlier P4 query allocation contains 40 episodes in total,
of which nine meet the current length requirement; they remain excluded.
The table's exclusion counts are incremental in the order shown, not independent
sets to add again.

P3 initially appeared to retain 164 episodes after D2/D3/D4. The older candidate-
execution identifier inventory covers all 164, so none remains under the stated
conservative exposure policy. No outcome arrays were read to establish this.

## SAGE eligibility

| Remaining population | SAGE training | SAGE validation | SAGE test |
|---|---:|---:|---:|
| P2 | 73 | 9 | 0 |
| P3 | 0 | 0 | 0 |
| P4 | 260 | 31 | 9 |
| **Combined** | **333** | **40** | **9** |

Only nine candidates are in the released SAGE test split and survive the other
recorded exclusions. Reserving all nine leaves 373 candidates for a separate
E18-only allocation. Clean SAGE reserves of 50, 100, or 200 cannot be formed
from this audited population. Reserving SAGE training/validation episodes does
not turn them into a training-disjoint evaluation set.

This is split-based eligibility, not independent proof of all checkpoint
training history. Exact LeWM episode-level training exposure remains unknown
for every prospective episode, as in the parent feasibility package.

## Exposure-category checks

The audit separates recorded candidate-execution stores from candidate-pool
inputs. After the other exclusions, **pool-only conservative exclusions are
zero in P2, P3, and P4**. Thus merely relaxing the pool-inventory exclusion does
not recover episodes in this inventory. Execution-store membership is treated
conservatively as exposure; the audit does not assert that a human inspected
every stored result or read those results to determine their completion.

Both source and target/goal episode identifier datasets were read where present.
This prevents accidentally overlooking an episode used as a target rather than
as a start. Relative to the old primary-ID-only projection, the expanded union
causes **zero additional exclusions** in these final counts. The old P2 count
of 82 is independently reproduced, not silently revised.

## Scope, access restrictions, and qualifications

- The global partition/length registry matched SHA-256
  `35cd851464f4d7243c3c07b794f65db0f32caa16bbc787a83dda68388c4898f0`.
- Read 389 recorded identifier projections, with provenance for the relevant
  pool metadata, public SAGE split, and public SAGE evaluation manifests.
- TSV schemas were allowlisted before reading rows. HDF5 reads were restricted
  to named integer episode-ID datasets. No whole outcome-bearing HDF5 file was
  hashed, and no success, cost, score, state, image, or action payload was read.
- Nine legacy non-HDF5 source tables were not opened. Their baseline identities
  remain covered only to the extent certified by the existing partition/exposure
  records; this audit does not newly certify those outcome tables.
- A filename-only search found no D5-named allocation in the canonical manifest
  tree. This agrees with historical records saying D5 was not generated, but it
  does not certify absence of unregistered or differently located allocations.
  No absent membership was invented and no locked allocation was released.
- Counts are conditional on the completeness of the recorded canonical inventory.
  This is an assistant-executed audit under user authorization, not an independent
  university-custodian attestation.
- Prospective field-value validation is still unperformed. The usable count may
  decrease; no physical-value claim is made from metadata alone.
- P4 remains protected. Counting an episode does not authorize using it in an
  evaluation, changing its allocation, or creating a confirmation manifest.

## Verification and execution

A second program re-read all 389 identifier projections and reconstructed the
exclusions using Boolean masks rather than the first program's set ledger.
It reproduced P2=82, P3=0, P4=300, total=382, and SAGE-test=9. It also checked
metadata/projection hashes and the per-category incremental counts.

Nine synthetic privacy/logic tests pass locally and in the existing pinned
remote Python environment. They cover outcome-column rejection, source+target
identifier union, unknown IDs, padding, duplicate exclusion, and non-mutating
ledger logic. No package installation or GPU allocation was required.

The audit executed via the existing WSL-to-Prometheus SSH route, using a CPU
process in the existing container with the project tree mounted read-only.
Only new audit code was staged remotely. Small count/provenance outputs were
saved in the canonical local repository; no raw memberships were copied out.
The three unrelated untracked E12 drafts and historical scientific files remain
unchanged.

Staging: `/lustreFS/data/superworld/ckontzias/thesis/staging/e18-expanded-capacity-9973e46`.
Initial scope commit: `9973e46`; audit-source commit: `60c3753`.

Artifacts:
- `e18-expanded-capacity-evidence/CAPACITY.json`
- `e18-expanded-capacity-evidence/VERIFICATION.json`
- `e18-expanded-capacity-evidence/REMOTE-TESTS.txt`
- `e18_expanded_capacity_audit.py`
- `verify_e18_expanded_capacity.py`
- `test_e18_expanded_capacity_audit.py`

## Implication for the larger study

Even prospective release and successful value validation of all 300 new P4
candidates would yield at most 382 under this ledger. Relative to planning
sizes of 400/600/800, the corresponding minimum shortfalls are 18/218/418
independent episodes, before any SAGE reserve. This is arithmetic, not a claim
that any one of those sizes guarantees the desired statistical power.

The parent package's 400/600/800 power scenarios are unchanged. Do not inflate
sample size by counting repeated starts or seeds as new independent episodes.
A larger robustly powered study therefore needs a separately justified source
of independent evaluation episodes, or a genuinely new provenance certificate
that establishes additional unused data. No such data collection is launched
by this audit. A clean large comparison with released SAGE checkpoints also
requires substantially more training-disjoint episodes than the nine found here.
