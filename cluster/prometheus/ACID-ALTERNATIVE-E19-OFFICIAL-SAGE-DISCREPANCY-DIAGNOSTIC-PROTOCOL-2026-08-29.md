# E19 official SAGE discrepancy diagnostic protocol

Date frozen: 29 August 2026

Evidence role: outcome-informed technical discrepancy localization after the
frozen E19 native-reproduction decision

## Immutable boundary

This diagnostic does not amend, rescue, reinterpret, or replace E19. E19's
terminal decision remains `stop_native_reproduction_failed`: all 180 official
cells and 9,000 episodes completed, and the unchanged official summarizer
accepted 29 of 60 released means. No expected value, tolerance, checkpoint,
dataset identity, manifest, seed, horizon, planner parameter, result, or E19
artifact may be changed.

The diagnostic consumes read-only copies of:

- E19 snapshot
  `/lustreFS/data/superworld/ckontzias/thesis/snapshots/gdp-cem-e19-9f5499887c0d2e1f`,
  source-manifest SHA-256
  `9f5499887c0d2e1f9808cc5f493e7f172e717bcb8db202088e89e5c29f2a1d6c`;
- E19 protocol SHA-256
  `759f64b67a5c8e9d33e03c4d7027ede7edf99f1a4186236fb8f0879fc7ed0e20`;
- E19 run root
  `/lustreFS/data/superworld/ckontzias/thesis/experiments/gdp-cem-e19/native-reproduction-run-20260828-9f549988`;
- official SAGE commit `8219029fd52e89157e05aebb998ab26f0ef46966`,
  tree `0c64066eeac97c27fee382c1879bb26968b3fd56`;
- the six byte-identical released SAGE checkpoints and both exact LeWM
  releases already sealed by E19; and
- the original PushT HDF5 and E19's disclosed JPEG-quality-95 Lance transport.

No D5, D3/D4 metric artifact, P3, P4, C1, I1, or E18-versus-SAGE performance
comparison may be generated, opened, hashed, or consumed.

## Outcome-informed sentinel freeze

The five sentinels were selected once from the already sealed E19 result,
before any diagnostic trace was run. The lowest registered seed, 32, is used
throughout so no within-row seed was selected after inspection. Together the
set covers both tasks, all five released methods, the first summarizer
rejection, the largest discrepancy, Cube's generated-goal cache path, PushT's
transport, and two positive controls.

| Sentinel | E19 cell | Task | Method | Seed | H | Frozen rationale |
|---:|---:|---|---|---:|---:|---|
| 0 | 1 | PushT | `base_cem` | 32 | 50 | first row rejected by the unchanged summarizer |
| 1 | 22 | PushT | `far_goal_prior_cem` | 32 | 125 | largest aggregate PushT far-goal-prior discrepancy |
| 2 | 58 | PushT | `generator_prior_top` | 32 | 125 | non-CEM control from a reproduced aggregate row |
| 3 | 131 | Cube | `lewm_generator` | 32 | 150 | largest E19 discrepancy and Cube cache path |
| 4 | 164 | Cube | `sage` | 32 | 75 | full-method control from an exactly reproduced aggregate row |

Each sentinel is executed twice from a fresh process and fresh model load:
10 runs and 500 diagnostic episodes total. The official 50-record manifest,
schedule, budget, seed, checkpoints, bf16 precision, 300 candidates, 30 CEM
rounds, 30 elites, five-action blocks, three-frame history, frameskip five,
and no-warm-start setting remain exact.

## Read-only tracing

Tracing is installed around the pinned evaluator classes without editing the
official SAGE checkout. It observes but does not replace sampling, scoring,
top-k selection, fitting, cache lookup, model inference, or environment action
execution. Canonical SHA-256 records include dtype, shape, and contiguous
tensor bytes.

For every real planner call, the trace records:

- the complete solver-input/preprocessing mapping hash;
- raw history and goal input hashes;
- LeWM history and final-goal latent hashes;
- generated or terminal local-goal hashes;
- first-round candidate and cost hashes;
- elite-index hashes for every CEM round; and
- the actual mean and effective standard-deviation update hashes for every
  CEM round.

The first real planner call also seals a read-only input and fixed-candidate
bank for the independent runtime and transport comparisons. The bank is not
fed back into the sentinel evaluator.

For Cube generated goals, every lookup records the exact
`(environment_id, plan_call, remaining_steps, option_duration_steps)` key,
whether it was a hit or miss, the cached tensor hash, and the returned local
goal hash. Within each fresh run/model instance, the audit rejects key
collisions, value drift for an existing key, expanded/unexpanded stage-key
disagreement, more than one value for a key, or a returned goal inconsistent
with the stored cache value. Cache namespaces are not compared across fresh
model instances; repeat identity is enforced separately on the complete event
streams.

## Exact-repeatability gate

After all ten runs complete successfully, the sealed analyzer compares the two
repeats for each sentinel. Exact repeatability requires:

1. identical official `episode_successes` vectors and success rates;
2. identity with the already sealed E19 sentinel outcome;
3. identical ordered trace-event kinds and canonical tensor hashes;
4. identical first-round candidate/cost, elite-index, and all mean/std hashes;
5. identical generated-local-goal and cache-key/value traces; and
6. identical canonical first-call bank content.

Elapsed time, filesystem output paths, Slurm identifiers, and the diagnostic
repeat label are excluded from equality. No tolerance is applied to tensors or
episode outcomes.

## Official-runtime comparison

On the repeat-0 first-call banks, a separate A6000 audit compares:

- the E19 compatibility-loaded object checkpoint; and
- a fresh model instantiated by the pinned official SAGE runtime from the
  exact released `config.json` and `weights.pt`, loaded strictly.

The audit requires identical parameter keys, shapes, dtypes, and bytes. On
real manifest inputs it compares history latents, final-goal latents, and
fixed-bank LeWM costs bit-for-bit, plus complete candidate order and top-30
elite membership. It never executes an additional environment episode.

## PushT transport comparison

For PushT sentinels with CEM, the audit addresses the released but absent
paper Lance dataset explicitly. At the exact manifest rows used by the first
planner call, it compares E19's decoded JPEG-quality-95 Lance images with the
lossless source-HDF5 pixels while retaining identical numeric fields,
preprocessing, compatibility-loaded LeWM, local-goal rule, and fixed candidate
bank. It reports pixel error, preprocessing and latent differences, cost
differences, full rank agreement, rank correlation, and top-30 elite-set
membership. No candidate is regenerated and no environment episode is run.

## Frozen decision rule

An **objective technical mismatch** is one of these preregistered binary
failures:

1. either repeat differs in an outcome or ordered intermediate hash;
2. compatibility-loaded and official-runtime models differ in parameter bytes,
   real-input latents, fixed-bank costs, ranks, or elites;
3. Cube cache stage keys collide, drift, or return a value different from the
   sealed value for that key; or
4. lossless-versus-E19 PushT transport changes top-30 elite membership for a
   frozen fixed candidate bank.

Pixel, latent, cost, or rank-order differences from JPEG transport are
quantified but are not by themselves an E20 trigger if every top-30 elite set
is unchanged.

Exactly one uniquely attributable and mechanically correctable mismatch class
authorizes freezing one separately named corrected E20 protocol and rerunning
the complete 180-cell grid once. E20 may correct only that mismatch; all E19
scientific settings, expected values, and the official two-point tolerance
remain frozen. Zero mismatch classes, multiple mismatch classes, or a mismatch
without a unique correction forbid E20.

If all diagnostic gates are internally consistent and no unique technical
cause explains E19, the terminal action is to prepare a read-only author
evidence packet containing hashes, identities, the five repeatability records,
runtime parity, transport quantification, Cube cache audit, and concise
reproduction instructions. Preparing the packet does not contact the authors.

## Information barrier and reporting

Before all ten sentinel runs and the dependent comparison/analyzer complete,
monitoring is limited to scheduler state, exit codes, file existence, byte
counts, and checksums. Partial evaluator logs, results, traces, banks, costs,
ranks, and metrics may not be opened unless an exact cell fails technically,
and then only that cell's logs may be used for execution diagnosis.

The final report must retain E19's decision verbatim, state whether exactly one
technical mismatch was identified, identify any E20 authorization narrowly,
or record creation of the author packet. It must explicitly state that no
protected evidence and no E18-versus-SAGE comparison was accessed.
