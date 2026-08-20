# PushT M2 conditioning-use audit — frozen exploratory specification

Date frozen: 2026-08-12  
Scope: post-confirmatory diagnosis on P1/P2 only  
Status: exploratory; this cannot revise, replace, or tune against the locked PushT P3 result

## Question

Does the selected conditional diffusion scorer use the current-state latent in a way that is necessary for transition plausibility, or is its apparent PushT P2 discrimination mostly a target-state density signal?

The selected, already-frozen M2 configuration is used without retraining: hidden width 1024, deployment sigma 0.25, training seeds 20260728/20260729/20260730, and the eight frozen deployment noise draws. No P3 or P4 labels may be read by this audit.

## Frozen inputs

- P1 frozen Hi-LeWM latent cache, job 294589.
- P1 train-only standardization statistics, job 294596.
- Exact-D25 P1 scorer-pair manifest, seed 20260728.
- The three selected true-condition M2 checkpoints from training array 294599, tasks 3–5.
- P2 imagined-candidate labels, job 294838.
- Original P2 raw-score selection artifact, job 294839, used only for a score-reproduction check and for the already-selected width/sigma.
- Frozen eight-draw noise bank `m2-score-noise-seed-20260728`.

Every input hash must match its existing manifest or checkpoint payload. Outputs go to a new job-ID namespace and no existing artifact is overwritten.

## Diagnostic D1: held-out real D25 transitions

Use 10,000 pairs selected without replacement from the P1 validation population by NumPy PCG64 seed 20260812. The same target rows and sample indices are used for all conditions and all three checkpoints.

For each pair, score:

1. `correct`: its true D25 source latent;
2. `wrong_episode`: the deterministic cross-episode source supplied by the existing M2 mismatched-pair construction with seed 20260728;
3. `mean_source`: the P1 training mean latent, which is zero after the frozen standardization.

All conditions use the same target, sigma, and eight noise vectors. The primary conditioning-use statistic is the paired per-pair difference `wrong_episode_error - correct_error`, first averaged across the three checkpoints. Report its mean, median, fraction above zero, and a 10,000-resample paired bootstrap 95% interval. Conditioning use is supported only if the interval’s lower bound is above zero. This establishes use, not useful failure detection.

## Diagnostic D2: P2 imagined candidates

For each of the 12 pools and 64 candidates, score:

1. `correct`: the pool’s actual source;
2. `wrong_pool`: the next pool’s source under the fixed cyclic mapping `(pool + 1) mod 12`;
3. `mean_source`: the P1 training mean latent.

Also define one derived score before execution: `conditional_penalty = correct_error - wrong_pool_error`. A high value means the target is specifically harder under its actual source than under a wrong pool source. No sign choice or alternate ratio may be selected after labels are read.

Report seed-specific and three-seed-ensemble AUROC/AP for all four scores against the existing positive class, budgeted-attainment failure. Report Pearson and Spearman correlation between `correct` and each ablation, plus mean/median absolute score changes normalized by the correct-score standard deviation and IQR.

The original `correct` scores must reproduce the selected slice of job 294839 with maximum absolute error at most `2e-5`; otherwise the audit fails before interpretation.

Uncertainty for the ensemble AUROC differences uses a 10,000-resample cluster bootstrap over whole candidate pools. Resamples containing only one label class are discarded and the valid replicate count is reported.

## Interpretation rules frozen before the run

- `uses_source_on_real_D25`: D1’s lower 95% paired-bootstrap bound is above zero.
- `conditioning_improves_P2_failure_ranking`: the lower 95% pool-bootstrap bound for `AUROC(correct) - AUROC(wrong_pool)` is above zero.
- `conditional_penalty_is_promising`: ensemble AUROC is at least 0.65 and its pool-bootstrap lower bound is above 0.50.
- `target_dominated_on_P2`: both ensemble correlations `corr(correct, wrong_pool)` and `corr(correct, mean_source)` are at least 0.95, and neither ablated ensemble AUROC is more than 0.02 below the correct-source AUROC.

These rules are diagnostic descriptions, not new promotion criteria. Whatever the outcome, the locked PushT P3 result remains the confirmatory result for the original M2 method. A redesigned M2 may be proposed only as an explicitly exploratory successor and must later be evaluated on data untouched by its design.

## Architectural audit

For each checkpoint, record the first-layer Frobenius norm separately for noisy-target, source, and sigma-embedding input columns. These norms are supporting diagnostics only and do not override D1/D2 behavior.
