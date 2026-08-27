# E16 continuation-aware direct far-goal VAD development protocol

Date fixed before any E16 diagnostic output was generated: 27 August 2026  
Role: outcome-informed P1/P2 method development only  
Confirmation status: not authorized by this document

## 1. Question and scope

E15 remains a failed, immutable study. It showed that the registered smooth
bounded-action VAD generated legal and diverse banks, and that its PushT bank
covered the demonstrated next actions better than a matched diagonal Gaussian,
but its one-chunk far-goal endpoint selector chose options with worse recorded
true-local Le-WM cost. E15 did not run closed-loop Gate C and did not establish
that all direct far-goal diffusion planners fail.

E16 asks one narrower, outcome-informed question:

> Did E15 mainly fail because a one-chunk greedy endpoint score cannot value a
> first action that creates useful later options, and can a fixed two-stage
> continuation score repair that selector without introducing a latent subgoal?

The E15 VAD, diagonal-Gaussian, direct eight-mode GMM, released Le-WM
checkpoints, and published-equation SAGE reconstruction are frozen and reused
without retraining or outcome-dependent changes. E16 trains only a shared
latent-to-state interface adapter needed because Le-WM predicts the next latent
but the frozen E15 proposal models also condition on the low-dimensional state.

E16 does **not** implement full-horizon trajectory diffusion, a learned path
critic, a generated latent subgoal, a guidance sweep, a new diffusion
architecture, or any change to E15's failed gate. Those are outside scope.

## 2. Evidence status and firewall

All E16 results are development evidence. The ranking diagnostic deliberately
reuses already exposed E15 P1-validation rows and is labelled outcome-informed.
The closed-loop study uses newly selected P2 identifiers and excludes every
base start named by the unused E14/E15 20-start manifest. It still remains P2
development evidence and cannot support a confirmatory claim by itself.

E16 must never generate, open, hash, or consume D5. It must not read
metric-bearing D3 or D4 artifacts. P3, P4, C1, and I1 remain protected. A
positive E16 result can authorize only drafting a separately frozen study on
fresh evidence.

The immutable E15 training snapshot is
`gdp-cem-e15-training-ebd6109b65528f6b`, whose source-manifest SHA-256 is
`ebd6109b65528f6b201c2de7deac29888a25e570f60d11ea9e6298374b61301c`.
The immutable E15 full-evaluation snapshot is
`gdp-cem-e15-offline-d970a18e4921eb2c`, whose source-manifest SHA-256 is
`d970a18e4921eb2c4d3d2ed7f6fdd295b583320b43fef1a88908000d82a8a22e`.
The E15 protocol SHA-256 is
`bcbe66b3b7b2635473d5bd98b3a450c5e136879f275ac3a0ddd6d4bdb254755b`.

## 3. Stage A: exact-bank ranking diagnostic

Stage A evaluates both PushT and Cube using the E15 seed-7201 VAD checkpoint
and all 90,000 E15 validation queries per task. Candidate generation replays
E15's exact generator initialization, cell order, row order, 300 candidates,
five deterministic velocity evaluations, guidance scale 1.5, smooth action
map, and released Le-WM rollout.

Before any new ranking statistic is accepted, the replay must match the frozen
E15 `cache_row`, far-goal-selected index-derived terminal cost, and selected
true-local cost. Maximum absolute disagreement may not exceed `2e-5`, and all
row identifiers must agree exactly. Failure is a technical replay failure and
blocks interpretation.

For every query, Stage A records:

- Pearson and Spearman correlation between all 300 far-goal endpoint costs and
  true-local costs;
- the one-indexed far-goal rank of the candidate with minimum true-local cost;
- minimum true-local cost within the top `1,5,10,30,100,300` candidates under
  far-goal ranking;
- additive regret of every top-k value from the 300-candidate local oracle;
- far-goal-selected and local-oracle costs; and
- the fraction of queries whose local oracle is contained in each top-k set.

Results are reported task first and separately by `(delta,tau)`. Aggregates
must not hide PushT behind Cube.

### 3.1 Fixed low-guidance bank diagnostic

Using the same seed-7201 conditional VAD checkpoint and the same 300 initial
noise tensors, a diagnostic 300-candidate bank is formed from candidates
`0:150` at the frozen guidance 1.5 and candidates `150:300` at guidance 0.0.
It is compared descriptively with the exact 300-candidate guidance-1.5 bank
for local-oracle cost, expert-action oracle MSE, selected true-local cost, and
selected far-goal cost. This is not a guidance search, is not an E16 proposed
arm, and cannot change the continuation settings.

## 4. Shared latent-to-state adapter

The adapter is necessary only to feed an imagined Le-WM intermediate latent
back into an unchanged E15 proposer. One adapter is trained per task from
unique E15 role-0 source indices only. E15 role-1 rows are opened once after
the final checkpoint is written and are never used for early stopping,
checkpoint selection, architecture selection, or hyperparameter selection.

The fixed adapter is:

```text
LayerNorm(192) -> Linear(192,512) -> SiLU ->
Linear(512,512) -> SiLU -> Linear(512,state_dim)
```

Inputs and targets are the frozen E15 train-standardized latent and state.
Training uses seed 8161, AdamW (`lr=1e-3`, `weight_decay=1e-4`), batch 1024,
20,000 steps, 500-step linear warmup followed by cosine decay, gradient norm
1.0, BF16 autocast, and EMA 0.999. The scientific checkpoint is the final EMA;
there is no best-validation checkpoint.

The adapter validity gate requires, on unique role-1 source indices for each
task:

- finite predictions;
- overall standardized RMSE at most 0.50;
- maximum coordinate standardized RMSE at most 0.85; and
- median coordinate R-squared at least 0.50.

Failure blocks all continuation experiments. It does not permit retraining or
changing the adapter in E16.

## 5. Stage B: one-continuation diagnostic

Stage B uses seed 7201 and a fixed hash-selected subset of 64 E15-validation
queries in each long-horizon cell with `tau=15` and
`delta in {75,90,100,115,125,140,150}`, for 448 queries per task.

For each query it deterministically replays the first 64 candidates from the
exact E15 VAD bank, rolls them through Le-WM, decodes each predicted
intermediate latent with the frozen shared adapter, and draws exactly one
second VAD option per first candidate. The second option uses the same final
goal, `tau=15`, and `remaining_delta=delta-15`. Its random stream is keyed by
task, E15 cache row, and first-candidate index under the E16 seed derivation.

Stage B reports how one continuation changes the selected first-candidate
index, its far-goal rank, and its first-stage true-local cost. These are
diagnostics, not an eligibility rule: a different valid route can disagree
with the single demonstrated immediate latent.

## 6. Stage C: continuation-aware direct planner

Stage C is permitted only if both task adapters pass Section 4 and Stages A
and B complete without a technical/replay failure. It uses new identifier-only
P2 starts, never E14/E15's previously named starts. Horizons are 75 and 150;
the local action chunk is always 15 primitive actions, matching the frozen
schedule. No 25-step short-horizon result enters the continuation claim.

At a stage with at least 30 actions remaining, every continuation arm:

1. samples 64 first chunks from its frozen E15 proposer;
2. rolls them through frozen Le-WM;
3. decodes each intermediate latent through the same task adapter;
4. samples eight second chunks per first chunk from the same proposer, with
   the same far goal and remaining horizon reduced by 15;
5. rolls all 512 continuations through frozen Le-WM; and
6. scores each first chunk by the arithmetic mean of its two lowest final-goal
   continuation costs, then executes the first chunk with minimum score.

At the final 15-action stage, where no full second chunk remains, the arm uses
the one-stage far-goal endpoint score. There is no softmin-temperature sweep,
weight, local-target term, candidate refinement, or fallback.

The continuation mechanism, first count 64, continuation count eight, best-two
mean, random-stream construction, action map, Le-WM, and timing method are
identical for VAD, diagonal Gaussian, and direct GMM. Total Le-WM rollout
trajectories per non-final planning stage are `64 + 64*8 = 576`.

## 7. Frozen Stage-C arms

The task-first closed-loop arms are:

1. released Base CEM;
2. full published-equation SAGE reconstruction;
3. E15 VAD with its original greedy 300-candidate endpoint selector;
4. E15 VAD with a greedy 576-candidate endpoint selector (matched rollout-count
   control);
5. continuation-aware VAD, 64 by eight;
6. continuation-aware diagonal Gaussian, 64 by eight; and
7. continuation-aware direct eight-mode GMM, 64 by eight.

The 576-candidate VAD control is required: improvement over the 300-candidate
arm alone cannot establish that continuation, rather than added Le-WM compute,
helped. Gaussian and GMM receive the same continuation structure so a generic
lookahead benefit cannot be mislabelled diffusion-specific.

Stage C uses model seeds `7201,7202,7203` and 12 new base starts per task,
paired across all arms, seeds, and both horizons. The selected 12 starts are
fixed by hash rank with salt `gdp-cem-e16-stage-c-20260827`, after excluding
every `(episode,start)` pair in the old E14/E15 P2 manifest. All results remain
development-only.

## 8. Reporting and uncertainty

Report success and task-native score per task before any equal-task aggregate.
For learned arms, report every model seed. Confidence intervals use a paired
cluster bootstrap whose resampling unit is `(task,base_start)` and keeps both
horizons, all arms, and all model seeds together. Individual episodes are
never resampled as independent observations.

Report synchronized end-to-end planner time, proposal time, adapter time, and
Le-WM rollout time. Candidate counts are not used as a latency proxy.

The primary mechanistic contrasts are:

- continuation VAD minus greedy VAD-300;
- continuation VAD minus greedy VAD-576;
- continuation VAD minus continuation Gaussian;
- continuation VAD minus continuation GMM; and
- continuation VAD minus full SAGE reconstruction.

A positive continuation result requires the continuation VAD point estimate
to beat both VAD greedy controls on equal-task success without reducing either
task by more than five percentage points. A diffusion-specific result further
requires it to beat both continuation controls. Full-SAGE superiority is a
separate contrast and is never inferred from passing the first two rules.
Intervals, task heterogeneity, ceilings, and null/negative results are reported
regardless of these labels.

## 9. Amendments and stopping

Before any metric-bearing output is opened, source, protocol, manifests,
checkpoints, and random seeds are checksum frozen. Technical execution errors
may be corrected only through a dated implementation decision that preserves
all scientific settings and inputs. Scientific gate failures, weak effects,
or unfavorable task results cannot be rescued, tuned, or rerun on the same
evidence.

After Stage C, E16 stops. It never automatically creates a confirmation run.
The more ambitious direct fix—diffusing a full 75- or 150-action plan—is
explicitly outside E16 and must not be attempted under this protocol.
