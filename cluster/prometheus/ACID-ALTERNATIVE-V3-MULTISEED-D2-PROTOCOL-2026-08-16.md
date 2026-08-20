# ACID-alternative v3: multi-seed fresh-D2 protocol

Date frozen: 2026-08-16 (Asia/Nicosia)  
Role: prospective post-v2 development test on previously unused data  
Protected material: C1 and I1 remain sealed and may not be read, scored, or executed

## 1. Question and claim boundary

This study tests whether the two fixed outputs of the residual-diffusion model
that survived the v2 pilot generalize across training seeds and fresh Le-WM
evaluation data:

1. **RDX**: conditional clean-residual reconstruction error, used as a
   candidate-failure ranker;
2. **AE**: the conditional-versus-unconditional log error ratio, used as an
   action-specific planning signal.

The study compares both outputs with original CEM, a capacity-matched
deterministic forward verifier, shuffled-action residual-diffusion controls,
and a newly audited reconstruction of ACID's published method. The two
diffusion outputs are separate frozen arms. They may not be selected between,
averaged, rescaled, sign-flipped, or combined after D2 outcomes are observed.

The strongest conclusion available from this study is:

> On the three released Le-WM control tasks, a fixed residual-diffusion
> verifier generalized across scorer seeds and fresh evaluation starts, and
> its predeclared action-evidence planning cost was non-inferior to a
> transparent published-equation ACID reconstruction.

This is not an official-code replication of ACID. The ACID project page still
listed code as forthcoming at the implementation audit. If the gates below do
not pass, the corresponding sentence is not allowed. PLDM or another backbone
is still required before claiming generality across world-model families.

## 2. Prior evidence and immutable endpoint choice

The architectural choices were made using P1 validation and the already
observed 24-start D1 development set. The v2 seed-6101 result is not fresh
evidence. It fixed the following choices before D2:

- RDX guidance: `g = 1.0`;
- AE definition: `log(mean_conditional_MSE + 1e-12) -
  log(mean_unconditional_MSE + 1e-12)`;
- noise levels: `{0.25, 1.0, 4.0}`;
- deterministic noise draws: 8 per level;
- horizon reduction: mean over five Le-WM transitions;
- latent reduction: mean squared error over latent dimensions;
- diffusion planning weight: adaptive spread weighting with `lambda = 0.005`;
- primary planning arm: AE;
- primary candidate-failure ranking arm: RDX.

The model remains the v2 width-384, three-block residual MLP trained to recover
the standardized clean transition residual with classifier-free action
conditioning and the fixed action-contrastive auxiliary objective. No model,
loss, sigma, guidance, margin, dropout, width, depth, checkpoint rule, or score
transformation is tunable in this protocol.

## 3. Scorer seeds and controls

Use scorer seeds `6101`, `6102`, and `6103` for every learned comparator.

- The already frozen v2 seed-6101 true and shuffled residual-diffusion
  checkpoints are retained.
- Train seeds 6102 and 6103 with the byte-audited v2 algorithm and unchanged
  hyperparameters. The only permitted source-level adaptation is expanding
  the seed guard and binding the trainer to this protocol hash.
- Use the three already completed native ACID checkpoints from the v1 study.
- Use the three already completed capacity-matched deterministic-forward
  checkpoints from the v1 study.

Every residual-diffusion seed must pass the original P1 mechanism checks in
each task: true-action pairwise accuracy at least 0.70, sigma-4 accuracy at
least 0.75, positive wrong-minus-true margin, and at least 0.10 accuracy
advantage over its matched shuffled-label checkpoint. A failure is reported;
the seed or task may not be dropped.

## 4. Audited ACID reconstruction

The comparator implements the live equations and hyperparameters in
arXiv:2607.02403:

- task-specific inverse dynamics model;
- four transformer layers, three heads, width 192;
- two latent prefix tokens and one noisy-action/time suffix token;
- prefix-to-prefix and suffix-to-all attention mask;
- straight flow path `x_tau = tau*epsilon + (1-tau)*action`;
- target velocity `epsilon - action`;
- `tau ~ Beta(1.5, 1.0)`;
- action standardization on P1 training data and de-standardization at test;
- 200,000 AdamW steps, batch 256, peak LR `1e-4`, 1,000-step warmup and
  cosine decay, weight decay `1e-4`, gradient clip 1, bf16;
- one Euler integration step;
- per-transition residual averaged across all five predicted Le-WM steps;
- adaptive cost weight `lambda * std(c_goal)/std(c_acid)` with published
  Le-WM `lambda = 0.07`.

Le-WM defines one learned transition using a five-primitive-action block; the
IDM therefore predicts that 10-dimensional block for PushT/Reacher or
25-dimensional block for Cube. This is the native action variable consumed by
the frozen Le-WM checkpoint, not a single-macro approximation.

The paper does not publish normalization placement, MLP expansion, exact time
embedding, token positional encoding, or inference-noise reuse. The retained
checkpoints declare pre-LayerNorm, GELU, MLP ratio 4, standard sinusoidal time
embedding, learned three-token positions, and biased linear projections.
These remain disclosed reconstruction choices.

The v1 evaluator reused one Gaussian noise vector across every candidate.
For this audit, the primary ACID comparator instead follows the paper's literal
`x_1 ~ N(0,I)` statement: one independently generated Gaussian sample is used
for each candidate and horizon transition. Random values are deterministic
under a recorded SHA-256-derived stream keyed by task, scorer seed, planner
seed, and cost-call index. Only one sample and one Euler step are used; no
Monte-Carlo averaging is introduced. This change affects inference only and
is fixed before D2.

## 5. Fresh D2 isolation

D2 contains exactly 50 starts per task from partition P3 of the immutable
episode partition. Selection seed is `2026081603`.

Isolation rules:

- select only P3 episodes;
- use at most one start per episode;
- exclude every episode appearing in the R0 manifest;
- require a valid 25-step goal window;
- rank eligible `(episode,start)` tuples by ascending
  `SHA256(task + NUL + seed + NUL + episode + NUL + start)`;
- record the dataset, partition, R0, and output hashes before any D2 outcome;
- refuse duplicate episodes, duplicate starts, or a partition other than P3.

This gives episode-level separation from P1 scorer training, D1/P2, and the
P4 namespace used for sealed C1/I1 without opening either protected manifest.
The manifest generator must not receive a C1 or I1 path.

All tasks retain the published Le-WM goal offset of 25 primitive steps,
50-step evaluation budget, five model steps, five primitive actions per model
step, 300 CEM candidates, 30 CEM iterations, and 30 elites.

## 6. Stage A: same-candidate physical audit

For each task, original CEM with planner seed `8201` produces its final
300-candidate population on each of the 50 starts. The frozen world model rolls
out each pool once. Every candidate action sequence is then executed in the
real simulator for 25 primitive steps. All scorers consume the identical
predicted trajectories and are judged against the identical physical outcomes.

For each scorer seed and pool, report:

- Spearman correlation between raw cost and physically realized standardized
  latent rollout RMSE;
- selected candidate's standardized RMSE, task distance where available, and
  environment success;
- true-minus-shuffled contrasts for RDX and AE;
- RDX/AE contrasts with deterministic forward and ACID;
- scorer parameter count and scoring latency.

Candidate selection uses the lowest `c_goal + w*c_verifier` candidate in the
captured pool. RDX, AE, forward, and shuffled controls use `lambda = 0.005`;
ACID uses `lambda = 0.07`. These are fixed method-level settings, not a D2
grid. B0 uses goal cost alone.

Uncertainty uses 100,000 task-stratified cluster-bootstrap repetitions with
seed `2026081604`. Starts are resampled within task and all three paired scorer
seeds for a start remain together. Equal-task estimates weight PushT, Reacher,
and Cube equally. Report per-task results beside every pooled result.

Stage A permits Stage B only if artifacts are finite/noncollapsed and:

1. RDX rank correlation is positive in all three tasks and its equal-task
   two-sided 95% lower bound is above zero;
2. RDX minus shuffled RDX has an equal-task lower bound above zero;
3. RDX is non-inferior to deterministic forward and ACID for ranking, with
   one-sided 95% lower bounds above `-0.03`;
4. AE minus shuffled AE has an equal-task lower bound above zero and no
   task-level point estimate below zero;
5. AE candidate selection is non-inferior to ACID: success lower bound above
   `-0.05` and standardized-RMSE upper bound below `+0.02`.

All five gates are reported even if an earlier gate fails. A failure stops
automatic Stage B; it cannot be repaired with another D2 transformation.

## 7. Stage B: paired closed-loop evaluation

If Stage A passes, run the following independently optimized CEM arms on the
same 50 D2 starts:

- B0 original CEM;
- audited ACID;
- deterministic forward;
- RDX;
- AE (primary diffusion planning arm);
- shuffled-label AE control.

Pair scorer seeds `6101/6102/6103` with planner seeds `8301/8302/8303`.
B0 is rerun at all three planner seeds. All arms use the same world-model
checkpoint, start, goal, environment, CEM innovations, population, iteration
count, and elites for a paired `(task,start,planner-seed)` unit. Candidate
populations may diverge after the first CEM update, as required for an actual
planning comparison.

Primary endpoint: paired closed-loop success of AE. Report paired differences
using a task-stratified start-cluster bootstrap (100,000 repetitions, seed
`2026081605`) and an exact paired sensitivity test. The alternative-to-ACID
planning claim requires:

1. AE minus ACID one-sided 95% lower bound above `-0.05` equal-task and above
   `-0.10` in every task;
2. AE minus B0 two-sided 95% lower bound above zero equal-task;
3. AE minus shuffled AE two-sided 95% lower bound above zero equal-task;
4. AE is not more than 0.10 below B0 in any task and has a higher point
   estimate than B0 in at least two tasks;
5. AE is non-inferior to forward with a one-sided equal-task lower bound above
   `-0.05`.

RDX closed-loop outcomes are secondary and cannot replace AE if AE fails.

## 8. Stop, amendment, and reporting rules

- D2 manifests, code, endpoint definitions, seeds, checkpoints, lambdas,
  bootstrap streams, and gates are hashed before candidate capture.
- Outcome-independent implementation errors may be corrected only with a
  dated amendment, new source hash, invalidation of affected artifacts, and
  matched reruns for every affected arm.
- No method improvement, new seed, task deletion, lambda search, endpoint
  search, alternative sign, score mixture, or post-hoc subgroup can alter this
  study after a D2 outcome is read.
- Failed runs and failed gates remain in the audit.
- C1 and I1 remain untouched regardless of the D2 result.
- Every artifact records its input hashes, source manifest, checkpoint hashes,
  Slurm IDs, GPU, software versions, seeds, and output hashes.

