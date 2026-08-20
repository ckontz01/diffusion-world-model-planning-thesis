# PushT M2 real-frame reachability audit — frozen exploratory specification

Date frozen: 2026-08-12  
Scope: P2 development data only  
Status: exploratory; no locked P3/P4 artifact or conclusion may be changed

## Question

Can the selected conditional diffusion scorer predict budgeted physical attainability when every candidate target is a real frame from the offline dataset? This removes the easiest imagined-state shortcut: detecting whether a target itself lies off the data manifold.

## Frozen inputs and models

- P2 real-frame execution aggregate, job 294668: 12 pools × 64 candidates in each of two strata, with five low-level execution repeats per candidate.
- Stratum 0: target exactly 25 primitive steps later in the same recorded trajectory.
- Stratum 1: target from a different P2 trajectory.
- Existing primary physical label: failure to attain block position within 20 pixels and wrapped block angle within pi/9 in at least three of five executions.
- Already-selected M2 width 1024, sigma 0.25, three true-condition checkpoints from job 294599, tasks 3–5, and the frozen eight-draw score-noise bank.
- Existing width-1024 mismatched-pair diffusion null checkpoints from job 294841, tasks 3–5.
- Existing width-1024 conditional autoencoder controls from job 294842, tasks 0–2.

No model is trained or tuned in this audit.

## Frozen source ablations

For each true-condition diffusion checkpoint, score every target under:

1. `true_correct_source`;
2. `true_wrong_source`, using the next candidate source in the same stratum under flattened cyclic mapping `(index + 1) mod 768`;
3. `true_mean_source`, using the P1 training mean latent;
4. `true_conditional_penalty = true_correct_source - true_wrong_source`.

Also score `mismatched_training_null` and `autoencoder_control` with the correct source. All diffusion scores share the exact same target, sigma, and noise draws.

## Frozen metrics

The positive class is physical budgeted-attainment failure. For each condition, report seed-specific and three-seed-ensemble AUROC/AP:

- separately in each stratum;
- combined across strata as a descriptive value;
- as the arithmetic mean of the two stratum-specific AUROCs (`macro_stratum_auroc`), which is the primary value because combined discrimination can be driven merely by stratum identity.

Use 10,000 stratified whole-pool bootstrap replicates (PCG64 seed 20260812): independently resample 12 pools with replacement inside each stratum. Report 95% intervals for every ensemble macro-stratum AUROC and for these predeclared differences:

- true correct minus mismatched-training null;
- true correct minus autoencoder control;
- true correct minus true wrong source;
- true correct minus true mean source.

Replicates in which either stratum has only one class are discarded and counted.

## Frozen interpretation rules

- `real_frame_discrimination_supported`: true-correct macro AUROC is at least 0.65 and its lower bootstrap bound is above 0.50.
- `beats_mismatched_training_null`: the lower bound for true-correct minus null is above zero.
- `beats_autoencoder_control`: the lower bound for true-correct minus autoencoder is above zero.
- `correct_source_beats_wrong_source`: the lower bound for true-correct minus wrong-source is above zero.
- `correct_source_beats_mean_source`: the lower bound for true-correct minus mean-source is above zero.
- `strong_specific_support_for_conditional_diffusion`: all five preceding statements are true.

Failure of the last rule does not show that diffusion cannot work. It shows that this frozen implementation has not yet separated conditional diffusion value from simpler controls on this development diagnostic.
