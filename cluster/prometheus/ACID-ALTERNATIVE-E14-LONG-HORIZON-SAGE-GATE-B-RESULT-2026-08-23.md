# E14 long-horizon diffusion and SAGE-reconstruction Gate-B result

Date completed: 23 August 2026

Role: P1-validation development only; not confirmation evidence

Frozen decision: **`stop_before_gate_c_no_diffusion_endpoint_passed_gate_b`**

Gate C authorized: **false**

D5 authorized, generated, or consumed: **no**

## Verdict

E14 ended at its preregistered offline proposal-validity gate. Neither of the
two diffusion endpoints was eligible for the P2 closed-loop Gate C, so E14 did
not produce a long-horizon success comparison with released Base CEM or the
published-equation SAGE reconstruction.

The result is more informative than the binary stop alone suggests:

- Variable-duration action diffusion (VAD) beat its capacity-matched Gaussian
  on both equal-task offline metrics for every model seed. The direction also
  held separately on PushT and Cube at all three local durations for every
  seed, and the fixed-seed true model beat both shuffled-goal and unconditional
  diffusion controls.
- VAD nevertheless failed the conjunctive bank-validity gate. All banks were
  finite and retained 300 unique candidates, but the maximum robust-boundary
  fraction exceeded the frozen 25% ceiling on Cube for all three seeds.
- Coupled subgoal-action diffusion (CVD) strongly improved oracle action
  coverage, generated-local error, and terminal consistency, but its selected
  true-local terminal cost was worse than Gaussian for every seed. It also
  failed the per-task duration-direction and boundary-validity gates.

The honest interpretation is therefore: **VAD learned a strong offline
long-horizon proposal mechanism, but E14 did not establish that its proposal
banks were sufficiently interior to support a valid closed-loop test.** This
does not overturn E11 or E13, and it does not support a SAGE efficacy claim.

## Frozen gate outcomes

| Gate-B requirement | VAD | CVD |
|---|---:|---:|
| Every bank finite, at least 285 unique candidates, and at most 25% boundary fraction | **Fail** | **Fail** |
| Better equal-task oracle action MSE and true-local Le-WM cost than matched Gaussian for every seed | Pass | **Fail** |
| Direction holds on each task for at least two of three durations for every seed | Pass | **Fail** |
| True fixed-seed model beats shuffled-goal and unconditional controls | Pass | Pass |
| Better local-latent error and terminal consistency than Gaussian | Not applicable | Pass |
| Eligible for Gate C | **No** | **No** |

The gate was conjunctive. VAD's positive performance comparisons could not
override its proposal-bank failure, and CVD's additional diagnostic wins could
not override its matched-planning-cost and bank failures.

## VAD results first, by task

The following are equal-cell P1-validation means. Oracle action MSE is the
best expert-action error among 300 proposals; true-local terminal cost is the
Le-WM cost of the planner-selected option against the recorded local target.
Lower is better for both.

| Task | Seed | VAD action MSE | Gaussian action MSE | VAD terminal cost | Gaussian terminal cost | Maximum VAD boundary fraction | Bank bound |
|---|---:|---:|---:|---:|---:|---:|---:|
| PushT | 6101 | **0.102771** | 0.154764 | **24.0462** | 29.7847 | 17.2250% | Pass |
| PushT | 6102 | **0.102723** | 0.153548 | **24.1274** | 29.7036 | 16.7889% | Pass |
| PushT | 6103 | **0.103833** | 0.154463 | **24.2826** | 29.4881 | 15.8333% | Pass |
| Cube | 6101 | **0.142857** | 0.334172 | **56.8277** | 61.0671 | **27.1733%** | **Fail** |
| Cube | 6102 | **0.144321** | 0.333277 | **56.4776** | 61.1129 | **36.3778%** | **Fail** |
| Cube | 6103 | **0.141155** | 0.333559 | **56.9014** | 61.1807 | **35.4711%** | **Fail** |

All six VAD task-seed banks were finite and had a minimum of 300 unique
rounded candidates. The failure is isolated to the predeclared boundary
ceiling on Cube; PushT stayed below it for every seed. Because the rule says
**every** bank must be within bounds, one Cube failure would have stopped VAD,
and all three Cube seeds failed independently.

Equal-task comparisons reproduce the audit decision:

| Seed | VAD action MSE | Gaussian action MSE | VAD terminal cost | Gaussian terminal cost | Matched comparison |
|---:|---:|---:|---:|---:|---:|
| 6101 | **0.122814** | 0.244468 | **40.4370** | 45.4259 | Pass |
| 6102 | **0.123522** | 0.243412 | **40.3025** | 45.4083 | Pass |
| 6103 | **0.122494** | 0.244011 | **40.5920** | 45.3344 | Pass |

For every seed and both tasks, VAD beat Gaussian separately at `tau=15`,
`tau=20`, and `tau=25`. On the fixed control seed, true VAD also beat both
nulls:

| Family | Oracle action MSE | True-local terminal cost |
|---|---:|---:|
| **True VAD** | **0.122814** | **40.4370** |
| Shuffled-goal VAD | 0.132121 | 54.5481 |
| Unconditional VAD | 0.128220 | 53.6346 |

These controls support genuine far-goal conditioning. They do not nullify the
bank-validity failure or authorize closed-loop evaluation.

## CVD result

CVD's 300 samples covered the recorded actions much better than its Gaussian
control, but the option selected using sampled-subgoal consistency ended
farther from the recorded true local latent. The latter is one of the two
matched metrics required by the frozen gate.

| Seed | CVD action MSE | Gaussian action MSE | CVD terminal cost | Gaussian terminal cost | Matched comparison |
|---:|---:|---:|---:|---:|---:|
| 6101 | **0.159314** | 0.364849 | 33.8979 | **32.3126** | Fail |
| 6102 | **0.158415** | 0.366858 | 33.8758 | **32.7027** | Fail |
| 6103 | **0.159132** | 0.367778 | 34.0606 | **32.9087** | Fail |

CVD did pass its architecture-specific checks:

| Seed | CVD local error | Gaussian local error | CVD consistency | Gaussian consistency |
|---:|---:|---:|---:|---:|
| 6101 | **0.03755** | 0.16247 | **3.9048** | 29.1582 |
| 6102 | **0.03845** | 0.15971 | **3.9819** | 29.1664 |
| 6103 | **0.03897** | 0.16174 | **4.0415** | 29.7256 |

Its fixed-seed true model also beat shuffled and unconditional controls. But
the per-task direction rule failed: seed 6101 won only Cube at `tau=25` and no
PushT duration; seeds 6102 and 6103 won only `tau=25` on each task. CVD's
maximum boundary fraction was 37.9000%, above the same 25% ceiling, while its
minimum unique-candidate count remained 300.

## SAGE reconstruction status

The registered published-equation SAGE subgoal and option-prior training
completed, and the normalized model tree passed its recorded checksums. It was
not run in closed loop. Under the frozen protocol, SAGE, released Base CEM,
and eligible diffusion/Gaussian endpoints enter together only at Gate C. With
no eligible diffusion endpoint, running just the comparator would not answer
E14's registered question and would violate the stage dependency.

Nothing in this result measures SAGE success, establishes parity with SAGE,
or shows that SAGE fails. The comparator remains a reconstruction because no
official SAGE code or checkpoint was available at the protocol freeze.

## Execution and audit integrity

- The replacement 32-cell Gate-B smoke array `299068` completed successfully.
- The full 32-cell Gate-B array `299069` completed successfully; every cell
  exited `0:0`.
- Analyzer `299070` loaded and analyzed the complete inputs, then failed while
  serializing a NumPy boolean to JSON. This was a technical output-layer error,
  not a scientific gate result.
- Replacement serializer job `299135` loaded the unchanged scientific analyzer
  dynamically, verified its SHA-256, converted NumPy scalar values only at the
  final JSON boundary, and completed `0:0`.
- The final `sha256.txt` verifies both `GATE-B-AUDIT.json` and
  `SERIALIZER-PROVENANCE.txt`.

Earlier scheduler, CRLF-path, checksum-parser, and wrapper corrections are
recorded in
[the implementation decisions](ACID-ALTERNATIVE-E14-IMPLEMENTATION-DECISIONS-1-2026-08-23.md)
and
[the serialization erratum](E14-GATE-B-SERIALIZATION-ERRATUM-2026-08-23.md).
They did not change tasks, endpoints, data, seeds, budgets, checkpoints,
metrics, or gates. One non-gating smoke diagnostic was exposed while
diagnosing a wrapper exit-127 failure; the full Gate-B outputs did not yet
exist, and nothing scientific was changed in response.

## Provenance

| Artifact | SHA-256 |
|---|---|
| Frozen E14 protocol | `9909cd1357638ec4bcebd9a8c84a94f266d9a82e7003b902b7b2a0c65eea1be6` |
| Original offline scientific snapshot | `bc27ec5c93dfae6681c149fd755d93742a0678583787bad7e3fcd43300d59cae` |
| Training source manifest | `99f92cbe3c735a999866b52103241633ec80a7dffeca5217c07b0ec5590176cd` |
| Final Gate-B wrapper/Gate-C snapshot | `9e47eeb2b957039e7f952528b53dbaeca165120ee10b57f0691832907265e8ad` |
| Serializer snapshot | `c7d5a65e87acb2cdff65ad4139c7641080db3b72ff3340bd405472b63e66f8f9` |
| Unchanged scientific analyzer | `5362788ed566a5f2f876b63ff004ba878bd5278d28ed323408431f02d3572299` |
| Full normalization audit | `985454c195d2f785c665eb59d81efadb789512a4d03f3e44ffa3ac24140b6b40` |
| Final `GATE-B-AUDIT.json` | `dcbb582cde4cc7a27dfecd3bc759143961aa3014c0657060da0ae795394d4d4b` |
| Serializer provenance | `58d77083080e097bc5459f1262ef91d3f0b3d70f9e2d3d29c4b68efbfa7d8bd0` |

The immutable scientific snapshot is:

```text
/lustreFS/data/superworld/ckontzias/thesis/snapshots/gdp-cem-e14-offline-bc27ec5c93dfae66
```

The checksum-verified final audit is:

```text
/lustreFS/data/superworld/ckontzias/thesis/experiments/gdp-cem-e14/development-run-20260823-99f92cbe/offline-retry2-9e47eeb2/gate-b-json-c7d5/GATE-B-AUDIT.json
```

The audit records `status = ok`, `artifact_count = 32`,
`claim_allowed = false`, `d3_metric_read = false`,
`d4_metric_read = false`, `d5_read = false`, and
`protected_p3_p4_c1_i1_read = false`.

## Scientific implication and next legitimate study

E14 adds a useful boundary to the paper:

1. The E11 velocity-diffusion mechanism extends offline to variable durations
   and far goals under VAD, with large and seed-consistent advantages over a
   matched Gaussian and correctly ordered null controls.
2. This study does not show that VAD works in long-horizon closed loop. The
   predeclared integrity gate stopped that inference before P2.
3. Coupling subgoals and actions in CVD improves internal consistency but does
   not improve the registered planner-selected true-local cost; CVD should not
   be the next primary endpoint.
4. E11 and E13 remain the confirmatory paper core. E14 is a development result
   and limitation, not a replacement headline.

A future E15 may redesign VAD's bounded action parameterization to reduce
Cube boundary saturation, but it must be a separately frozen, outcome-informed
development study. It should measure both exact clipping and near-boundary
mass so a smooth squashing transform cannot merely game the old statistic,
use fresh development queries, and repeat controls before any new closed-loop
or confirmation authorization. The E14 25% threshold must not be relaxed or
reinterpreted after seeing this result.
