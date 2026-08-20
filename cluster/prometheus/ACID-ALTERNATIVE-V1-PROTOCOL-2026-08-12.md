# Native ACID and diffusion-transition-verifier matched study

Status: **pre-data protocol v1.0**  
Frozen: 2026-08-12, before any result from the implementations described here  
Scope: Le-WM first; PLDM only after a usable checkpoint lineage is established  

## 1. Question and claim boundary

The primary question is whether a post-hoc conditional diffusion transition
verifier (DTV) can be a practical alternative to Action Consistency via Inverse
Dynamics (ACID) for repairing decision-time planning with a frozen latent world
model.

This study does **not** use the earlier hierarchical single-macro M1 or M2
implementation as ACID or as confirmatory evidence. Native ACID scores every
adjacent transition in the flat world-model rollout. The new DTV is likewise
action-conditioned and scores every adjacent predicted transition. Earlier
P2/P3/P4 work remains an explicitly exploratory record and is excluded from
all tests below.

The strongest allowed conclusion is:

> Under matched Le-WM/PLDM planning conditions, an action-conditioned
> diffusion transition verifier provides a statistically supported alternative
> to ACID for ranking model-predicted trajectories.

That conclusion is earned only if all gates in Section 11 pass. If only Le-WM
is completed, the conclusion must say "on Le-WM," not "across latent world
models." If DTV does not beat the deterministic forward verifier, no
diffusion-specific benefit may be claimed.

## 2. Primary sources and implementation status

- ACID paper: <https://arxiv.org/abs/2607.02403>
- ACID project: <https://gawon1224.github.io/ACID/>
- Le-WM paper/code: <https://arxiv.org/abs/2603.19312> and
  <https://github.com/lucas-maes/le-wm>
- PLDM paper/code: <https://arxiv.org/abs/2502.19337> and
  <https://github.com/vladisai/PLDM>
- TRM paper: <https://arxiv.org/abs/2605.22164>

At freeze time, the ACID project still labels code as "coming soon." Therefore
the ACID arm is a transparent reimplementation of the published equations and
appendix, not an official-code reproduction. The implementation report must
list every choice not fixed by the paper. If official code appears before
confirmation begins, it is audited in a new implementation note; confirmation
is not silently rerun with changed code.

The Le-WM repository currently links a Google Drive archive for its full
baseline suite, but that folder returns HTTP 404. Official Le-WM checkpoints
and datasets remain available from the authors' Hugging Face collection. The
PLDM portion is therefore conditional: use a recovered, hash-verified Le-WM
suite checkpoint if one becomes available, or train PLDM from its official
code and report that reconstruction as such. A reconstructed PLDM that cannot
approximately reproduce its published original-CEM baseline cannot support
the cross-backbone claim.

## 3. Frozen benchmark interface

The core environments are PushT, Reacher, and single-cube OGBench Cube. For
each available backbone, every arm uses exactly the same:

- world-model checkpoint and frozen encoder;
- HDF5 dataset bytes and train/development/confirmation manifests;
- observation preprocessing and action standardization;
- start states, goal states, goal offset, and evaluation budget;
- initial candidate tensors and all underlying standard-normal CEM innovations
  within each paired planner run;
- CEM update rule, warm start, number of iterations, population, and elites;
- environment reset and success implementation;
- GPU model and software container within a reported comparison block.

The Le-WM/ACID headline configuration is the released Le-WM configuration:

| Setting | Value |
|---|---:|
| Goal offset | 25 primitive environment steps |
| Evaluation budget | 50 primitive environment steps |
| World-model horizon | 5 action blocks |
| Action block | 5 primitive actions |
| Receding horizon | 5 action blocks |
| CEM population | 300 |
| CEM iterations | 30 |
| CEM elites | 30 |

The rollout contains the encoded initial state and five predicted successor
latents. Native transition scorers consume all five tuples
`(z_hat[t], action_block[t], z_hat[t+1])`. No arm may rerun the world model to
obtain a private trajectory.

After the first CEM update, candidate tensors necessarily diverge because each
cost selects different elites and therefore a different mean and variance.
Claiming identical later candidate tensors would be incompatible with testing
the costs as actual CEM objectives. Exact identical-pool comparisons are made
separately in the same-candidate audit: a frozen candidate pool is rolled out
once and every cost ranks those exact trajectories. Closed-loop comparisons
instead use common random numbers (the same Gaussian innovations at every CEM
iteration), which is the strongest valid pairing for independently optimized
CEM arms.

## 4. Arms

### B0 — original CEM

The unmodified terminal latent goal cost from the released world model:

`c_g = ||z_hat[H] - z_goal||^2`.

### A1 — faithful native ACID reimplementation

Train a separate inverse dynamics model for each task/backbone on real,
within-episode, one-model-step transitions. Its published architecture is a
four-layer, three-head, width-192 prefix/suffix transformer. Two latent tokens
form the prefix; a suffix token contains the noisy action and sinusoidal flow
time embedding. The attention mask permits prefix-to-prefix attention and
suffix-to-all attention, while preventing prefix tokens from attending to the
suffix.

Training follows the paper:

- straight flow path `x_tau = tau * epsilon + (1 - tau) * action`;
- velocity target `epsilon - action`;
- `tau ~ Beta(1.5, 1.0)`;
- actions standardized per training dimension;
- 90/10 transition train/validation split, with no episode-boundary pairs;
- 200,000 optimizer steps, batch 256;
- AdamW, peak LR `1e-4`, betas `(0.9, 0.999)`, weight decay `1e-4`;
- 1,000-step linear warm-up, cosine decay to zero, gradient norm clip 1;
- bf16 mixed precision on supported GPUs.

Inference uses the paper's single Euler step for all three core tasks. For a
candidate trajectory:

`c_A = mean_t ||action[t] - IDM(z_hat[t], z_hat[t+1])||^2`.

The primary ACID weight is the paper value `lambda = 0.07`.

Published text does not fix transformer normalization/MLP ratio, exact
sinusoidal embedding, or inference-noise reuse. The reimplementation freezes
pre-layer normalization, GELU, MLP ratio 4, the standard transformer
sinusoidal embedding, learned three-token positional embeddings, and a common
fixed Gaussian noise bank per verifier seed and horizon slot. The same noise is
reused across candidates and CEM iterations so candidate comparisons use
common random numbers. These are declared reconstruction choices, not
attributed to ACID's authors.

### R1 — learned reachability / TRM hybrid

Train the published pair head on frozen latent pairs using features
`[z_i, z_j, z_i-z_j, abs(z_i-z_j)]`, two hidden layers of 256 SiLU units, a
Softplus scalar output, AdamW LR `1e-3`, weight decay `1e-4`, batch 1024, and
Smooth-L1 loss. Use 100,000 balanced training pairs and 10,000 held-out pairs.

For Reacher and Cube, the generic label is within-episode temporal separation,
balanced over the available full episode and scaled by the task's maximum
training separation. For PushT, the faithful TRM arm uses its published
task-state-distance target; a temporal-label PushT head is retained only as an
ablation because the TRM paper explicitly uses task state for PushT.

At planning time, R1 scores only `(z_hat[H], z_goal)`. The primary version is
the standardized hybrid, which is rank-equivalent to the adaptive combination
in Section 5. Replacement-only TRM is secondary.

### D1 — diffusion transition verifier (proposed)

Train a conditional denoiser on the same real, one-model-step tuples used by
ACID. Latents are standardized from training data. For noise level `sigma`,

`z_noisy = z_next + sigma * epsilon`

and the model predicts `epsilon` conditioned on `(z_current, action_block,
z_noisy, sigma)`. Sigma is sampled log-uniformly from `[0.01, 1.0]` during
training. The denoising objective is mean squared noise-prediction error.

The network is a residual MLP with SiLU activations, LayerNorm, three residual
blocks, and base width 384. It is trained for 200,000 steps with the same batch
size, optimizer, learning-rate schedule, mixed precision, and gradient clipping
as A1. Checkpoint selection uses held-out real-transition denoising loss only.

At planning time, D1 evaluates the denoising residual of each predicted
transition under its conditioning action and averages over the five rollout
steps. Primary inference uses a fixed common-random-number bank and the three
predeclared standardized noise levels `{0.10, 0.25, 0.50}`; the mean across
levels is the scalar cost. The one-level versions are latency/sensitivity
ablations and cannot replace the primary version after confirmation outcomes
are seen.

### F1 — capacity-matched deterministic forward verifier

F1 predicts standardized `z_next` from standardized `(z_current,
action_block)` and scores mean squared forward residual on each predicted
transition. It uses the same residual-block family, activation, normalization,
training tuples, optimizer, batch size, updates, validation split, and
checkpoint rule as D1. Its hidden width is selected mechanically before
training to make its trainable parameter count within 2% of D1; validation or
closed-loop results cannot influence this width.

F1 is the load-bearing diffusion control. D1 versus F1 asks whether denoising
at multiple noise scales adds value beyond attaching another learned neural
transition model.

## 5. Identical cost integration

For every additive arm `m` with raw verifier cost `c_m`, compute spreads over
the current CEM population and environment independently:

`w_m = lambda * std(c_g) / max(std(c_m), 1e-8)`

and use `c = c_g + w_m*c_m`. PyTorch's sample standard deviation is used,
matching the released CEM implementation's use of sample standard deviation
for candidate updates. Means need not be subtracted because they do not alter
candidate ranking within a population. The primary `lambda` is `0.07` for A1,
R1, D1, and F1. The common sensitivity grid is
`{0.005, 0.04, 0.07, 0.10}`; it is not used to redefine the primary result.

All models return a `(batch, candidate)` cost tensor. The wrapper asserts that
the shared predicted trajectory has `H+1` states and records raw goal cost,
raw verifier cost, adaptive weight, and timing for every CEM iteration.

## 6. Data separation and freshness

Offline scorer training may use the pre-existing training partition because
all methods are intended to reuse world-model training trajectories. Model and
hyperparameter decisions use only scorer-training validation data and the new
development starts below.

Evaluation has three non-overlapping namespaces:

1. **R0 reproduction:** the official Le-WM seed-42 sampling rule and 50 starts.
   Only B0 and A1 are used to check whether the local stack approximately
   reproduces the published Le-WM/ACID table. These outcomes are not used in
   the proposed-method confirmation test.
2. **D1 development:** 24 freshly sampled valid starts per task, generated by
   hash seed `2026081201`, excluding R0 and every recoverable legacy P2/P3/P4
   `(episode, start, goal-offset)` tuple. D1 draws from P2 episodes. It is
   inspectable and may expose implementation faults. Only predeclared
   sensitivity choices may be made.
3. **C1 confirmation:** 50 additional starts per task, generated by hash seed
   `2026081202` from P4 episodes under the same exclusions and never run until
   code, model checkpoints, primary weights, and analysis code are frozen and
   hashed.

Manifest generation sorts eligible tuples before seeded selection, records
source dataset SHA-256, and refuses duplicate or overlapping tuples.

## 7. Seeds and paired execution

Train A1, R1, D1, and F1 with seeds `6101`, `6102`, and `6103`. Confirmation
uses planner seeds `7101`, `7102`, and `7103`, paired one-to-one with the
corresponding trained scorer seed. B0 is rerun at all three planner seeds. Each
method therefore has 150 confirmation episodes per task and shares every
`(task, start, planner-seed)` unit with all other arms.

This paired design estimates practical end-to-end variability across both
training and CEM randomness without claiming to separately identify their
variance components. Offline validation is reported per training seed, never
only for the best seed.

## 8. Reproduction and implementation gates

Before D1 development:

- unit tests verify attention masking, tensor shapes, fixed noise, Euler sign,
  episode-boundary exclusion, action/latent standardization, and adaptive cost;
- the wrapper's B0 output matches the released model's `get_cost` to numerical
  tolerance on identical inputs;
- adding a zero verifier weight leaves CEM actions bitwise identical;
- a tiny overfit test makes each model fit a fixed synthetic batch;
- R0 B0 is within 10 percentage points of the published Le-WM result on each
  task, or the mismatch is investigated before efficacy testing;
- native A1 has finite validation loss and correct-action recovery better than
  a fixed action permutation.

If A1 cannot approximately reproduce the direction of ACID's reported gains,
we report it as a failed reimplementation and do not use it as evidence that
D1 beats ACID.

## 9. Diagnostics and negative controls

The study records more than binary success:

- verifier validation loss and per-dimension residuals;
- correct-versus-permuted-action identification on held-out real transitions;
- shuffled-action-label D1 and F1 models with identical data volume;
- action-ablated D1, with parameter count reported;
- candidate-cost variance and adaptive-weight distribution by CEM iteration;
- same-candidate Spearman correlation with realized rollout error/task
  distance on a fixed diagnostic candidate pool;
- oracle-best rank and selected candidate's realized distance;
- world-model predicted-versus-executed latent transition error;
- NaN/Inf, cost-collapse, and CEM elite-diversity rates.

Shuffled and action-ablated models are diagnostic controls, not extra headline
arms. They are never allowed to determine confirmation starts or primary
weights.

## 10. Compute, budget, and latency sensitivity

The primary comparison uses population 300, 30 CEM iterations, and 30 elites.
On the development manifest and then once on confirmation after the primary
analysis is locked, test populations `{30, 50, 150, 300}` with 10% elites and
30 iterations. The full-population weight sensitivity grid is
`{0.005, 0.04, 0.07, 0.10}`.

Latency uses CUDA events after 20 warm-up calls and at least 100 measured cost
calls on the same GPU. Report median, IQR, and p95 for world-model rollout,
verifier, total cost call, full CEM solve, and end-to-end episode. Also report
peak allocated VRAM and scorer parameter count. A method's accuracy is not
described as compute-saving unless matched-success comparisons support it.

## 11. Statistical analysis and claim gates

The primary endpoint is paired closed-loop success. Report task-level rates
and paired differences with two-sided 95% cluster-bootstrap confidence
intervals, resampling start identities and keeping their three paired seed
runs together. Also report an exact paired test as a sensitivity analysis.
Never pool raw episodes across tasks without task-stratified resampling and
per-task results beside it.

The diffusion-as-ACID-alternative claim requires all of the following on C1:

1. **Useful:** D1 minus B0 has a task-stratified pooled 95% CI whose lower
   bound is above zero.
2. **ACID non-inferiority:** D1 minus A1 has a one-sided 95% lower bound above
   `-0.05` pooled and above `-0.10` on every task.
3. **Diffusion-specific:** D1 minus F1 has a pooled two-sided 95% CI wholly
   above zero. Held-out correct-action identification must also beat both F1
   and shuffled-action D1.
4. **Breadth:** D1 may not lose to B0 by more than 10 percentage points on any
   individual task, and its point estimate must exceed B0 on at least two of
   the three tasks.
5. **Mechanism:** D1 cost must positively rank realized rollout error or task
   distance in the same-candidate audit, and true action conditioning must
   outperform the shuffled/action-ablated controls.

If gates 1, 2, 4, and 5 pass but gate 3 fails, the conclusion is that learned
transition verification is competitive with ACID; it is **not** evidence that
diffusion is the reason. If non-inferiority passes but superiority over B0 does
not, D1 may be described as comparable, not as a repair. PLDM is required
before saying the result generalizes across world-model families.

## 12. Amendment rule and audit trail

Before D1 is run, implementation errata that make code disagree with this
document may be corrected and logged with old/new hashes. After any D1 outcome
is inspected, method improvements become explicitly exploratory v2 work and
cannot alter C1. After C1 begins, only outcome-independent execution repairs
are allowed; affected runs are invalidated and rerun for every arm in the
paired block. No result file is overwritten.

Every run records git/source hashes, input and checkpoint SHA-256 values,
resolved configuration, Slurm job ID, node/GPU, library versions, seeds,
timestamps, and output checksums.
