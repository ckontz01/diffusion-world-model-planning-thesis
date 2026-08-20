# E12 matched-PRISM untouched-D4 closed-loop protocol

Frozen-design date: 2026-08-20  
Status: freeze candidate; no D4 outcome may be read until this protocol and its implementation snapshot pass preflight  
Protected inputs: P4, C1, and I1 remain sealed and are never inputs to E12

## 1. Question, scope, and chronology

E12 asks whether E11's frozen latent-conditioned velocity-diffusion action
generator retains a diffusion-specific and compute-efficiency advantage when
compared directly with PRISM-style learned action priors on the same Le-WM
checkpoints, datasets, starts, candidate budgets, evaluation goals, model
seeds, and hardware.

The design was written after the E11 D3 result and after discovering the
public PRISM repository. E11's result is therefore prior development evidence,
not confirmatory evidence for E12. E12 uses a new, identifier-selected D4
sample from the still-unread part of P3. It does not reuse D3 outcomes in any
E12 claim interval.

The E11 result that motivated E12 was:

- `vp_true_select`: 93.39% equal-task success;
- `gaussian_select`: 90.64%;
- reconstructed ACID: 83.31%; and
- the paired diffusion-minus-Gaussian effect: +2.75 percentage points,
  two-sided 95% start-cluster interval [1.64, 3.89].

Those numbers cannot be treated as E12 confirmation because they influenced
the choice to audit PRISM and add the new comparators.

E12 distinguishes three claims that must not be conflated:

1. **Published PRISM:** a conditional diagonal-Gaussian action prior fused
   with MPPI through a Product of Gaussians (PoG).
2. **Public post-paper PRISM extension:** the repository's August 2026
   `best_of_n` mode, which samples action sequences from a diffusion policy and
   ranks them once with the Le-WM cost.
3. **E11 treatment:** a frozen-Le-WM-latent-conditioned velocity-diffusion
   action generator whose candidates are ranked once with the same Le-WM
   cost.

The second and third occupy the same planner slot. Their direct comparison is
therefore the novelty-critical comparison. No hybrid diffusion-plus-ACID or
diffusion-plus-PRISM arm is part of E12.

## 2. PRISM artifact status and attribution

The public PRISM repository is pinned to commit
`baa0eb95efb812196b68796c258b1f0cf10b7625`. The audited files and SHA-256
digests are:

- `prior_head.py`: `6a60613ea2acd10b9185d415868a9006acf27f1211df3b3e4758c2458921617c`;
- `prism_mppi.py`: `4e6d2430f4bf64c5d901c5bf4db986e8bf4436618591b983543b5e8f63cd62e6`;
- `train_prior_head.py`: `0524f78bd796665213cc1045e576dc68ae8dc2fe015084620ee6cc3340ec5881`;
- `dp_baseline/dataset.py`: `07a3c2706b79242c16778c8a79b3c92605e4495a58b0ffd38b7a0ee5d55d2b62`;
- `dp_baseline/train.py`: `e9a617a8abb9e8d9c5970c8d9ef96e237ec14170fa80068d6317f9c7e25e6feb`;
- `docs/23_diffusion_policy_baseline.md`:
  `59677186511b4dde1c45f1048f79b89aa8ca85f635a9108da84ce5dd8bc87578`;
- `eval_dp_prior.py`: `983279b6d6fd9562061f0593efad7473a5d8312233982a3697791d499181f01e`;
- `dp_prior_policy.py`: `4f34dd683427ee28ff3677d97ae0603f732bda5684382101bda2a880df8af494`;
  and
- `LICENSE`: `1e9c03c85e67143e960a8a3befc5cc14f14008456d563e9c3f9ac7cdbc411df5`.

The published Gaussian PriorHead and PoG-MPPI path is publicly runnable and
will be implemented from the pinned equations with parity tests against the
pinned source.

The public repository does **not** contain
`dp_baseline/model.py`, `dp_baseline/scheduler.py`, or the diffusion-policy
checkpoint used for its `best_of_n` table. Git history at the pinned clone was
audited and those modules were never committed. Consequently, E12 must label
that arm **PRISM-DP best-of-N reconstruction**, never official PRISM-DP. Its
architecture and training recipe are fixed below from the repository's own
documentation. The missing-code fact and all reconstruction choices must be
reported in the paper.

## 3. Data partitions and untouched D4 starts

All learned E12 components use P1 only. P2 is development-only. D3 is exposed
and excluded. D4 is selected from unused P3 episode identifiers. P4, C1, and
I1 remain sealed.

Before this protocol was written, identifier-only auditing established these
unused P3 episode counts after excluding every R0, D1, D2, and D3 episode:

- PushT: 1,360;
- Reacher: 556; and
- Cube: 489.

No outcome, image, action, reward, success flag, or result from those
remaining episodes was read.

For each task, select exactly 400 distinct eligible episodes and one start per
episode. The fixed goal offset is 25 environment steps, the evaluation budget
is 50, and `dataset_goal_step = start_step + 24`, matching E11's released
evaluation convention.

For every eligible episode enumerate `range(episode_length - 25)`. Select that
episode's start with the lexicographically smallest SHA-256 digest of

`gdp-e12-d4<NUL><task><NUL>2026082001<NUL><episode_id><NUL><start_step>`.

Sort the one-per-episode records by `(digest, episode_id, start_step)` and take
the first 400. Record input hashes, counts before and after every exclusion,
the selected-row hash, and zero intersections. Existing output is never
overwritten.

The selector may read only episode identifiers, partition labels, episode
lengths/offsets, exclusion identifiers, frozen source/protocol bytes, and the
complete dataset byte stream solely for a predeclared SHA-256 check. It may
not deserialize observations, actions, rewards, goals, success values, videos,
or prior result summaries.

The 400 rows are split into eight immutable contiguous 50-row resource shards
by `eval_index`. Sharding is not an analysis factor. Every arm receives the
same rows in the same order.

After D4 is generated, no metric-bearing output may be inspected until every
required D4 shard has terminated and the single frozen aggregate analysis has
run. Scheduler state, exit status, file existence, byte count, and checksums
may be monitored without opening result contents.

## 4. Fixed shared stack and randomness

Use the same released Stable-WorldModel datasets, Le-WM checkpoints, latent
preprocessing, action scalers, task success callable, goal offset, 50-step
budget, and frozen E11 velocity/Gaussian checkpoints already hashed by E11.
Do not retrain or select among the E11 checkpoints.

Use model seeds `6101`, `6102`, and `6103`. Use base planner/environment seeds
`8301`, `8302`, and `8303`. Use velocity proposal seeds `9101`, `9102`, and
`9103`, Gaussian proposal seeds `9201`, `9202`, and `9203`, PRISM-DP proposal
seeds `9301`, `9302`, and `9303`, and MPPI proposal seeds `9401`, `9402`, and
`9403`.

For every task/seed/shard derive an executed stream seed as the first eight
little-endian SHA-256 bytes modulo `2^63-1` of

`gdp-e12|<namespace>|<task>|<base_seed>|<shard>`.

Every arm in a task/seed/shard uses the same derived environment seed. Paired
variants within a proposal family use the same family proposal stream. No
method may reuse another method's random draws merely to induce artificial
correlation where the candidate distributions differ.

All timed confirmation shards must run on `gpu09.cluster` with an NVIDIA RTX
6000 Ada Generation. The analyzer rejects mixed hardware. Native artifact
sanity runs may use another GPU but are reported separately and never enter a
D4 interval.

## 5. Frozen learned components

### 5.1 E11 velocity diffusion and Gaussian control

Reuse E11 exactly:

- frozen Le-WM current/goal latents;
- complete standardized 25-action trajectories;
- width 512 and four FiLM residual blocks;
- velocity prediction;
- classifier-free conditioning dropout 0.15;
- deterministic five-evaluation velocity-DDIM sampling;
- guidance 1.5 for the treatment;
- E10M's P1-only latent/action statistics and robust action bounds; and
- one Le-WM rollout to select the lowest-cost actual candidate.

The Gaussian control retains E11's capacity-matched conditional diagonal
Gaussian architecture and P1 training. It remains mandatory: it isolates the
benefit of iterative diffusion sampling from the benefit of any learned
conditional proposal.

### 5.2 Published-equation PRISM Gaussian PriorHead

Train a separate head per task and seed on P1 only. The architecture is fixed
to:

- input `concat(z_current, z_goal)` with the released frozen Le-WM encoder;
- `Linear(384,512)`, GELU, `Linear(512,512)`, GELU;
- a final output of `2 * (25 * raw_action_dim)`;
- unconstrained mean; and
- standard deviation `softplus(raw_sigma) + 0.05`.

Train with beta-NLL at beta 0.5, AdamW learning rate `3e-4`, weight decay
`1e-4`, batch 256, 50 epochs, 1,000-step linear warmup followed by cosine
decay, gradient clipping at 1.0, and best P1-validation NLL. Action targets use
the same P1-train StandardScaler later used by the planner.

Two predeclared goal-pair variants are trained because the pinned published
simulation code used episode-final goals while the shared Le-WM evaluation
queries a goal 25 steps ahead:

1. `endframe`: the published simulation training convention; and
2. `h25`: the same equations and optimizer with `z_goal` at start + 25,
   removing the known train/evaluation goal-distance mismatch.

The `h25` arm is the fairness comparator; `endframe` is the fidelity
sensitivity. Neither may be selected after seeing D4.

At planning time fuse the unit base Gaussian with the head Gaussian using
Product-of-Gaussians precision addition, prior scale `s=1`, and output standard
deviation floor 0.05. MPPI uses K candidates, 30 iterations, temperature 0.5,
top-k 30, and keeps the fused standard deviation fixed across all iterations
while updating the mean with MPPI weights.

### 5.3 PRISM-DP best-of-N reconstruction

Train one image-conditioned diffusion policy per task and seed on P1-train
episodes; select checkpoints using P1-validation loss only. Pair the current
image with the image at exactly start + 25 and target the next 25 raw actions.

The reconstruction is fixed to the public repository's documented recipe:

- shared small CNN image encoder, 224x224 RGB to a 256-dimensional feature;
- concatenate current and goal image features, then a two-layer MLP to a
  256-dimensional condition;
- FiLM-conditioned one-dimensional U-Net with channels 64, 128, 256, and 512,
  Mish activations, and an implementation parameter count reported exactly;
- epsilon prediction over a 25-action trajectory;
- 100-step cosine (`squaredcos_cap_v2`) DDPM training schedule;
- deterministic 10-step DDIM sampling;
- per-dimension min-max action normalization to [-1,1], fit on P1-train only;
- AdamW learning rate `1e-4`, weight decay `1e-6`, batch 128;
- 100,000 optimizer steps, 500-step warmup plus cosine decay;
- gradient clipping at 1.0; and
- EMA decay 0.999, with EMA weights used at evaluation.

All choices not recoverable from the public artifact, including exact
convolution kernels, residual-block counts, padding, and timestep embedding,
must be written into the immutable E12 implementation manifest before P2 or
D4 evaluation. The implementation must have deterministic shape/scheduler
tests and report its divergence from the unavailable original code. It must
not be called an exact reproduction.

At evaluation, sample K complete trajectories, denormalize them, convert them
through the same planner action scaler, run exactly one Le-WM candidate-cost
call, execute the lowest-cost actual candidate for the shared 25-step
replanning cadence, and then replan.

## 6. Staged execution and information barriers

### Stage A: native PRISM artifact sanity

Using the official PRISM PushT and Cube bundles at pinned Hugging Face
revisions, reproduce vanilla MPPI and published Gaussian-PoG-MPPI at K=128,
30 iterations, seeds 0, 1, and 42, N=50. This checks artifact integration only.
It does not enter any matched thesis comparison because its model/data split
and checkpoints differ from E11.

### Stage B: matched P1 training and parity

Train both PRISM PriorHead goal variants and the PRISM-DP reconstruction for
all three tasks and seeds. Before any P2 or D4 evaluation require:

- exact PriorHead forward/loss/PoG numerical parity with the pinned source;
- fixed-variance MPPI update parity on synthetic tensors;
- no P2/P3/P4/C1/I1 identifier in any training or validation sample;
- disjoint P1-train/P1-validation episode identifiers;
- action-normalization round-trip and train-only statistics tests;
- diffusion scheduler determinism, shape, finite-value, and EMA-load tests;
- exact candidate-count and replanning-cadence tests;
- checkpoint/config/source/data hashes; and
- a P1-only closed-loop smoke for every policy family.

Failure blocks later stages. An implementation correction creates a new
snapshot and repeats Stage B; it may not alter the statistical gates below.

### Stage C: exposed-P2 budget and efficiency curves

P2 is explicitly developmental. Run success, latency, Le-WM-cost-call, peak
memory, candidate-diversity, and boundary-fraction curves for:

- one-pass selectors (`gaussian`, `vp`, `prism_dp`) at
  K in {1, 16, 32, 128, 300}; and
- iterative planners (`vanilla_mppi`, `prism_pog_h25`,
  `prism_pog_endframe`) at K in {32, 64, 128, 300} with 30 iterations.

Stage C may diagnose bugs and populate compute curves. It may not change D4's
primary K values, training recipes, superiority/non-inferiority margins,
inference, arms, or goal pairing. Any bug fix requires a new source snapshot
and full preflight before D4.

### Stage D: untouched-D4 confirmation

Run exactly ten arms:

1. `b0_cem_k300`: released 30-iteration CEM;
2. `acid_cem_k300`: E11's published-equation ACID reconstruction;
3. `latent_gaussian_select_k300`: E11 Gaussian proposal control;
4. `vp_select_k300`: primary proposed treatment;
5. `prism_dp_select_k300`: primary direct PRISM-DP reconstruction comparator;
6. `vp_select_k16`: secondary matched public-artifact candidate budget;
7. `prism_dp_select_k16`: secondary public-artifact candidate budget;
8. `vanilla_mppi_k128`: matched published-compute MPPI control;
9. `prism_pog_h25_mppi_k128`: fairness PRISM-PoG comparator; and
10. `prism_pog_endframe_mppi_k128`: published-training-convention sensitivity.

Total confirmation design:
`3 tasks x 3 seeds x 10 arms x 400 starts = 36,000 episodes`, implemented as
`3 x 3 x 10 x 8 = 720` 50-episode resource shards.

Selector arms use one Le-WM candidate-cost call per planning decision. CEM and
MPPI arms use 30. The K=16 selector contrast answers whether the conclusion
holds at the public extension's stated N; K=300 is the primary matched-E11
contrast and may not be replaced by whichever looks better.

## 7. Outcomes and inference

The primary outcome is binary environment success under the released task
callable. Report per-task results first, then equal-task aggregates. Explicitly
flag task ceilings, especially Cube. Never pool raw episodes across tasks.

For every arm also report:

- every task and model seed separately;
- paired success differences and discordance;
- end-to-end, proposal-generation, encoder, and Le-WM scoring time;
- Le-WM cost calls and candidate evaluations per decision and episode;
- trained and total parameter counts, including whether a second image encoder
  is required;
- peak CUDA memory;
- action boundary fraction and proposal diversity; and
- checkpoint, source, protocol, manifest, hardware, and result hashes.

For a treatment-control contrast, first average the three paired seed outcomes
within each `(task, eval_index)`. The primary interval is conditional on the
fixed three model/planner-seed blocks and uses 100,000 task-stratified paired
bootstrap repetitions over those start clusters with seed `2026082002`.
Report the two-sided 2.5/97.5 percentile interval and the one-sided fifth
percentile lower bound. A secondary two-way bootstrap independently resamples
the three seed blocks and starts within tasks, preserving arm pairing, with
seed `2026082003`. Also report the exact paired sign test over non-tied
start-cluster differences. Individual episodes are never bootstrapped as
independent observations.

Holm-adjust the two-sided descriptive sign-test p-values for the treatment
contrasts with B0, ACID, and both PRISM-PoG arms as one family. Gatewise tests
below are hierarchical or intersection-union tests and do not imply a single
simultaneous confidence set for every table entry.

## 8. Frozen claim gates

### 8.1 Replication of the diffusion-specific mechanism

`vp_select_k300` passes the E12 diffusion-specific replication only if, versus
`latent_gaussian_select_k300`, it has:

1. a strictly positive equal-task point estimate;
2. a one-sided 95% start-cluster lower bound above zero;
3. a positive task point estimate on at least two of three tasks;
4. no task point estimate below Gaussian by more than 0.05; and
5. finite, non-degenerate proposals with boundary fraction below 0.25 in every
   task/seed.

This is the claim that iterative diffusion matters beyond a learned Gaussian
proposal. It is mandatory for any diffusion-specific paper claim.

### 8.2 Direct superiority to PRISM-DP reconstruction

Only if Gate 8.1 passes may E12 claim superiority over the direct planner-slot
competitor. At K=300, `vp_select_k300 - prism_dp_select_k300` must have:

1. a positive equal-task point estimate;
2. a one-sided 95% start-cluster lower bound above zero;
3. a positive point estimate on at least two tasks; and
4. no task estimate below PRISM-DP by more than 0.05.

The allowed wording is “superior to our disclosed PRISM-DP best-of-N
reconstruction on the tested Le-WM suite and fixed three-seed set.” Because
the public DP implementation/checkpoint is incomplete, “superior to PRISM” or
“superior to official PRISM-DP” is prohibited.

### 8.3 Compute-efficient alternative to PRISM-DP reconstruction

If Gate 8.2 fails, an efficiency claim is allowed only if Gate 8.1 passes and
the K=300 velocity treatment:

1. has a one-sided 95% success lower bound versus PRISM-DP of at least -0.03;
2. has lower median paired end-to-end time across matched 50-episode
   `(task, seed, shard)` blocks on every task; and
3. has either fewer trainable parameters, no second image encoder, or lower
   peak CUDA memory, with the exact measured distinction named rather than
   collapsed into “more efficient.”

K=16 is a secondary robustness analysis and cannot rescue a failed K=300 gate.

### 8.4 Published PRISM and ACID comparisons

PRISM-PoG is an iterative learned-prior planner, not the same compute class as
a one-pass selector. Compare it on both success and a Pareto table containing
latency, Le-WM calls, and candidate evaluations. A superiority statement
against PRISM-PoG requires a positive pooled point estimate, a one-sided lower
bound above zero, positive estimates on at least two tasks, and no task harm
greater than 0.05; otherwise report it descriptively.

ACID remains E11's transparent published-equation reconstruction because no
official implementation is used. The only allowed wording is “our
published-equation ACID reconstruction.” Report any known gap between this
reconstruction and the paper's published numbers next to the comparison.

## 9. Failure, correction, and stopping rules

Before D4 exists, implementation defects may be corrected without changing
the frozen statistical design; every correction requires a new immutable
snapshot, changelog entry, and complete preflight. Once D4 exists, no tuning,
arm replacement, rescue model, checkpoint selection, budget change, seed
change, margin change, inference change, or implementation change is
permitted. An execution failure may only be rerun from identical snapshot,
manifest, arm, seed, shard, and dependency hashes.

If any learned component fails Stage B validity, report the failure and do not
consume D4. If Stage C reveals that a fixed arm is computationally impossible
under the declared hardware limit, amend the protocol transparently before D4
generation and treat the resulting experiment as E12.1, not E12.

If the mechanism gate or both PRISM-DP claim routes fail, report the complete
negative result. No post-hoc task deletion, especially removal of Reacher or
Cube, is permitted. Cross-backbone PLDM, hybrid verifier combinations, and
new architectures require later protocols and cannot rescue E12.
