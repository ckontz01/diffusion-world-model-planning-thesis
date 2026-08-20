# E8A Gaussian-anchored diffusion-refinement result

Date completed: 2026-08-17  
Role: disjoint P1-validation method development; not confirmation

## Bottom line

Gaussian-anchored diffusion refinement (GADR) passed all nine frozen E8A
advancement gates. This is the first proposal-generation result in this
project for which true-goal diffusion beat both its shuffled-goal diffusion
control and the matched non-diffusion conditional-Gaussian proposal while
retaining full candidate diversity.

The selected configuration is fixed as:

- cosine restart timestep `40` of `100`;
- one epsilon-denoiser evaluation (direct clean-action projection);
- refinement of `50%` of the conditional-Gaussian bank;
- candidate zero retained as the unrefined conditional-Gaussian mean.

This result authorizes a separately frozen exposed-D2 closed-loop diagnostic.
It does not authorize D3, C1, I1, or an alternative-to-ACID claim.

## Selected equal-task metrics

Lower is better for action MSE and Le-WM goal cost.

| Metric | Gaussian base | Shuffled GADR | True GADR |
|---|---:|---:|---:|
| Selected-action MSE | 0.703982 | 0.648713 | **0.632521** |
| Oracle-action MSE | 0.397874 | 0.364191 | **0.354652** |
| Minimum Le-WM goal cost | 2.097222 | 2.118767 | **1.672113** |
| Candidate variance | 0.362820 | 0.296662 | 0.289532 |
| Boundary-clipped fraction | 0.038556 | 0.019949 | 0.020827 |
| Unique candidates (of 300) | 300 | 300 | 300 |

True GADR beat both controls on selected-action MSE in PushT and Cube. On
Reacher it had slightly worse selected-action MSE than shuffled GADR, but it
substantially lowered Le-WM goal cost and improved oracle-action MSE. The
cross-task gate required wins on at least two tasks and therefore passed
without suppressing the Reacher result.

Two of the 36 frozen configurations were eligible: restart `40`, one denoiser
evaluation, and refined fraction `0.25` or `0.50`. The predeclared
lexicographic rule selected `0.50` because it had the lower true-GADR
equal-task selected-action MSE.

## Interpretation

E7P failed because sampling from pure terminal noise amplified epsilon error
under the near-zero-SNR end of the cosine schedule. E8A avoided that failure
by starting from a competent conditional-Gaussian action sequence and adding
only moderate noise before one learned projection. The result supports the
specific mechanism that the diffusion model can improve an existing proposal
rather than replace it from pure noise.

The large improvement in predicted Le-WM goal cost could still represent
world-model exploitation. The exposed-D2 diagnostic must therefore compare
true GADR with the identical shuffled-goal and Gaussian proposal mechanisms in
closed loop, as well as original CEM and the audited published-equation ACID
reconstruction. Only physically realized task success can decide whether the
P1 proposal improvement transfers.

## Provenance

- evaluation array: `297720` (`3/3` completed);
- analysis job: `297721` (completed);
- official aggregate:
  `/lustreFS/data/superworld/ckontzias/thesis/results/acid-alternative/gdp-cem-e8a-refinement/analysis/job-297721/summary.json`;
- aggregate SHA-256:
  `d7d804d8ccf38c0b5dad3c5e46c3ad2f1a7396b892bf40d36d73d8bb16e35521`;
- protocol SHA-256:
  `e6ad569e0313276bff2cf79835bcd53c4b1604113b34bacdb5004a4bae034141`;
- immutable source-manifest SHA-256:
  `d4003deb1f5b068112dd3023ab96ce45c0e2f24efd53af8ca75c1b6e36bd5bea`;
- decision: `authorize_separately_frozen_exposed_d2_gadr_diagnostic`;
- `d2_read=false`, `d3_read=false`, and `protected_c1_i1_read=false`.

The official aggregate and provenance were copied locally under
`results/gdp-cem-e8a-refinement-job-297721`; its recorded hashes verify.
