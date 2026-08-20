# Thesis Master: Benchmark, Experimental Protocol, and Verified Paper Map

> **Historical status (20 August 2026):** this is the consolidated pre-data
> protocol that governed the original Hi-LeWM post-hoc scorer study. It remains
> part of the audit trail but is no longer the active final-method protocol.
> The project later pivoted to pure goal-conditioned velocity-diffusion action
> proposals; see `README.md` and the frozen E11 protocol/result under
> `cluster/prometheus/` for the current method and claim.

**Project:** Feasibility-aware subgoal selection for hierarchical latent planning  
**Status:** final pre-data master document  
**Date:** 28 July 2026  
**Literature search cutoff:** 28 July 2026

This is the single active specification for implementation, evaluation, and thesis positioning. It consolidates the final protocol in `protocol-spec-v3-2-1-2026-07-28.md` with the still-valid literature map from `benchmark-paper-map-v3-1-2026-07-28.md`. The older files are historical audit records and do not govern new work.

The consolidation is deliberately asymmetric:

- The experimental protocol below comes from v3.2.1 and remains substantively unchanged.
- No experimental rule is inherited from v3.1.
- A paper is carried over only where its title, metadata, and stated role were checked against a primary paper record or the paper itself.
- Results from other papers are context, not evidence for this thesis. Local empirical claims begin only after the frozen protocol is run.

## 1. Research question and scope

The study asks whether post-hoc feasibility signals improve selection of the first committed subgoal in a frozen hierarchical LeWorldModel planner.

It does **not** claim that diffusion replaces ACID as a general method. ACID and the proposed diffusion score measure different failure modes:

- M1 asks whether a proposed transition is consistent with the macro-action used to generate it.
- M2 asks whether the proposed transition resembles supported transitions under a conditional diffusion denoiser.
- M3 estimates temporal effort or reachability from logged trajectories.

The contribution is their controlled comparison at the same subgoal interface, with the predictive models, nominal planning budget, proposal mechanism, and initialization held fixed. B1 is intentionally different: it changes the proposal distribution and tests the published empirical-macro restriction.

### 1.1 Experimental arms

| ID | Condition | Intervention | Status |
|---|---|---|---|
| B0 | Naive Hi-LeWM | Unconstrained high-level CEM | Mandatory base reproduction |
| B1 | Hi-LeWM with empirical-macro CEM | Restricts the proposal distribution using empirical macro-actions | Mandatory published baseline |
| M1 | B0 + macro cycle-consistency score | Adds a single-macro inverse-dynamics residual | Mandatory learned score |
| M2 | B0 + conditional diffusion denoising-error score | Adds an action-free transition-support score | Mandatory proposed score |
| M3 | B0 + temporal reachability score | Adds a horizon-matched pairwise temporal head | Mandatory learned score |
| G0a | Macro-action KNN isolation | Training-free pool diagnostic | Offline first; gate before closed loop |
| G0b | Subgoal-latent KNN isolation | Training-free negative-control geometry | Offline first; gate before closed loop |

B0 and M1-M3 differ only by the added candidate score. B1 is a proposal-support baseline, not a fourth scoring signal. B1 plus the best score is post-core work.

## 2. Frozen experimental protocol

### 2.1 Freeze and amendment rule

Every numeric value below is either frozen now or assigned a frozen selection procedure that binds it on the development partitions before any locked run.

- Corrections of identified factual errors or internal contradictions enter the changelog as dated pre-data errata.
- Improvement proposals that do not identify an error are deferred until development data exists.
- After development runs begin, every change records its date, the run evidence motivating it, and the affected sections.
- P3 and P4 data must never be used to improve models, calibration, hyperparameters, thresholds, or sample sizes.

### 2.2 Notation and score placement

Let the frozen encoder be `e`, the low-level predictor be `f_low`, and the high-level predictor be `f_hi(z_t, m) = z_hat_(t+Delta)`. The macro encoder `E_M` maps a primitive action chunk of length `Delta` to macro-action `m`. A candidate is `c = (x_t, m, z_sg)`, where `z_sg = f_hi(e(g(x_t)), m)`. `P_low` is the frozen budgeted CEM/MPPI configuration inherited from the base system.

**Budget relation:** `H_low = Delta` primitive environment steps. Stratum-1 positive pairs are sampled at exactly separation `Delta`.

**Score placement:** each feasibility score is applied to the first high-level transition of a candidate plan—the transition that the receding-horizon controller will commit. Mean score over all high-level transitions is a sensitivity analysis only.

### 2.3 Ground-truth target: budgeted low-level attainability

The target is whether the frozen low-level planner, under its standard budget, attains the candidate subgoal. It is controller-relative and encoder-relative. Planner failure is not evidence of physical impossibility.

#### Repeated execution and label

Each labeled candidate is executed `K = 5` times. Reset the simulator to `x_t`, run `P_low` toward `z_sg` for `H_low` steps, and use planner seeds `{s_1, ..., s_5}` fixed once and shared across candidates, conditions, and scorer evaluations.

- Primary label: `y = 1` when at least 3 of 5 runs attain the subgoal.
- Secondary target: empirical attainment rate `p_hat in {0, .2, .4, .6, .8, 1.0}`.
- No candidate is excluded as ambiguous.
- Sensitivity: recompute AUROC using 2/5 and 4/5 thresholds.

#### Attainment criterion by stratum

- **Real-frame candidates, strata 1 and 2:** use physical state error and the benchmark-defined success tolerances of the base evaluation suites where available. PushT uses block position and angle; an agent-pose-included variant is a sensitivity analysis. Cube follows the position-and-yaw-plus-contact pattern of its benchmark events. Where no benchmark tolerance exists, set a physically interpretable threshold from object and arena scale before any P2 run and perform a P2 sensitivity analysis. Record latent distance as a diagnostic.
- **Imagined candidates, stratum 3:** use latent distance under the frozen encoder at tolerance `delta`.
- **Tolerance selection:** choose `delta` from 10 log-spaced values between 0.05 and 1.0, in units of per-dimension latent standard deviation on P1. Select the value maximizing Cohen's kappa between latent and physical criteria on P2 real-frame candidates; break ties toward the smaller value. Re-verify agreement once on locked P3 real-frame candidates and report it with every stratum-3 result.

#### Candidate strata

1. Same-trajectory latents at separation `Delta`, expected to be mostly positive.
2. Cross-trajectory latents, expected to be mixed.
3. High-level-planner and imagined-rollout proposals, the deployment distribution and the only stratum used for promotion.

Report every metric per stratum. Never pool strata in a headline number.

#### Executed categories

- **Reached under standard budget:** at least 3/5 with `P_low`.
- **Reached only under extended budget:** fails the standard budget but reaches at least 3/5 with 4x samples and 2x horizon, using the same `K` and seeds.
- **Not reached under tested budgets.**

Do not call the latter categories “unreachable,” “invalid,” or “off-manifold.”

### 2.4 Exact score definitions

All learned scores consume `(z_t, m, z_sg)`, emit a scalar whose larger value means lower attainability, train only on P1, and pass through the common calibration layer.

#### M1: macro cycle consistency

Train `g_phi(z_t, z_(t+Delta)) -> m_hat` on real pairs `Delta` steps apart, with `m = E_M(a_(t:t+Delta))` from the frozen macro encoder.

`s_M1(c) = ||m - g_phi(z_t, z_sg)||_2^2`

This is the **single-macro-residual adaptation of ACID**. ACID's original per-primitive-step residual is only a sensitivity variant if the base system exposes macro-to-primitive decoding.

#### M2: conditional diffusion denoising error

Train `epsilon_theta(z_tilde, sigma, z_t)` on real pairs `(z_t, z_(t+Delta))`, noising only the target:

`z_tilde = z_(t+Delta) + sigma * epsilon`, where `epsilon ~ N(0, I)`.

The denoiser conditions on clean `z_t` and does not condition on `m`. The deliberate separation is: M1 measures action consistency, M2 measures action-free transition support, and M3 measures temporal effort.

`s_M2(c) = (1/N) * sum_i ||epsilon_i - epsilon_theta(z_sg + sigma_star * epsilon_i, sigma_star, z_t)||_2^2`

Use `N = 8` fixed-seed noise draws. Select `sigma_star` from `{0.1, 0.25, 0.5, 0.75, 1.0}`, in P1 latent-standard-deviation units, by P2 stratum-3 AUROC and then freeze it.

**Relationship to DOSER:** DOSER's canonical score is clean-sample reconstruction error. At a fixed noise level, clean reconstruction error and epsilon-prediction error differ by the noise-scale factor and therefore rank candidates identically; they diverge when averaging across noise levels. Describe M2 as an **epsilon-prediction variant inspired by DOSER**, never as a direct transplant. A DOSER-faithful sensitivity variant averages clean-latent reconstruction error over noise levels from the same grid. The primary method is a single-pass score, not iterative diffusion sampling.

#### M3: temporal reachability head

Train `r_psi(z, z_prime) -> t_hat` to predict within-episode temporal separation using 100,000 training pairs, 10,000 validation pairs, separations 1-40, target scale 40, and P1 episodes only.

`s_M3(c) = r_psi(z_t, z_sg)`

Conversion to failure probability within `H_low` occurs only through calibration. A binary `1[t_true <= H_low]` head is a sensitivity variant.

#### G0 diagnostics

Use KNN isolation with `k = 3` and robust per-coordinate standardization:

- G0a over macro-action vectors within a candidate pool.
- G0b over subgoal latents within the same pool.

The predeclared prediction is that G0a outperforms G0b on stratum 3. Neither enters closed-loop evaluation unless it passes the same promotion gate.

### 2.5 Training records

For all learned scorers:

- AdamW, learning rate `3e-4`, cosine decay, batch size 256.
- Early stopping on P1 validation loss, patience 10.
- Three independent training seeds.
- P1 episode lists and SHA-256 hashes committed before any P3 or P4 run.
- Deterministic episode split by seeded hash of episode identifiers, seed `20260728`.

Architecture-specific rules:

- M1: 3-layer MLP; width chosen from `{256, 512}` by P2 stratum-3 AUROC.
- M2: MLP denoiser; width chosen from `{512, 1024}` by the same metric.
- M3: ASAR-supplement pairwise MLP architecture.
- M1/M2 use all available P1 pairs at separation `Delta`; record realized pair counts with partition hashes.

### 2.6 Data partitions

| Partition | Role | Permitted influence |
|---|---|---|
| P1 | Scorer training and validation episodes | Fit model parameters |
| P2 | Calibration and hyperparameter development, including executed pools | Choose declared hyperparameters, tolerances, query count, and weights |
| P3 | Locked offline candidate audit | Promotion through the frozen gate only |
| P4 | Locked closed-loop confirmation | No choices |

Partitions are episode-disjoint pairwise. Record hashed episode manifests and all exclusions. P2 numbers never appear as results.

### 2.7 Calibration and score combination

- Primary calibration: Platt scaling from raw score to attainment-failure probability on P2 executed candidates.
- Sensitivity calibration: isotonic regression.
- Calibration metrics: Brier score primary, ECE secondary.
- Planner cost: `goal term + w * calibrated failure probability`.
- Select one `w` per arm from `{0.25, 0.5, 1, 2, 4}` by P2 closed-loop development success, then freeze it.
- M1 sensitivity: ACID's native adaptive scale-invariant weighting.

### 2.8 Nulls, comparator, and promotion gate

Frozen nulls:

- M1: permute macro labels across P1 pairs.
- M2: mismatch `z_t` and `z_(t+Delta)` across different P1 episodes.
- M3: permute temporal labels.

M2 also requires a capacity-matched plain-autoencoder reconstruction control. It governs interpretation, not promotion. If M2 passes the gate but does not beat the autoencoder, report it as a reconstruction-error signal; a diffusion-specific claim requires beating the autoencoder.

An arm is promoted only if all conditions hold on P3 stratum 3 under the primary label:

1. AUROC is at least 0.70.
2. The paired 95% bootstrap interval for AUROC improvement over that method's null excludes zero, using 10,000 resamples clustered by evaluation seed.
3. AUPRC is reported with the stratum's positive-class prevalence and as AUPRC minus prevalence.

Failed arms remain in the offline results and are excluded from closed loop. That exclusion is a result.

### 2.9 Statistical units, sample sizes, and endpoint

- **P3 exact size:** 24 pools per stratum per environment, 64 candidates per pool, 5 executions per candidate.
- **P4 exact size:** 40 evaluation seeds per environment; per-seed query count is fixed on P2 and shared across conditions.
- **Primary endpoint:** paired difference in PushT closed-loop success at the longest Hi-LeWM goal offset—reported as 75 and to be confirmed from the artifact before P2—between M2 and B0 over exactly 40 seeds. Use a 95% seed-clustered bootstrap with 10,000 resamples.
- **Secondary family:** M1 vs B0, M3 vs B0, B1 vs B0, promoted G0, compositions, and the second environment. Apply Holm correction at alpha 0.05 within this family.
- **Nesting:** executions within candidate, candidates within query, queries within seed. Cluster all intervals at seed level; never treat planning steps or repeated executions as independent.
- **Scorer replication:** calibrate each of three training seeds separately, then average their calibrated failure probabilities as the fixed primary ensemble. Individual-seed results are sensitivities.
- **Checkpoint replication:** use the Hi-LeWM artifact checkpoint for primary results and replicate the primary endpoint on one independently trained checkpoint. Other results may remain conditional on the artifact checkpoint.

### 2.10 Matching rule

Offline comparisons use identical fixed candidate pools. Closed-loop comparisons share initial states, goals, initial candidate draws, and random-number streams. Later adaptive CEM proposals may diverge because different scores select different elites. Never claim fully matched proposals beyond initialization.

### 2.11 Environments and substitution

- PushT is mandatory and primary.
- Cube is the planned second environment.
- Replace Cube with TwoRoom if, at the longest offset on development runs, B0 success is above 85% or below 5%, or B1 improves over B0 by less than 5 absolute points.
- Record the trigger evaluation and decision before any P4 run.
- PLDM Diverse Maze is a cross-backbone extension only.

## 3. Complete reporting set

The primary endpoint remains the single confirmatory claim in Section 2.9. The following are secondary or diagnostic reports and do not create additional primary hypotheses:

1. Closed-loop success by environment, goal offset, and planning budget.
2. Subgoal attainment rate.
3. Proportions in the three executed categories.
4. AUROC and AUPRC for budgeted low-level failure, per stratum.
5. Brier score and ECE.
6. Feasible-in-top-k and feasible-winner rate.
7. Planning latency and per-candidate scorer latency.
8. Peak VRAM, host RAM, GPU model, software stack, and requested scheduler resources.
9. Success and feasible-winner rate versus candidate-pool size.
10. Equal-candidate comparisons for algorithmic effect and equal-wall-clock comparisons for practical effect whenever scorer costs differ materially.
11. Per-environment results; any pooled or macro-averaged result is secondary.

## 4. Execution order

1. Run the official Hi-LeWM artifact and reproduce B0 and B1 on PushT.
2. If the artifact cannot produce a baseline on the available GPU within one week, port empirical-macro CEM as a proposal restriction into the trusted stable-worldmodel harness and record the deviation.
3. Run P1/P2 only: build the candidate-execution audit, validate label distributions, fit scorers and nulls, set tolerances, choose allowed hyperparameters, and fix the per-seed P4 query count.
4. Commit the frozen configuration, environment identifiers, episode lists, exclusion lists, random seeds, and hashes.
5. Run locked P3 once and apply the gate without tuning.
6. Run P4 for promoted arms only.
7. Repeat the required second environment under the substitution rule.
8. Only after the core study: B1 plus best score, ASAR-style compositions, PRISM, FF-JEPA, or a cross-backbone extension.

## 5. Compute plan

The institutional Prometheus cluster is sufficient for this study. Its [hardware documentation](https://prometheus-docs.cyens.org.cy/docs/hardware/) lists 512 GB host RAM per GPU node, eight nodes with eight 24 GB A5000 GPUs each, and `gpu09` with four 48 GB GPUs described as “NVIDIA RTX A6000 Ada Generation.” The listed core count and throughput correspond to RTX 6000 Ada Generation, so record the exact identity from `nvidia-smi` instead of repeating the ambiguous website name in the paper.

Recommended allocation:

- Use one `gpu09` GPU for primary and timed comparisons. ACID reports its latency experiment on one RTX 6000 Ada, making this the closest available hardware match.
- Request 8-16 CPU cores and 64-128 GB host RAM initially; increase only if measured data-loader or simulator use warrants it. The node's 512 GB capacity is ample.
- Use separate jobs or job arrays for training seeds, candidate-pool generation, and environment seeds. Do not combine GPUs into a single timed planning run unless the method itself requires it.
- Use A5000 nodes for non-timed scorer training, diagnostics, plots, or independent seeds when 24 GB VRAM suffices.
- Store datasets and results on Lustre, stage high-I/O temporary data on local NVMe where allowed, and use Apptainer/Singularity with a pinned CUDA/PyTorch environment.
- Before the first result, record `nvidia-smi`, driver, CUDA runtime, PyTorch version, container digest, SLURM request, CPU model, host RAM, and wall-clock measurement method.

RunPod or another dedicated cloud VM is an acceptable fallback. Cloud use does not reduce publishability; reproducibility depends on the recorded machine image, exact GPU, software stack, seeds, manifests, and fair timing protocol. Do not mix hardware within a latency table unless results are explicitly separated by hardware.

## 6. Novelty and claim boundary

The final claim is:

> We conduct a controlled comparison of three post-hoc candidate-scoring signals, macro inverse-dynamics consistency, diffusion denoising error, and horizon-matched learned reachability, at the subgoal interface of a frozen hierarchical LeWorldModel planner, while holding its proposal mechanism and initialization, predictive world models, and nominal planning budget fixed.

Do not claim any of the following:

- first feasibility-aware hierarchical planner;
- first decision-time constraint on high-level subgoal search;
- first use of support information in hierarchical LeWM planning;
- first use of diffusion error for OOD or support estimation;
- complete matching of adaptive closed-loop proposals;
- physical impossibility from failure under a finite planner budget.

The defensible diffusion statement is narrower: **no public prior use of this exact placement—a diffusion denoising-error cost for decision-time subgoal selection in a frozen latent world-model planner—was found by the 28 July 2026 search cutoff.** This is a search result, not a universal priority claim. Re-run the search immediately before the defense and submission.

## 7. Papers that determine the benchmark

These papers directly determine the implementation, the three scores, or the closest matched comparison.

| Paper | Verified contribution relevant here | Role in this thesis |
|---|---|---|
| [Mind the Gap: Promises and Pitfalls of Hierarchical Planning in LeWorldModel](https://arxiv.org/abs/2607.12547), Caselli et al., submitted 14 Jul 2026 | Freezes low-level LeWM, adds hierarchical planning, identifies high-level search mismatch, and introduces empirical-macro CEM on PushT and Cube | Implementation base for B0; source of B1 |
| [Hierarchical Planning with Latent World Models](https://arxiv.org/abs/2604.03208), Wancong Zhang et al., submitted 3 Apr 2026 | Multi-temporal-scale latent world models use long-horizon predictions as subgoals for a short-horizon planner | Foundational architecture and motivation; not a matched score baseline |
| [ACID: Action Consistency via Inverse Dynamics for Planning with World Models](https://arxiv.org/abs/2607.02403), Seo, Kim, and Kwak, submitted 2 Jul 2026 | Adds a per-step inverse-dynamics cycle-consistency residual to decision-time planning with adaptive scaling | Source of M1; compare mechanism and published numbers, not claim equivalence |
| [Beyond Euclidean Proximity: Repairing Latent World Models with Horizon-Matched Trajectory Reachability Metrics](https://arxiv.org/abs/2605.22164), Li, Wang, and Liu, submitted 21 May 2026 | Trains a post-hoc pairwise temporal-separation head for terminal ranking while freezing the world-model planning stack | Source of M3 and the closest score-only precedent |
| [Predictive but Not Plannable: RC-aux for Latent World Models](https://arxiv.org/abs/2605.07278), Wenyuan Li et al., submitted 8 May 2026 | Adds multi-horizon, budget-conditioned reachability supervision during world-model training | Mandatory M3-related citation; not a matched arm because it changes training |
| [Beyond Penalization: Diffusion-based Out-of-Distribution Detection and Selective Regularization in Offline Reinforcement Learning](https://arxiv.org/abs/2605.08202), Wang et al., submitted 6 May 2026 | Uses single-step diffusion reconstruction errors as support signals in offline RL | Closest scoring primitive for M2; source for the DOSER-faithful sensitivity analysis |
| [LeWorldModel: Stable End-to-End Joint-Embedding Predictive Architecture from Pixels](https://arxiv.org/abs/2603.19312), Maes et al., submitted 13 Mar 2026 | Compact end-to-end JEPA world model with latent CEM planning | Underlying model family and checkpoint ecosystem |
| [stable-worldmodel: A Platform for Reproducible World Modeling Research and Evaluation](https://arxiv.org/abs/2605.21800), Maes et al., submitted 20 May 2026 | Standardized open-source world-model data, training, environments, and planning solvers | Trusted harness and contingency target |

### 7.1 Closest external methods: cite and compare, do not reproduce in the core

| Paper | What it changes | Why it is not one of M1-M3 |
|---|---|---|
| [SAGE: Subgoal-Conditioned Action Generation for Latent World Model Planning](https://arxiv.org/abs/2607.17973), Cheng, Zhang, and Wang, submitted 20 Jul 2026 | Generates duration-conditioned reachable subgoals and conditions action proposals on them; the frozen world model evaluates/refines candidates | Proposal generation rather than post-hoc scoring under the fixed B0 proposal mechanism |
| [Action from Adjacent Set in Physical Space Outperforms the Best Prediction in World Models](https://arxiv.org/abs/2607.23602), Liangyu Li, Qingwen Liu, and Mingqing Liu, submitted 26 Jul 2026 | Uses KNN isolation over early action prefixes and adjacent-set reconstruction; also provides candidate-audit and TRM-control practices | Source of G0 and protocol diagnostics; optional composition after the core study |
| [PRISM: PRior-guided Imagination Sampling in world Models](https://arxiv.org/abs/2606.07974), Wang et al., submitted 6 Jun 2026 | Fits a state-conditioned action prior and fuses it into the planning proposal distribution | Optional proposal-quality baseline, behind B1 in priority |
| [FF-JEPA: Long-Horizon Planning in World Models with Latent Planners](https://arxiv.org/abs/2606.09311), Sergi Masip et al., submitted 8 Jun 2026 | Learned latent planners, including diffusion variants, generate intermediate targets | Subgoal generator, not a feasibility scorer |

## 8. Related work to cite without core reproduction

### 8.1 World-model and planning ecosystem

- [World Action Verifier: Self-Improving World Models via Forward-Inverse Asymmetry](https://arxiv.org/abs/2604.01985), 2 Apr 2026: training-time verification and self-improvement; not the same as a decision-time subgoal cost.
- [Unifying Object-Centric World Models and Diffusion Policy: A Hierarchical Framework for Multi-Stage Robotic Tasks](https://arxiv.org/abs/2606.08775), 7 Jun 2026: changes the hierarchical model and uses a diffusion-policy low level.
- [Beyond the Next Step: Variable-Length Latent World Models for Long-Horizon Planning](https://arxiv.org/abs/2606.21775), 19 Jun 2026: changes temporal world-model training.
- [DINO-WM: World Models on Pre-trained Visual Features enable Zero-shot Planning](https://arxiv.org/abs/2411.04983), 7 Nov 2024: possible cross-backbone context.
- [DWM: Separating World Effects from Actions in Latent World Models](https://arxiv.org/abs/2607.18715), 21 Jul 2026: a world-model training intervention, not a post-hoc score.
- [Fast LeWorldModel](https://arxiv.org/abs/2606.26217), 24 Jun 2026: planning-efficiency context.
- [Latent Geometry Beyond Search: Amortizing Planning in World Models](https://arxiv.org/abs/2605.08732), 9 May 2026: amortizes planning with a goal-conditioned inverse dynamics model.
- [ATM: Action-Consistency Transfer Matrix for Diagnosing and Improving Latent World Models](https://arxiv.org/abs/2606.09028), 8 Jun 2026: action-consistency diagnostics.
- [Conformal Orbit-Valid Trust Horizons for Equivariant World Models](https://arxiv.org/abs/2606.24946), 23 Jun 2026: adjacent trust-horizon work, not evidence for successful subgoal scoring here.
- [A Definition and Roadmap for World Models](https://arxiv.org/abs/2607.06401), 7 Jul 2026: broad framing for feasibility checks and correction.

### 8.2 Diffusion and support-estimation lineage

- [AnoDDPM: Anomaly Detection With Denoising Diffusion Probabilistic Models Using Simplex Noise](https://openaccess.thecvf.com/content/CVPR2022W/NTIRE/html/Wyatt_AnoDDPM_Anomaly_Detection_With_Denoising_Diffusion_Probabilistic_Models_Using_Simplex_CVPRW_2022_paper.html), Wyatt et al., CVPR Workshops 2022.
- [Denoising diffusion models for out-of-distribution detection](https://arxiv.org/abs/2211.07740), Graham et al., submitted 14 Nov 2022.
- [Your Diffusion Model is Secretly a Zero-Shot Classifier](https://arxiv.org/abs/2303.16203), Li et al., submitted 28 Mar 2023.
- [Subgoal Diffuser: Coarse-to-fine Subgoal Generation to Guide Model Predictive Control for Robot Manipulation](https://arxiv.org/abs/2403.13085), Huang et al., submitted 19 Mar 2024. It generates subgoals and uses a learned reachability estimate; it does not apply the proposed M2 score at the frozen latent-world-model interface.
- DOSER, listed in Section 7, is the closest direct precedent for the denoising-error scoring primitive.

The diffusion mechanism is established prior art. The thesis claim concerns its placement and controlled evaluation, not invention of denoising-error support estimation.

### 8.3 Hierarchical reachability lineage

- [Generating Adjacency-Constrained Subgoals in Hierarchical Reinforcement Learning](https://arxiv.org/abs/2006.11485) (HRAC), 2020.
- [Landmark-Guided Subgoal Generation in Hierarchical Reinforcement Learning](https://arxiv.org/abs/2110.13625) (HIGL), 2021.
- [Fast and Precise: Adjusting Planning Horizon with Adaptive Subgoal Search](https://arxiv.org/abs/2206.00702) (AdaSubS), 2022.
- [Strict Subgoal Execution: Reliable Long-Horizon Planning in Hierarchical Reinforcement Learning](https://arxiv.org/abs/2506.21039), 2025.
- [Hierarchical Entity-centric Reinforcement Learning with Factored Subgoal Diffusion](https://arxiv.org/abs/2602.02722) (HECRL), 2026.
- [S3: Stable Subgoal Selection by Constraining Uncertainty of Coarse Dynamics in Hierarchical Reinforcement Learning](https://arxiv.org/abs/2607.19232), 2026.

These establish that reachable or adjacent subgoal selection is not new. The differentiation is the regime: post-hoc decision-time scoring for sampling-based MPC over frozen latent world models, without a learned task policy, value function, or online RL.

### 8.4 Adjacent July 2026 papers

These are search-neighbor citations, not benchmarks, unless a later full-text review finds a direct method overlap:

- [FARO: Feasibility-Aware Robot Motion Optimization](https://arxiv.org/abs/2607.18362), 20 Jul 2026.
- [KineBench: Benchmarking Embodied World Models via IDM-Free Kinematic Grounding](https://arxiv.org/abs/2607.19876), 22 Jul 2026.
- [FeelWorld: Visuo-Tactile World Model for Hierarchical Contact Prediction and Planning](https://arxiv.org/abs/2607.24267), 27 Jul 2026.
- [Operator-on-F complements value-equivalence: a planning-time diagnostic for latent world models](https://arxiv.org/abs/2607.04464), 5 Jul 2026.
- [A Control Theory of Predictability in Latent World Models](https://arxiv.org/abs/2607.10362), 11 Jul 2026.

## 9. Artifact and implementation status

| Component | Current evidence | Operational rule |
|---|---|---|
| Hi-LeWM | The paper links the method; the associated [Zenodo archive](https://doi.org/10.5281/zenodo.21353240) describes code, checkpoints, configurations, scripts, tests, and setup files | Treat “archive exists” and “reproduction works” as separate claims; test it first |
| HWM | Public repository `kevinghst/HWM_PLDM` covers a limited PLDM Diverse Maze implementation | Do not use it as the Hi-LeWM implementation base |
| LeWM | Public repository `lucas-maes/le-wm` and relevant task checkpoints | Underlying model/checkpoint reference |
| stable-worldmodel | Public repository `galilai-group/stable-worldmodel` | Trusted fallback harness |
| RC-aux | Public repository `Guang000/RC-aux` | Optional implementation reference for reachability supervision |
| ASAR | The v1 paper promises an artifact but did not provide a public URL at the search cutoff | Recheck before borrowing code; implement diagnostics from the paper meanwhile |

## 10. Re-verification and change control

Before the defense and again before submission:

1. Re-run searches for `hierarchical world model subgoal feasibility`, `diffusion subgoal score`, `latent reachability planning`, `action consistency world model`, and the exact M2 description.
2. Re-open the current arXiv records for Hi-LeWM, ACID, TRM, DOSER, SAGE, and ASAR; update version numbers, code status, and claims if their papers changed.
3. Generate BibTeX from primary records rather than copying author lists from this planning document.
4. Keep literature updates separate from the frozen experimental protocol unless a new paper invalidates the study's novelty or requires a named baseline for a defensible comparison.
5. Record every protocol amendment in a dated changelog with the motivating run or factual correction.

### Internal literature watch list — remove from examiner-facing exports

Maintain author alerts for the two groups that produced the closest rapid follow-ups during May-July 2026:

- **Liangyu Li** and **Qingwen Liu**: authors spanning TRM and ASAR.
- **Qi Zhang** and **Yisen Wang**: authors spanning VL-WM and SAGE.

Maintain topic alerts for: `hierarchical world model subgoal`, `latent reachability planning`, `subgoal feasibility world model`, `diffusion subgoal score`, and `action consistency world model`. Before the defense and every submission, manually recheck Hi-LeWM, ACID, TRM, DOSER, SAGE, ASAR, and their linked artifacts or project pages even if no alert fired.

### Consolidation changelog

- **28 Jul 2026:** created the master from protocol v3.2.1 and the verified literature portions of benchmark map v3.1.
- Removed v3.1's superseded label rules, sample-size language, gate wording, environment substitution rule, score definitions, matching claim, and novelty sentence wherever they differed from v3.2.1.
- Removed the internal provenance-letter system; links now point directly to primary records.
- Corrected HWM's lead author to Wancong Zhang and FF-JEPA's lead author to Sergi Masip.
- Preserved DOSER as a scoring precedent while retaining the exact limitation that M2 is an epsilon-prediction variant, not a direct transplant.
- Added the complete metric list locally, so no protocol rule depends on another file.
- Restored the four-author literature watch list as an internal operational appendix, excluded from examiner-facing exports.

## 11. Immediate next action

Stop revising the protocol from hypothetical review comments. The next evidence-bearing step is to execute the Hi-LeWM artifact, reproduce B0/B1, and run the P1/P2 pilot. The first stack trace or label distribution now has more decision value than another prose audit.
