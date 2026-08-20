# PushT B0/B1 development pilot specification

Frozen before submission on 8 August 2026.

## Purpose and classification

This run validates the released Hi-LeWM checkpoint under the full published
PushT `d=25` selected configuration for B0 (unconstrained high-level CEM) and
B1 (empirical-macro CEM). It is a development pilot, not a paper reproduction
or thesis result.

The paper reports means over three random seeds, but the released PushT matrix
specification contains only seed `42`. The artifact also omits a B1 matrix
specification. No unverified seed values are invented here. Publication-facing
reproduction remains pending clarification of the other two paper seeds or a
predeclared independent reproduction seed set.

## Frozen run

- Environment: `swm/PushT-v1`.
- Released checkpoint: `pusht_hierarchical_default_epoch_15_object.ckpt`.
- Runtime: the pinned `stable-worldmodel==0.0.6` artifact environment.
- Development seed: `42`.
- Evaluation episodes: `50`, sampled deterministically by the released evaluator.
- Goal offset: `25` environment steps.
- Evaluation budget: `50`.
- Planning mode: online hierarchical replanning, not staged.
- High level: horizon `1`, receding horizon `1`, action block `1`, replan interval `5`.
- High-level CEM: `900` samples, `20` iterations, top `10`, variance scale `1.0`.
- Low level: horizon `2`, receding horizon `1`, action block `5`.
- Low-level CEM: `300` samples, `30` iterations, top `150`, variance scale `1.0`.
- Both solver batch sizes: `1`.
- Device: one A5000-class GPU from Prometheus `defq`; exact identity is captured by `nvidia-smi`.

B1 changes only the high-level solver to the released empirical-macro
implementation with `4096` sequences, chunk length `5`, residual scale `0.1`,
minimum residual standard deviation `0.001`, eight returned candidates, encoder
batch size `4096`, sequence sampling, and seed `42`. B0 keeps that block disabled.

## Acceptance checks

The run is accepted as an implementation pilot only if:

1. both arms finish with non-empty result and episode-manifest files;
2. both resolved configurations contain all frozen settings;
3. both arms use identical `(eval_index, episode_id, start_step)` rows;
4. all 100 rollout videos exist and are non-empty;
5. the validator produces `status: ok`; and
6. Slurm reports a zero exit code.

Success rates are used only to decide whether the released B0/B1 path behaves
plausibly enough to proceed. They are not estimates for the thesis endpoint.

## Operational erratum after job 294573

Both experimental arms completed, but the original post-run validator caused
the batch job to exit `1`: it assumed a fractional success rate and the token
`SUCCESS`, whereas the released evaluator writes a percentage and the token
`PASS`. The experiment outputs themselves were not changed. Validator v2 fixes
only those two parsing assumptions. No model, planner, seed, episode, or
evaluation setting changed.
