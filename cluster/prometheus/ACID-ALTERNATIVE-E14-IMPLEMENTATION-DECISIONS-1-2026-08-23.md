# E14 pre-outcome implementation decisions 1

Date fixed: 23 August 2026  
Status: pre-outcome implementation record. Initial decisions were fixed after
cache construction and static tests; the explicitly labelled errata and
aggregation details below were fixed before any Gate-B or Gate-C metric was
generated or read.

This document resolves implementation details left open by the frozen E14
development protocol. It does not change an endpoint, task, horizon, gate,
seed, candidate budget, or confirmation rule.

## Cache artifacts

Both task caches completed successfully and contain 400,000 P1-train and
40,000 episode-disjoint P1-validation rows, balanced across the 45 valid
`(delta,tau)` cells.

| Task | Cache SHA-256 | Manifest SHA-256 |
|---|---|---|
| PushT | `ff102572c7eed39134002aa90af0bd324df1d1312522c994d19206ec5ac6bac9` | `93a20e7d46e5142e2231630ae74caeec4638ad8aaeab95ef5b4cbd8513b90c54` |
| Cube | `b7b4b63669d6eb05ccbc9cd7cc9a40e401f1a36ef0bdd9b61724dceb988b15f6` | `4385e22fcf199922d954a137817d283e829b345e66444a8644776ed592ef888e` |

Every downstream job must verify those hashes and the upstream latent-cache
hash before loading arrays.

## Endpoint optimization and controls

- VAD and CVD retain E11's 30,000 updates, batch 1,024, 1,000-step linear
  warm-up followed by cosine decay from `2e-4`, AdamW weight decay `1e-4`,
  BF16, gradient clipping 1.0, and EMA 0.999.
- Masked objectives are normalized per row by the number of active dimensions,
  so `tau=25` does not receive more weight merely because it has more active
  action coordinates than `tau=15`.
- Checkpoint selection uses one deterministic 8,192-row subset of P1-validation
  per task and model seed. Gate B uses all 40,000 validation rows; checkpoint
  rows do not become a substitute for Gate B.
- Shuffled-goal controls use a deterministic fixed-point-free permutation
  within each P1 role, `delta`, and `tau` cell. Thus shuffling cannot leak the
  duration or horizon label.
- The unconditional diagnostic is a separately trained capacity-identical
  diffusion model whose far-goal branch is always disabled. It is not merely a
  second sampling setting selected after seeing the true model.

## Gate-B metric interpretation and aggregation

- `best-of-300 action error` means the minimum active-coordinate primitive-
  action MSE to the recorded expert option among all 300 candidates. It is an
  oracle coverage diagnostic, not the planner's selected-action error.
- `Le-WM terminal cost` means the squared latent distance between Le-WM's
  terminal prediction for the planner-selected option and the recorded true
  local latent at `t+tau`. VAD selects against the far goal; CVD selects against
  its paired sampled local latent. The evaluation therefore reports selection
  cost, far-goal cost, and true-local cost separately and uses true-local cost
  for the frozen Gate-B comparison.
- CVD local-latent error is computed in the P1-train-standardized latent space.
  Its additional terminal-consistency metric is Le-WM terminal squared distance
  to each option's paired sampled local latent, minimized by the CVD selector.
- A cell metric is the arithmetic mean over rows in one task/`delta`/`tau`
  cell. Per-task/per-`tau` direction is the equal-`delta` mean of its valid
  cells. The equal-task headline is the arithmetic mean of two task values,
  each itself the equal-cell mean over that task. This prevents Cube, PushT, a
  duration, or a horizon from dominating through row counts.
- Candidate uniqueness rounds only active standardized action coordinates to
  `1e-4`; padded coordinates are excluded. Boundary fraction is measured after
  applying the frozen P1-train 0.1%/99.9% robust action bounds and likewise
  excludes padding.

## Published-equation SAGE reconstruction

- The subgoal decoder feed-forward dimension is 2,816. This yields 20,434,112
  parameters on PushT, versus 20.71M reported by SAGE.
- The option decoder feed-forward dimension is 2,048. With the disclosed
  trajectory-GMM interpretation it yields 13,072,040 parameters on PushT,
  versus 13.61M reported by SAGE. Cube's larger primitive-action dimension is
  reported separately rather than hidden by a shared count.
- The eight Gaussian mixture weights are trajectory-level weights. Each of
  five learned queries emits one five-primitive-action block for every mode;
  a single sampled mode therefore selects a complete 25-step option.
- SAGE training uses the paper's fixed learning rate, batch, epochs, BF16,
  gradient clipping, and AdamW settings. The subgoal checkpoint is selected by
  its disclosed combined validation loss. The option checkpoint is selected
  by validation trajectory-mixture NLL.
- The option prior always receives the frozen selected subgoal generator's
  prediction, never the ground-truth local latent.

## Information discipline

The actual-cache/GPU preflight may inspect shapes, hashes, finite gradients,
parameter counts, and candidate-interface compatibility. It may not report or
select a method using a training objective, offline proposal metric, or
closed-loop outcome. E14 remains development-only and cannot authorize D5
without passing the frozen Gates A--C.

## Pre-execution submission erratum

The first submission attempt created the identifier-only manifests but Slurm
rejected every job before assigning an ID because the scripts requested QoS
`normal` on partition `a6000`. Prometheus requires `normal-a6000`, as used by
the earlier thesis GPU jobs. The three E14 GPU scripts were corrected and a
new immutable source snapshot is required. No preflight, training, validation,
or performance result existed when this scheduler-only error was corrected.

The next actual-cache preflight reached the SAGE GMM sampler on both tasks and
then stopped because PyTorch 2.5 forbids CUDA `multinomial` under strict
deterministic-algorithm mode. All dependent training arrays were consequently
blocked before starting. The sampler now draws its eight-way categorical mode
and Gaussian noise from an explicitly seeded CPU generator and transfers the
small completed bank to the GPU. This preserves strict reproducibility instead
of weakening the global determinism setting. No performance-bearing result
existed when this implementation-only correction was made.

## Pre-outcome closed-loop schedule interpretation

The following choices were recorded while endpoint training was still running,
before Gate B or any E14 closed-loop outcome was available:

- Within one published schedule cycle, the scalar `delta` passed to every
  learned proposal is the scheduled remaining horizon,
  `H - elapsed_environment_steps`. It is not rounded or clipped to the
  cache grid. Some schedules therefore query intermediate delta values that
  lie between the frozen training offsets; the sinusoidal scalar conditioning
  handles these as interpolation points. The same rule applies to the SAGE
  reconstruction and both learned endpoint families.
- Cube executes the published schedule once, using its `H`-step environment
  budget. PushT receives the published `2H` budget, so the complete schedule is
  repeated once after the first `H` steps while retaining the same dataset
  goal. The remaining-delta clock restarts at `H` for this second schedule
  cycle. This deterministic rule uses the complete budget and is identical for
  every arm.
- Released Base CEM and the SAGE reconstruction each score 30 populations of
  300 candidates at every stage. VAD, CVD, and their matched Gaussian controls
  score one population of 300. No warm start crosses a stage boundary.

## Pre-Gate-B line-ending erratum

The frozen identifier-only training TSVs were created on Windows and retained
CRLF line endings. Bash `read` therefore preserved a trailing carriage return
in the final `seed` field. Python correctly parsed the integer and model
training was scientifically unaffected, but Slurm created output directories
whose names end in the hidden carriage-return byte. The original Gate-B
analyzer constructs clean `seed-N` paths and would not have found those
directories.

Jobs 299011, 299012, and 299013 (offline smoke, full Gate B, and the analyzer)
were cancelled while still dependency-blocked, before any Gate-B metric was
generated or read. Completed and running training outputs are preserved
byte-for-byte. A deterministic, non-metric normalization step will create a
separate clean logical tree of directory symlinks and LF-only copies of the
identifier manifests. Resubmitted offline jobs must use that logical tree and
the clean-manifest hashes. This fixes path identity only; it cannot change a
model, row, seed, arm, candidate bank, metric, or gate.

The first normalization job then exposed the same hidden byte inside the
absolute filenames written to each training `sha256.txt`. Python's generic
`splitlines()` incorrectly treated that embedded carriage return as a record
boundary. Job 299047 failed during checksum parsing before creating a logical
tree or reading a performance metric. Checksum records are now split only on
their real LF terminators, with the digest and basename still verified against
the unchanged artifacts. The failed partial staging directory is discarded
before the replacement normalization; model and result bytes remain unchanged.

## Pre-outcome Gate-C aggregation

- Success is averaged over the 20 shared starts within each
  task/horizon/model-seed cell, then equally over the three model seeds, then
  equally over task-horizon cells. Thus neither a task, horizon, seed, nor
  shard receives weight from its row count.
- Task-horizon loss checks and the horizon-150 Base-CEM check use the same
  start-then-seed cell means. The SAGE non-inferiority check uses the six-cell
  equal-task/equal-horizon mean.
- Stage latency is divided by the number of simultaneously evaluated contexts
  before aggregation. The five-times-faster alternative compares the
  equal-task/equal-horizon mean of per-shard median context-stage latency,
  averaged over model seeds.
- Development uncertainty uses 10,000 deterministic paired bootstrap draws.
  The resampling unit is the base start within a task. Because the exact same
  20 starts are reused at all three development horizons, all horizons, arms,
  and model seeds for a sampled start remain together. Tasks are resampled
  independently and then weighted equally. These intervals are descriptive
  and do not replace any frozen Gate-C threshold.
- The environment `TimeLimit` is set to `2 * eval_budget`, matching the prior
  released-stack harness, while `evaluate_from_dataset` executes exactly the
  protocol's `H` Cube actions or `2H` PushT actions. The larger safety limit
  prevents wrapper truncation from changing the measured budget.
