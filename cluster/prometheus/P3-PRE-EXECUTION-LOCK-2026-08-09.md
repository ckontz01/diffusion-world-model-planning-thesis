# PushT P3 pre-execution lock

Status: **frozen before any P3 candidate-attainment execution or learned-score
evaluation**

Date: 2026-08-09  
Root seed: `20260728`

This file locks the scientific choices for the PushT P3 offline audit. P3 may
test these choices once, but no P3 value may alter a model, score direction,
architecture, sigma, tolerance, calibrator, weight, query count, candidate
count, exclusion, sample size, endpoint, null, or promotion criterion.

## Governing protocol

- Master protocol SHA-256:
  `c375855205d7d8d9f69d4669251bad1692b379de577534ea2bc4d1aa4af75c85`
- Implementation amendments through A-032 SHA-256:
  `44638501dd496fc8893d4e0ecc563824685229251c8227b5f9d3e6802af9db8e`
- Frozen Hi-LeWM checkpoint SHA-256:
  `b87805747d40037841877ce7b99b7dda3ebe7a52202c0ba46bf0006ab5d6f008`
- P1 M2 fixed-noise bank SHA-256:
  `3a94b491079e6030137480352d1ac0d985214db6ebd96f271539b2022edcf74b`

## Immutable P2-selected settings

- Imagined-candidate latent-attainment tolerance:
  `delta = 0.7168711644368866` P1-standardized latent RMSE, attained in at
  least 3 of 5 executions.
- M1: width 512; larger raw squared macro-cycle residual means greater failure.
- M2: width 1024; sigma 0.25; eight frozen noise draws; larger mean squared
  epsilon-prediction residual means greater failure.
- M3: frozen ASAR-style temporal head; larger predicted temporal separation
  means greater failure.
- Each learned method uses its three fixed training seeds independently and
  the arithmetic mean of the three P2-frozen Platt failure probabilities.
- Closed-loop weights, if an arm is promoted: M1 `2.0`, M2 `1.0`, M3 `0.25`.
- Positive class for discrimination and calibration is budgeted-attainment
  failure.

Immutable development artifacts:

- P2 real-frame tolerance HDF5, job `294668`:
  `d748303d886df769ed3770cab3ef0b5e2b664848923219e1f47ce7997d51e971`
- P2 imagined-candidate labels HDF5, job `294838`:
  `72031cd0ea7a02af2a33c61fb3db6f42c47b2982a31a544a2fe3fff011fc76c4`
- P2 true-scorer selection HDF5, job `294839`:
  `63bad1d8c97902f682a6aacfa21ef451f8c0cee7373a501b2de0d8f3e4b10ba1`
- P2 null/control calibration HDF5, job `294843`:
  `eced1f2842bc7ba9bda81ae4d2647200c3f30c7b1f25679025cfb9c60f9cad3f`
- P2 weight selection HDF5, job `294847`:
  `0bec312e2b85ec462501b2643d0d0c003408d59328ce8919f8f0f6d7ffdf1818`

## Immutable P3 inputs

- P3 latent cache HDF5, job `294787`:
  `18ba80c5346cdb99202a64b160e20f4eed9b8d0728f9b44fe0ac67e3c292e19b`
- P3 stratum-3 B0 candidate HDF5, job `294828`:
  `64341a03c5d618ebe1b5c6c86f701add6ee9ab841f2a20e57ead23fde35efdaf`
- P3 real-frame candidate HDF5, job `295090`:
  `390caf5b1ec32975a36d41242d38e039c2ad3c6ca1d9e1c727066c5e172ac771`

The imagined stratum contains 24 pools of 64 candidates. Each real-frame
stratum also contains 24 pools of 64 candidates. Every candidate receives the
same five frozen repeat seeds:
`[1070413377, 951166590, 4200525716, 38670800, 2537523285]`.

## Locked P3 analyses

1. Re-evaluate physical-versus-latent agreement on the two real-frame strata
   using `delta = 0.7168711644368866`; report combined and per-stratum Cohen's
   kappa. The tolerance is not reselected.
2. On imagined stratum 3, score M1, M2, and M3 true replicas and their frozen
   nulls. Also score the capacity-matched M2 autoencoder control and G0a/G0b
   as interpretation/geometry diagnostics.
3. Report per method: seed-wise and ensemble AUROC, AUPRC, failure prevalence,
   AUPRC minus prevalence, Brier score, 10-bin ECE, 2-of-5 and 4-of-5 label
   sensitivities, and per-pool diagnostics. Never pool candidate strata.
4. Use 10,000 paired bootstrap resamples of the 24 complete query pools,
   bootstrap seed `20260728`. A pool and all its candidates/executions remain
   together in every resample.
5. Promote an arm only if its primary-label ensemble AUROC is at least 0.70
   and the paired 95% bootstrap interval for AUROC improvement over its own
   null excludes zero. AUPRC and prevalence must also be reported but are not
   extra promotion thresholds.
6. M2 may support a diffusion-specific interpretation only if it passes the
   promotion gate and beats the capacity-matched autoencoder control. If it
   passes promotion without beating the autoencoder, describe it only as a
   reconstruction-error signal.
7. P4 closed-loop evaluation is permitted only for promoted arms, using the
   weights above and the already frozen 40 P4 seeds. Failed arms are reported
   honestly and receive no P4 rescue run.

P3 latent encoding and candidate construction were outcome-blind preparation,
not P3 evaluation. No P3 attainment label or learned-score result existed when
this lock was written.
