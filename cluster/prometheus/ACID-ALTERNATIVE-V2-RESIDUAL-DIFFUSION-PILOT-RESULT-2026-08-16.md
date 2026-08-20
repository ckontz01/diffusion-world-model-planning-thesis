# ACID-alternative v2 residual-diffusion pilot result

Date: 2026-08-16 (Asia/Nicosia)  
Status: **promising development result; preregistered promotion gates not fully passed**  
Confirmation status: **not confirmation**; C1 and I1 were not read or used

## Executive verdict

This experiment materially changes the assessment of the diffusion idea. The
original diffusion transition verifier was weakly action-conditioned and did
not outperform its controls. The redesigned residual/classifier-free/
contrastive diffusion verifier fixes that mechanism failure and produces the
strongest D1 candidate-failure rank correlation observed in the matched
seed-6101 comparison.

The result is genuinely promising, but it is not yet enough to claim a robust
alternative to ACID:

- the raw residual-diffusion score beats v1 diffusion significantly and is
  above the matched deterministic forward verifier as a point estimate;
- it is positive on PushT, Reacher, and Cube;
- a separately frozen action-evidence ratio beats its shuffled-action null
  decisively and gives the best observed `lambda=0.005` candidate-selection
  success/RMSE pair;
- nevertheless, the v2 raw-score gate and the E2 action-evidence gate each
  fail registered conditions, for different reasons;
- all results use one scorer seed and already observed D1 development data;
- `A0_acid` is our transparent equation-based ACID adaptation, not official
  ACID code, so these results do not establish superiority to faithful ACID.

The honest conclusion is: **diffusion now works well enough to justify a
carefully reframed, fresh-data study, but the “alternative to ACID” claim has
not yet been earned.**

## Frozen design and lineage

Primary residual-diffusion protocol:

- file: `ACID-ALTERNATIVE-V2-RESIDUAL-DIFFUSION-PILOT-PROTOCOL-2026-08-16.md`;
- SHA-256:
  `a6c33f33cc20da6e93ccdeb77269438de34869cb60c91b20e6da47801861ebff`.

Training source:

- `train_residual_diffusion_pilot_20260816.py`;
- SHA-256:
  `871ebc12c4af778031155f78b060e017c7060775d3f2e32bb49dc986925a52ad`.

D1 analysis source:

- `score_analyze_residual_diffusion_d1_pilot_20260816.py`;
- SHA-256:
  `7c1fc99ceb8f03a445cf56318f86c62413f7c14b1691c408f72c11773d7551f4`.

E2 action-evidence protocol and source:

- protocol SHA-256:
  `79ee6aa81284e5e10288917cac878cd35df30fa76b4da7d94434fd41dbaa817f`;
- analysis source SHA-256:
  `8be50caddaae970c054d14618bfde08cb1870d6423a1ffabb3fb74e62c32e703`.

Effective Slurm jobs:

- six-model seed-6101 training array: parent `297483`, effective element jobs
  `297484`, `297485`, `297486`, `297489`, `297490`, and `297483`;
- P1 gate: `297487`;
- residual-diffusion D1 score: `297488`;
- E2 action-evidence score: `297491`.

Every job completed with state `COMPLETED` and exit code `0:0` on the
Prometheus `a6000` partition, whose allocated device reported as NVIDIA RTX
6000 Ada Generation.

## What changed architecturally

The failed v1 epsilon denoiser could infer light injected noise from the next
latent without using the action. The v2 model instead:

1. predicts a standardized clean latent transition residual;
2. trains at `sigma in {0.25, 1.0, 4.0}`;
3. uses classifier-free action-conditioning dropout;
4. includes an explicit true-versus-permuted-action contrastive loss at high
   noise;
5. remains capacity matched to the v1 diffusion and deterministic-forward
   controls (about 2.03 million parameters).

This is a substantive architectural correction, not a score rescaling of the
failed v1 model.

## P1 mechanism gate

All tasks passed every frozen P1 gate.

| Task | True-action accuracy | Shuffled accuracy | Advantage | Accuracy at sigma=4 | Wrong-minus-true margin |
|---|---:|---:|---:|---:|---:|
| PushT | 0.99445 | 0.50287 | +0.49158 | 0.99398 | +0.81760 |
| Reacher | 0.94106 | 0.50150 | +0.43956 | 0.94796 | +0.45391 |
| Cube | 0.99923 | 0.49993 | +0.49929 | 0.99887 | +1.33751 |

This directly fixes the most important failure of v1: the model now uses the
action condition on held-out real P1 transitions, including Reacher.

P1 gate result:

- job: `297487`;
- summary SHA-256:
  `630eb6dfb7802ca8de5ff20e96d2c2a652af2b2d74d75c12ef23197226a16560`;
- decision: `advance_to_frozen_D1_pilot_scoring`.

## D1 candidate-failure ranking

The endpoint is within-pool Spearman correlation between candidate score and
the physically realized standardized rollout RMSE. Higher is better.

| Verifier | Equal-task estimate | 95% CI | PushT | Reacher | Cube |
|---|---:|---:|---:|---:|---:|
| Residual diffusion `RDX0_G100` | **0.25206** | **[0.18986, 0.31316]** | **0.34613** | **0.13916** | 0.27089 |
| Deterministic forward | 0.22394 | [0.16183, 0.28488] | 0.29139 | 0.10083 | **0.27961** |
| Shuffled residual diffusion | 0.21745 | [0.15835, 0.27566] | 0.22940 | 0.17019 | 0.25277 |
| v1 raw diffusion | 0.15966 | [0.09344, 0.22515] | 0.23759 | 0.03401 | 0.20737 |
| ACID adaptation | 0.04624 | [0.00575, 0.08704] | 0.02635 | 0.07850 | 0.03387 |

Registered paired contrasts for residual diffusion:

| Contrast | Estimate | 95% CI | Gate implication |
|---|---:|---:|---|
| minus v1 raw diffusion | **+0.09240** | **[+0.02804, +0.15940]** | pass |
| minus deterministic forward | +0.02812 | [-0.01878, +0.07538] | pass registered gap tolerance; not a significant win |
| minus shuffled residual diffusion | +0.03461 | [-0.00508, +0.07473] | **fail** |

The true score improves strongly over the shuffled model on PushT
(`+0.11674`) and slightly on Cube (`+0.01812`), but is worse on Reacher
(`-0.03102`). Generic transition-manifold denoising therefore explains a
substantial portion of the raw score's performance.

D1 result:

- job: `297488`;
- summary SHA-256:
  `74f0fcfea152f9ce0930b142171149b037b53a5a36a7134339c0b7ee6fc635a9`;
- cost archive SHA-256:
  `a959d93b704b78cd3999faa946ad1db0f7dfe16b93084257cbdbcd99491e6223`.

### Why the v2 promotion gate failed

Five of seven substantive D1 conditions passed. Two failed:

1. the lower 95% confidence bound for improvement over the shuffled model was
   `-0.00508`, not above zero;
2. at frozen `lambda=0.005`, residual diffusion improved success from `0.625`
   to `0.63889` but worsened standardized RMSE from `0.36469` to `0.37118`.

The alternate registered guidance `g=1.5` came close to the selection gate
(`0.65278` success, `0.36606` RMSE) but was not selected by the frozen ranking
criterion and cannot replace the recorded primary result after inspection.

## E2 action-evidence diagnostic

After recording the v2 failure, one new score-only diagnostic was frozen. It
uses the classifier-free branches of the already trained model:

`log(conditional MSE + 1e-12) - log(unconditional MSE + 1e-12)`.

No menu of transformations was searched. The shuffled model computes the
identical matched null. Recomputed conditional candidate costs reproduced the
v2 archive with maximum absolute errors between `1.55e-11` and `1.14e-8`,
well within the registered `1e-6` tolerance.

| Score | Equal-task estimate | 95% CI | PushT | Reacher | Cube |
|---|---:|---:|---:|---:|---:|
| True action evidence | **0.13735** | **[0.08181, 0.19357]** | 0.23100 | 0.01452 | 0.16654 |
| Shuffled action evidence | -0.00879 | [-0.05685, 0.03751] | 0.04817 | 0.00071 | -0.07526 |
| Paired true minus shuffled | **+0.14615** | **[+0.08150, +0.21123]** | +0.18283 | +0.01380 | +0.24180 |

This is the clearest evidence obtained so far that action conditioning matters
on imagined D1 trajectories rather than only on held-out real transitions.
However, action evidence is a weaker standalone global ranker than raw
residual diffusion and forward, and its Reacher point estimate is only
`0.01452`. Those facts correctly fail its registered ranking gates.

### Candidate selection at lambda=0.005

| Method | Equal-task success | Equal-task standardized RMSE |
|---|---:|---:|
| Action evidence E2 | **0.66667** | **0.36433** |
| Deterministic forward | 0.65278 | 0.36858 |
| ACID adaptation | 0.65278 | 0.38082 |
| v1 raw diffusion | 0.62500 | 0.36469 |
| Raw residual diffusion | 0.63889 | 0.37118 |

E2 is the only tested score in this table that is nonworse than v1 raw
diffusion on both registered selection metrics. Its per-task result remains
mixed: it improves PushT and Cube, while Reacher obtains higher success but
worse RMSE than v1 raw diffusion.

E2 result:

- job: `297491`;
- summary SHA-256:
  `26af7294f6a279b74273db7ae2cfa03b3c7a4c681d24bfe04fad6ecec88d5c33`;
- manifest SHA-256:
  `4816ce2c0588a34ce275c69705d785ee211f00375fe193d7ad4f09e364bbd212`.

## Claim boundary

The strongest defensible sentence today is:

> On one already observed D1 development seed, a capacity-matched
> action-conditioned residual-diffusion verifier significantly improved
> candidate-failure ranking over the original diffusion verifier, achieved a
> higher point estimate than the deterministic-forward control, and an
> independently frozen classifier-free action-evidence score significantly
> exceeded its shuffled-action null while producing the best observed
> `lambda=0.005` selection tradeoff.

The following sentences are **not** yet defensible:

- “diffusion is robustly better than deterministic forward”;
- “diffusion is a faithful replacement for ACID”;
- “the method generalizes across seeds or fresh data”;
- “the result is confirmatory.”

## Stop decision and next legitimate step

The current v2 and E2 promotion decisions are both recorded as failures. No
additional D1 transformation, task-specific exception, lambda, sign, or score
mixture will be tried under these protocols, and seeds `6102/6103` are not
automatically authorized by them.

The evidence does justify discussing a transparently new thesis framing with
the supervisor: raw residual diffusion is the high-quality generic failure
ranker, while classifier-free action evidence is a complementary mechanistic
and selection signal. If that framing is accepted, the next experiment must
be specified in a new protocol before execution, use fixed endpoints rather
than another D1 score search, include multiple scorer seeds, and make the
decisive assessment on isolated fresh D2 data. A faithful published-equation
ACID implementation and, when available, official ACID code remain required
before the final “alternative to ACID” comparison.
