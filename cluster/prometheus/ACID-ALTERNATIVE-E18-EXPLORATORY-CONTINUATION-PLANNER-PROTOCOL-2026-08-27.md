# E18 exploratory action-conditioned continuation-planner protocol

Date fixed before any E18 identifier or metric output: 27 August 2026

Evidence role: outcome-informed P2 method development only

Confirmation status: not authorized by this document

## 1. Why E18 is a new study

E16 found substantial oracle reranking headroom inside the frozen E15 VAD
banks, but its latent-only state adapter failed on Cube. E17 then trained one
stronger action-conditioned transition-state adapter per task. PushT passed
every frozen E17 gate. Cube passed overall RMSE, median coordinate R-squared,
copy-current improvement, and all duration gates, but failed the frozen
worst-coordinate RMSE ceiling: 1.1626 versus 0.8500. E17 therefore remains a
failed and immutable preflight.

That preflight failure blocked promotion under E17; it did not evaluate the
actual continuation planner. E18 asks the narrower exploratory question:

> When the exact failed E17 checkpoints are used without modification, can a
> fixed two-stage 64-by-8 continuation score select better first VAD chunks
> than greedy far-endpoint selection, and is any benefit specific to
> diffusion rather than generic lookahead?

E18 does not reinterpret E17 as a pass. It deliberately evaluates the frozen
checkpoints in a separately named development study so that the conservative
E17 validation decision and the empirical planner question remain distinct.

## 2. Evidence firewall

All E18 outcomes are P2 development evidence. They cannot support a
confirmatory paper claim by themselves. E18 may read:

- released PushT and Cube datasets and Le-WM checkpoints;
- the frozen E15 VAD, diagonal-Gaussian, and direct eight-mode GMM final EMA
  checkpoints for seeds 7201, 7202, and 7203;
- the frozen E17 adapter checkpoints and already exposed E17 audit; and
- identifier-only P2 partition information needed to select starts.

E18 must not generate, open, hash, or consume D5. It must not read
metric-bearing D3 or D4 artifacts. P3, P4, C1, and I1 remain protected. The
new P2 start manifest excludes every start named by the unused E14/E15 P2
manifest. It is generated only after this protocol and the evaluator are
checksum-frozen.

The E15 training source-manifest SHA-256 is
`ebd6109b65528f6b201c2de7deac29888a25e570f60d11ea9e6298374b61301c`.
The E17 source-manifest SHA-256 is
`9fb5a8c296feec81c7982a79272e502216eaf91ad987b0e70c156cb2c5ad9fc1`.
The E17 audit SHA-256 is
`d819b5db889de3362f26c729df6000b53a7028917c3d527b7f74410aac5188f8`.
The immutable E17 adapter checkpoint hashes are:

- PushT: `c58726a3502bf52bbbaad6263c1f636ef393ecbd34835b021750f7451bed88b8`;
- Cube: `008311d81dcf3753170a7ecfd886cfb23fddc0ec932150e609071d3c830214a0`.

## 3. Frozen planner mechanism

The local chunk duration is always 15 primitive actions. At any stage with at
least 30 actions remaining, every continuation arm performs exactly:

1. draw 64 first chunks from its frozen E15 proposer;
2. roll each first chunk through frozen Le-WM;
3. predict the resulting standardized state with the frozen E17 adapter using
   the current standardized state, current standardized latent, bounded raw
   first chunk, its duration mask, and Le-WM terminal latent;
4. draw eight second chunks for each predicted intermediate condition, using
   the unchanged final goal and remaining horizon reduced by 15;
5. roll all 512 second chunks through frozen Le-WM; and
6. score each first branch by the arithmetic mean of its two lowest final-goal
   continuation costs, then execute the first chunk with minimum score.

At the final 15-action stage, a continuation arm draws 64 first chunks and
uses the ordinary one-stage Le-WM endpoint score. There is no learned value
critic, local-target term, score weight, softmin temperature, refinement,
fallback, guidance change, adapter ensemble, or outcome-dependent switch.

The E17 checkpoint is used exactly as written at step 30,000. It is not
retrained, calibrated, thresholded, selectively disabled, or replaced on
Cube. The E15 proposers, five deterministic velocity evaluations, guidance
1.5, smooth bounded-action map, Le-WM checkpoints, and state/action
normalizers are unchanged.

## 4. Frozen arms and compute controls

Five task-first arms are evaluated:

1. `vad_greedy_300`: original E15 VAD with 300 one-stage candidates;
2. `vad_greedy_576`: VAD with 576 one-stage candidates, matching the 64 plus
   64-by-8 Le-WM rollout count of a non-final continuation stage;
3. `vad_continuation`: the proposed E17-conditioned 64-by-8 planner;
4. `diagonal_gaussian_continuation`: the same continuation mechanism with the
   matched frozen E15 diagonal Gaussian; and
5. `direct_gmm_continuation`: the same mechanism with the frozen E15 direct
   eight-mode trajectory GMM.

The Gaussian and GMM controls use the same first count, continuation count,
adapter, best-two score, action map, goals, start states, horizons, seeds, and
Le-WM rollout budget. This prevents a generic lookahead effect from being
mislabelled diffusion-specific. The 576-candidate VAD arm prevents extra
Le-WM compute alone from being mislabelled continuation-aware planning.

## 5. Starts, horizons, seeds, and execution registry

Tasks are PushT and Cube. Horizons are 75 and 150; horizon 25 is excluded
because it cannot test long-horizon continuation. The schedule is five or ten
15-action chunks respectively. PushT retains the released evaluation budget
of twice the goal horizon; Cube retains one times the horizon, matching the
existing Le-WM evaluation interface.

For each task, 12 H150-compatible P2 base starts are selected by SHA-256 rank
with salt `gdp-cem-e18-p2-continuation-20260827`, after excluding all 20
episode/start pairs in the old E14/E15 P2 manifest. The same 12 base starts are
paired across both horizons, every arm, and all three learned-model seeds.

The learned seeds are 7201, 7202, and 7203. Starts are split into four shards
of three. The exact execution registry therefore contains:

`2 tasks * 5 arms * 3 seeds * 2 horizons * 4 shards = 240 cells`

and the complete information barrier contains:

`2 tasks * 12 starts * 5 arms * 3 seeds * 2 horizons = 720 episodes`.

No performance-bearing cell may be opened before all 240 cells terminate
successfully. Until then, monitoring is restricted to scheduler state, exit
codes, file existence, byte counts, and checksums. A dependent analyzer is the
first process allowed to read episode outcomes.

## 6. Technical validity

Before submission, a nonmetric input audit must verify:

- the E15 and E17 source, protocol, summary, audit, and checkpoint hashes;
- that the E17 audit still says `stop_transition_adapter_preflight_failed`,
  PushT passed, Cube failed, and planner evaluation was not authorized by E17;
- that E18 is independently marked exploratory and does not use E17 as an
  authorization artifact;
- final-step 30,000 identity and strict adapter architecture loading;
- all 18 frozen proposer checkpoints and their training-only lineage; and
- absence of protected paths and artifacts.

Every evaluated cell must have finite timing and outputs, exact task/arm/seed/
horizon/shard identity, the expected schedule, and the exact Le-WM rollout
budget. Bounded raw proposals must have zero strict legal out-of-bounds and
zero exact-boundary values. Rounded first-bank uniqueness must be at least 95%
of its candidate count; every eight-way continuation set must contain at least
seven unique chunks. Predicted adapter states must remain finite and their
absolute maxima are reported task first. A validity failure blocks scientific
interpretation; it cannot be tuned away.

## 7. Reporting and uncertainty

Success is reported per task and horizon before any pooled number. Every model
seed is shown. Cube cells at or above 95% success are marked as ceiling cells.
Timing is synchronized and decomposed into encoding, proposal/selection,
adapter, and Le-WM rollout time.

Confidence intervals use 10,000 paired bootstrap resamples. The sampling unit
is `(task, base_start)`: each selected start keeps both horizons, every arm,
and all three seeds together. Episodes and seed-runs are never resampled as
independent observations.

The frozen contrasts are continuation VAD minus:

- greedy VAD-300;
- greedy VAD-576;
- continuation diagonal Gaussian; and
- continuation direct GMM.

For each contrast, report task/horizon effects, task-average effects,
equal-task/equal-horizon effect, and its paired interval.

## 8. Frozen interpretation rules

`continuation_mechanism_passed` is true only if continuation VAD has a strictly
positive equal-task/equal-horizon point difference against both greedy VAD
controls and neither task-average difference is below -0.05 against either
control.

`diffusion_specificity_passed` is true only if continuation VAD has a strictly
positive equal-task/equal-horizon point difference against both continuation
controls and neither task-average difference is below -0.05 against either
control.

The joint exploratory signal passes only if both rules pass. Confidence
intervals do not silently replace these frozen point/task rules and are always
reported. A PushT-only benefit, Cube-only benefit, tie, or generic
continuation benefit is reported under that narrower description.

Even a joint pass authorizes only drafting a separately frozen confirmation
protocol on untouched evidence. It does not authorize generating or consuming
D5 automatically. A failure does not identify the E17 adapter as the sole
cause; it establishes only that this exact frozen planner did not realize the
E16 oracle headroom under the registered development test.

## 9. Stopping and amendments

E17 remains unchanged. Scientific settings, inputs, arms, counts, schedules,
seeds, starts, scoring, gates, and checkpoints cannot change after the E18
source snapshot is frozen. Technical execution errors may be corrected only
through a dated implementation record that preserves those quantities and all
existing artifacts. Scientific weakness cannot be rescued or rerun on the
same starts.

E18 stops after its complete development analysis. It does not implement the
other proposed routes: a learned progress/value critic, value-guided
denoising, latent-subgoal diffusion, or substantially longer/full-horizon
trajectory diffusion.
