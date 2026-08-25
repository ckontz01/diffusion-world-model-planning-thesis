# E15 boundary-aware long-horizon Gate-B result

Date completed: 25 August 2026

Role: P1-validation development only; not confirmation evidence

Frozen decision: **`stop_before_gate_c_frozen_gate_b_failed`**

Gate C authorized: **false**

D5 authorized, generated, or consumed: **no**

## Verdict

E15 solved the specific implementation-validity problem that stopped E14, but
it did not pass the preregistered diffusion-mechanism gate. The common smooth
action representation produced legal, finite, diverse proposal banks for all
22 trained endpoints and controls. The direct eight-mode GMM also passed every
registered structural check. Those two parts of Gate B passed cleanly.

Boundary-aware VAD continued to show a strong aggregate advantage over its
matched diagonal Gaussian: for every model seed it had lower equal-task
best-of-300 expert-action error and lower equal-task planner-selected true-local
Le-WM cost. The task-first result was not uniform, however. VAD beat Gaussian
on both metrics at all three durations on Cube, but on PushT its better action
coverage did not translate into a better selected true-local terminal cost at
any duration. VAD therefore failed the frozen per-task two-of-three-duration
requirement for every seed.

The conditioning controls produced a second, independent failure. True VAD
beat shuffled-goal VAD, but it did not beat unconditional VAD on both primary
metrics: unconditional VAD had slightly lower best-of-300 action error, and
the required per-task duration direction also failed. The frozen conjunctive
Gate B therefore stopped E15 before any closed-loop P2 comparison.

The honest interpretation is: **the E15 transform fixed E14's illegal-action
and clipping problem, and VAD remained useful on Cube, but fresh P1 evidence
did not establish that far-goal-conditioned diffusion supplied the required
task-robust long-horizon mechanism.** E15 contains no SAGE efficacy result, no
closed-loop GMM comparison, and no D5 confirmation evidence.

## Frozen gate outcomes

| Gate-B requirement | Outcome |
|---|---:|
| All 22 VAD, Gaussian, GMM, and null banks pass common integrity | **Pass** |
| All six task/seed direct-GMM banks pass eight-mode structural validity | **Pass** |
| VAD beats Gaussian on both equal-task primary metrics for every seed | **Pass** |
| Both VAD-over-Gaussian directions hold on each task for at least two durations | **Fail** |
| True VAD beats shuffled-goal VAD on the registered comparisons | **Pass** |
| True VAD beats unconditional VAD on the registered comparisons | **Fail** |
| Gate C eligible | **No** |

The gate was conjunctive. Passing bank integrity, GMM structure, and the pooled
matched comparison could not override either diffusion-mechanism failure.

## Boundary-aware representation result

The redesign achieved its intended technical purpose:

- all 22 banks were finite;
- the minimum rounded full-trajectory candidate count was 300, above the
  frozen minimum of 285;
- the maximum strict legal out-of-bounds fraction was exactly zero;
- the maximum exact `-1/+1` boundary fraction was exactly zero;
- every expert reference matched the immutable data-preflight manifest; and
- every task/duration expert-relative near-limit and low-Jacobian check passed.

This resolves the ambiguity left by E14: the prior Cube failure was not an
unavoidable consequence of using expert-like boundary actions. A smooth,
legality-preserving representation can produce fully valid banks. E15 still
failed for scientific mechanism reasons after that confound was removed.

## VAD versus matched Gaussian, task first

Values are equal-cell P1-validation means. Action MSE is best-of-300 error to
the representable expert action. Terminal cost is the Le-WM cost of the option
selected against the recorded true local latent. Lower is better for both.

| Task | Seed | VAD action MSE | Gaussian action MSE | VAD terminal cost | Gaussian terminal cost | Both metrics won? |
|---|---:|---:|---:|---:|---:|---:|
| PushT | 7201 | **0.005219** | 0.007870 | 31.3291 | **30.0614** | **No** |
| PushT | 7202 | **0.005211** | 0.007731 | 31.4069 | **29.8552** | **No** |
| PushT | 7203 | **0.005256** | 0.007775 | 31.2271 | **29.7711** | **No** |
| Cube | 7201 | **0.025043** | 0.059990 | **64.1842** | 73.9156 | Yes |
| Cube | 7202 | **0.025006** | 0.059976 | **64.3719** | 74.0543 | Yes |
| Cube | 7203 | **0.024867** | 0.059551 | **64.2954** | 73.8201 | Yes |

For Cube, the two-metric direction held at `tau=15`, `20`, and `25` for every
seed. For PushT, it held at none of those durations for any seed because the
terminal-cost direction was consistently unfavorable. This is why a positive
equal-task average was insufficient.

The equal-task aggregation nevertheless records the size and consistency of
the overall matched effect:

| Seed | VAD action MSE | Gaussian action MSE | VAD terminal cost | Gaussian terminal cost |
|---:|---:|---:|---:|---:|
| 7201 | **0.015131** | 0.033930 | **47.7566** | 51.9885 |
| 7202 | **0.015108** | 0.033854 | **47.8894** | 51.9547 |
| 7203 | **0.015062** | 0.033663 | **47.7612** | 51.7956 |

## Conditioning controls

Seed 7201 was frozen for the shuffled-goal and unconditional controls.

| Family | Equal-task action MSE | Equal-task terminal cost | True VAD beats it on both? |
|---|---:|---:|---:|
| **True VAD** | 0.015131 | **47.7566** | — |
| Shuffled-goal VAD | 0.015658 | 61.1210 | Yes |
| Unconditional VAD | **0.014670** | 59.2136 | **No** |

True VAD's much lower terminal cost than either null shows that the far goal
affected which option was selected. The unconditional model's slightly better
oracle action coverage shows that conditioning was not uniformly beneficial.
Under the frozen rule, both primary metrics and the task-duration directions
had to improve. True VAD beat the shuffled control on that full rule, but did
not beat the unconditional control: Cube had no winning duration and PushT
won only `tau=15`.

## Direct-GMM control

Every direct-GMM task/seed bank passed the registered structural checks:
nontrivial mass in all eight modes, at least six posterior-winning modes, and
sufficient normalized prior entropy. The GMM was deliberately not required to
beat VAD at Gate B, so no efficacy conclusion should be drawn from its offline
ranking. Its purpose was to enter the matched closed-loop comparison without
performance-based filtering if the complete gate passed. Because VAD's
mechanism gate failed, that comparison was not run.

## Execution and audit integrity

- Full 22-cell training array `299201`, training smoke array `299217`, Gate-A
  validator `299218`, full sealed Gate-B evaluation array `299219`, and the
  corrected post-barrier analyzer `299257` all completed successfully.
- Every `299219` evaluation cell exited `0:0` before the aggregate was opened.
- Pending analyzer `299220` was cancelled before execution when a source audit
  found that its common-integrity loop omitted the two VAD null banks. The
  correction applied the already frozen thresholds to all 22 unchanged banks;
  no metric, threshold, model, sample, or comparison direction changed.
- `sha256 -c` verifies both final Gate-B files. The task-first TSV contains 990
  data rows plus its header, and the audit contains 22 task/condition/seed
  aggregates.
- The audit records `status = ok`, `artifact_count = 22`, common-integrity bank
  count 22, `gate_b_passed = false`, and `claim_allowed = false`.
- The audit also records `d3_metric_read = false`, `d4_metric_read = false`,
  `d5_read = false`, `p2_read = false`, and
  `protected_p3_p4_c1_i1_read = false`.

The protocol-conformance correction is documented in
[the E15 implementation decisions](E15-IMPLEMENTATION-DECISIONS-1-2026-08-25.md).

## Provenance

| Artifact | SHA-256 |
|---|---|
| Frozen E15 protocol | `bcbe66b3b7b2635473d5bd98b3a450c5e136879f275ac3a0ddd6d4bdb254755b` |
| Training source manifest | `ebd6109b65528f6b201c2de7deac29888a25e570f60d11ea9e6298374b61301c` |
| Full-evaluation source manifest | `d970a18e4921eb2c4d3d2ed7f6fdd295b583320b43fef1a88908000d82a8a22e` |
| Corrected analyzer source manifest | `e0fb137d34750b0c1d7e8c239d5a7b3d9c84b2c50c81d870f12aa04ff6ccc039` |
| Corrected analyzer file | `22a57711c47122fdef9773b95c7f96c88610afc3fa12cee972a0a9d1cc1a658f` |
| Gate-A audit | `704d93286bce622bcf3b68dedd1c0840acc78a5ffc3e954a888b259482c59674` |
| Final Gate-B audit | `a56f6a8b4c727f889beee99a982ee8f35f49f84fdc51d7367bb2228e9f00c44a` |
| Task-first per-cell TSV | `9c03694388a2aa350bca353136879f6320d037ffbc9cbfd0697caa9aa0c86084` |

The checksum-verified final audit is:

```text
/lustreFS/data/superworld/ckontzias/thesis/experiments/gdp-cem-e15/development-run-20260825-ebd6109b/offline-e0fb137d/gate-b/GATE-B-AUDIT.json
```

## Scientific implication and next legitimate work

E15 closes the planned long-horizon rescue line:

1. The boundary-aware transform is technically valid and should replace hard
   clipping in any future use of these proposal families.
2. VAD's positive equal-task result is driven by a strong Cube effect. PushT
   did not improve on the planner-selected local target, and the unconditional
   null prevented a clean far-goal-conditioning claim.
3. No closed-loop comparison with the published-equation SAGE reconstruction
   or the direct GMM was authorized. The repository therefore still makes no
   claim that diffusion matches or beats SAGE in long-horizon planning.
4. E11 and E13 remain the paper's confirmatory core. E14 and E15 should be
   reported as development evidence showing both the promise and the limit of
   extending the method to SAGE-style horizons.
5. The preregistered response to this failure is to stop, not to tune another
   boundary transform, endpoint, null rule, or Gate-B threshold. D5 remains
   sealed. The next work is manuscript construction, the ACID fidelity
   appendix, and reproducibility packaging rather than an E16 rescue.
