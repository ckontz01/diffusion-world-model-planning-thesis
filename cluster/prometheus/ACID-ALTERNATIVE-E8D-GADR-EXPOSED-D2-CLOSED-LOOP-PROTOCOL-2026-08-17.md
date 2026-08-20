# E8D GADR exposed-D2 closed-loop protocol

Date fixed before execution: 2026-08-17  
Role: one-model-seed development study on already exposed D2 starts  
Protected inputs: D3, C1, and I1 remain sealed and forbidden

## Scientific question and boundary

E8A qualified Gaussian-anchored diffusion refinement (GADR) on a disjoint
P1-validation set. Its immutable aggregate is
`/lustreFS/data/superworld/ckontzias/thesis/results/acid-alternative/gdp-cem-e8a-refinement/analysis/job-297721/summary.json`,
SHA-256
`d7d804d8ccf38c0b5dad3c5e46c3ad2f1a7396b892bf40d36d73d8bb16e35521`.
The decision was `authorize_separately_frozen_exposed_d2_gadr_diagnostic`.
The selected configuration was restart timestep `40`, one epsilon-denoiser
evaluation, and a refined fraction of `0.50`.

E8D asks whether that proposal improvement survives physical closed-loop
control and exceeds the published-equation ACID reconstruction. It does not
use diffusion as a scalar cost. Diffusion changes only the proposal
distribution; every candidate is still selected by the released Le-WM goal
cost and the ordinary CEM elite rule.

D2 outcomes from earlier verifier studies are already known, so E8D is
development evidence regardless of its result. Passing E8D authorizes only a
separately frozen multi-seed D2 replication. It does not authorize a claim or
access to D3/C1/I1.

## Immutable tasks, starts, and upstream artifacts

Run PushT, Reacher, and Cube on the exact 50 episode-isolated P3 D2 starts per
task created by job `297535`:

| Task | D2 manifest SHA-256 | Provenance SHA-256 |
|---|---|---|
| PushT | `85fd2bc499892be09a5e92000aab879e314ebc3100b11017c3864104d4d25e89` | `fcb07dfb55822bc6717c56016f62f26646a7486b8c834762d4bf0fd8eb771ede` |
| Reacher | `a8683cccfd998017fdf52f21ec6b3a588a4cbda2578049ba007f8bd4f817fd61` | `f175561fd58908ef9d226c4dcd9bda0e67d8dd4adfe1d01b35a4a3dd2fe46a11` |
| Cube | `bd131f4fc43e69311cf9722dfd678abb7cf888fe067ddf00f7310ff866eb7388` | `fa0dfb090aadeb1daadaf703707a64f049cac988c1c9074f0a09345eebb8a62b` |

Use the released Le-WM checkpoint and dataset already audited for each task.
Use proposal/model seed `6101`, planner seed `8301`, and independent proposal
seed `9101` in every arm. The exact E7P proposal checkpoints qualified by E8A
are:

| Task | Dataset SHA-256 | Le-WM checkpoint SHA-256 |
|---|---|---|
| PushT | `b6ebd9ac94bbe9e383f6e7a9cd92d74e9aa665ea57b758ed3717b0ee7df8d4fb` | `c3883fb585f4d97b628922a13a43441fe63e883808014d25312aca1793820659` |
| Reacher | `85a7dddfa1801302abcb175a80a23bb69c78291dd977ce40d69aedcb9123da06` | `6b03b0e39f00a601b83dc94765e4b022c48127ced762543bddb1398ce52c310d` |
| Cube | `0664d507c4ff12009010644c9ae950836f954e700c172ccf22e7423af1a55625` | `5175b8d7a99b3c19aeee08027c666fb0562e316f14c36e74ac3a52ecce531e07` |

The exact policy identifiers are `pusht/lewm_hf_22b330c`, `reacher/lewm`, and
`cube/lewm_hf_b0747c5`, respectively.

| Task | True diffusion | Shuffled-goal diffusion | Conditional Gaussian |
|---|---|---|---|
| PushT | `c97dcc80da47121b5cb04aea5a2273af191beb9e80f87a1cca8c968e486d9242` | `b18e24dba361a1358a14d3161bf5f27611c5abf6e291c7c63aed21c8ba32de09` | `c6e73b84d2b159dc1272df494563281561a64066f096853e5142fde9838b24ff` |
| Reacher | `5978c9fa6997aa9581d4622d41ac3a162379077ce0c183c8cad82613f5f923ca` | `e642a35a0ef6fc79e6876818a01e34b366385e439e0c769bf1ef0bce55f1015c` | `320187e4106db767fc57ea1fcc1e37eee1e767eea34f110623ef8903f1ba0b7a` |
| Cube | `a7be54e0cbab724b361077ea62e9e6894944b4d3a73940376f0af3b43992bee4` | `b147056b56cc69953b9f0d70e2c07eb4afb926444d33cbd0df4dadb58d0149b4` | `3481fe922c93183943f84bd72a0c53ad8671db3e5f36792ee38d502920d3e3ab` |

The primary ACID reconstruction uses seed `6101` and exact checkpoint hashes
`6b49d24ab9a3cfdbe4695343f3a9c30723f9ee4d70c892fe603f8e9818b3f9d2`
(PushT),
`8e0a7bad0f8c9d4ce574fca611d2642e5213e8831e7db0c7b4559939146ae5ab`
(Reacher), and
`dade8d6afd8392f475d1e56c031f330c4e72c924e2c4254c2bcca5bf6d6be416`
(Cube). It remains a transparent reconstruction of the published equations,
not unreleased official ACID code.

## Exact GADR proposal construction

All proposal calculations begin in the proposal checkpoints' standardized
primitive-action coordinates.

For a requested learned bank of `M` action sequences:

1. encode the current observation and goal with the frozen Le-WM encoder and
   apply the P1-train latent standardizer stored in the checkpoints;
2. evaluate the conditional diagonal-Gaussian model once;
3. draw a complete `M`-candidate Gaussian noise tensor from the proposal RNG,
   set candidate zero to the conditional mean, and clamp to the stored
   P1-train 0.001/0.999 robust bounds;
4. draw one complete matched forward-noise tensor at cosine timestep `40`;
5. use one epsilon-denoiser evaluation to project every base candidate to a
   predicted clean action sequence, clamping to the same bounds;
6. retain the Gaussian base and replace the first
   `floor((M-1)*0.50 + 0.5)` non-mean candidates by their projected versions;
7. inverse-standardize and reshape the 25 primitive actions to five Le-WM
   macro actions.

True and shuffled GADR use identical current/goal inputs, Gaussian bases,
forward noise, candidate positions, and all non-model randomness. Their
training goal pairing is the only intended difference. The Gaussian control
draws and discards the same matched forward-noise tensor so that its subsequent
proposal RNG stream remains aligned, but performs no replacement.

## Planner integrations and frozen arms

Shared closed-loop settings are 300 candidates, 30 CEM iterations, 30 elites,
variance scale one, five macro actions, five primitive actions per macro,
receding horizon five, goal offset 25, evaluation budget 50, and 50 starts.
Every CEM iteration draws the complete ordinary Gaussian bank before any
candidate overwrite. Candidate zero remains the current CEM mean.

Run exactly ten arms per task:

1. `b0`: released original CEM;
2. `custom_b0`: custom proposal-capable solver with injection disabled;
3. `acid`: audited one-sample published-equation reconstruction at
   `lambda=0.07`;
4. `gaussian_refresh`: overwrite `round(299*0.50)=150` non-mean slots in every
   iteration with the learned Gaussian bank;
5. `gadr_shuffled_refresh`: identical refresh using shuffled-goal GADR;
6. `gadr_true_refresh`: identical refresh using true-goal GADR; this is the
   primary matched-budget method;
7. `gadr_true_first`: the same true GADR overwrite only in CEM iteration one;
   this is an integration ablation and cannot replace the primary result;
8. `gaussian_select`: generate 300 Gaussian proposals, evaluate each once,
   and execute the lowest-cost actual candidate;
9. `gadr_shuffled_select`: the identical one-pool shuffled-GADR selector;
10. `gadr_true_select`: the identical one-pool true-GADR selector; this is the
    separately assessed efficiency method.

The selector arms use no CEM Gaussian, no elite mean, and one 300-candidate
Le-WM evaluation per planning call. The matched-budget refresh arms retain all
`300*30` Le-WM candidate evaluations. No verifier cost, ACID cost, guidance
weight, success predictor, or post-hoc score is added to a GADR arm.

The two fractions have distinct, fixed meanings. A refresh call overwrites 150
of the 299 non-mean CEM slots with one GADR bank of size 150; within that bank,
exactly 75 candidates are diffusion-refined, one is the learned Gaussian mean,
and 74 remain Gaussian draws. A selector bank has size 300; exactly 150
candidates are diffusion-refined, one is the learned Gaussian mean, and 149
remain Gaussian draws. Thus the primary arm injects 75 diffusion-refined
candidates per CEM iteration, not 150. This effective treatment count is part
of the frozen design and must be checked from runtime diagnostics.

## Integrity checks and outcomes

Before launch, unit tests must establish:

- exact one-step refinement against an oracle calculation;
- identical Gaussian bases and forward noise for true/shuffled/control arms;
- matched RNG consumption across proposal conditions;
- exact candidate counts, slots, bounds, refresh timing, and candidate-zero
  preservation;
- custom solver equality with released CEM on deterministic synthetic inputs;
- all checkpoint, E8A aggregate, D2 manifest/provenance, dataset, world-model,
  protocol, and source-manifest hashes;
- rejection of tokenized D3/C1/I1 artifact paths.

`custom_b0` and `b0` must produce bit-identical 50-episode success vectors in
each task. A mismatch invalidates every custom-solver arm rather than being
treated as a method result.

The primary outcome is binary environment success. Report every task and the
equal-task mean. Report paired success differences, two-sided 95% intervals,
one-sided 95% lower bounds, and exact discordant-start sign tests. Use 100,000
task-stratified start-cluster bootstrap repetitions with seed `2026081705`.
Also report end-to-end wall time, Le-WM cost-call count, proposal-call count,
proposal time, clipping fraction, refinement displacement, and peak CUDA
memory.

## Frozen advancement rules

The primary `gadr_true_refresh` route advances to a separately frozen
three-model-seed D2 replication only if all conditions hold:

1. its equal-task success point estimate is strictly above `acid`;
2. it is strictly above `b0`;
3. it is strictly above `gaussian_refresh`;
4. it is strictly above `gadr_shuffled_refresh`;
5. it exceeds `gadr_shuffled_refresh` on at least two of three tasks;
6. it is no more than 0.10 below `acid` in any task; and
7. all arms and integrity checks pass, including bit-identical B0 replay.

The efficiency `gadr_true_select` route is assessed separately and advances
only if it is strictly above `gaussian_select`, `gadr_shuffled_select`, and
`b0`; is no more than 0.05 below `acid` on the equal-task mean; exceeds the
shuffled selector on at least two tasks; and all integrity checks pass. A
selector pass supports an efficiency hypothesis, not superiority to ACID,
unless its point estimate also exceeds ACID.

Both rules are fixed before any GADR D2 outcome is read. Confidence intervals
are mandatory diagnostics but do not gate this one-model-seed pilot. A passing
point-estimate pilot still requires model seeds `6102/6103`, paired planner
seeds, and confidence intervals before any fresh-data study. Failure stops the
corresponding integration. No arm, task, weight, fraction, restart level,
reverse-step count, seed, start, or success definition may be changed after
inspection to rescue a failure.
