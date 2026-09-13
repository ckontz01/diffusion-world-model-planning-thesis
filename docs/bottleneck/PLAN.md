# Diffusion bottleneck study: development plan

Prepared 13 September 2026. Base repository commit: `001aad99a2e2e6a141797e0c516604e7188d706a`.

## Aim and status

Identify which changes can improve the current diffusion planner, then develop a stronger method. The completed independent PushT result is the baseline, not a limit on what diffusion can achieve. This plan does not modify its recorded results, tests, stopping decision, or evaluation rules.

This is outcome-informed development. The latest aggregate results were already known when the plan was written. No statement in this document converts those data into new untouched confirmation. The longer-term target is a mechanism supported by controlled interventions and improvements across strong baselines, tasks, and computational budgets—not merely another favorable point estimate.

Implemented locally: summary checks, an outcome-tensor analyzer, a raw-trajectory diagnostic reader, and a full indexed-backup rechecker. The real summary and complete outcome tensor have been hash-verified and analyzed locally. A separate standard-library reaggregation checked all 15 method-pair contingency tables and all 20 point contrasts and cluster standard errors. The raw-trajectory mode has not been executed on real traces in this session. The simulator intervention runner is NOT implemented or launched. The desktop is offline, and GitHub branch creation was blocked before execution.

## Preserve the existing work

The original study completed at 1,600 references. Its remaining 4,400 references stay outside development payload reads. Both old short-horizon studies and all E19/R1–R3 historical decisions retain their original meanings. In particular, E17 (the action-conditioned state-adapter preflight) remains failed on Cube; a new experiment can investigate the unchanged model without relabelling that result. The original E16/E17 restriction against full-horizon diffusion was a scope choice for those studies, not a general ban on future research.

All new code and outputs belong on `diffusion-bottleneck-analysis`, based on the experiment branch—not an E20 reproduction and not a continuation of the stopped sequential study. The branch has not been created remotely in this session. No global permission setting, model checkpoint, or protected allocation is changed by the patch.

## A. First analyze the completed evidence

A1. Verify the published summary, outcome tensor, and independent-verifier identity. The tensor order is reference × horizon × fixed seed block × method. There are 1,600 independent reference units and 57,600 paired measurements; there are not 57,600 independent trials.

Report all five VAD-continuation contrasts, by horizon and equally weighted overall. Compute the within-reference H150-minus-H75 interaction for each contrast, keeping both horizons and all fixed seeds together. Secondary intervals are explicitly exploratory and unadjusted for the original stopping rule or new multiple testing; they cannot replace the registered bounds.

A2. Count paired successes and failures between each pair of methods, including VAD versus SAGE. A union of whole-planner successes is a privileged, nondeployable between-policy oracle. It does NOT show that one planner's candidate bank already contains the other's successful plan.

A3. Rehash all 450 sealed raw-result shards before interpreting trajectories, then recheck every trajectory against its recorded outcome. Inspect only the first completed look. No missing/corrupt run is silently turned into model failure, and no subset result is called the complete grid.

The actual archived position rule is the Euclidean norm of the JOINT four-coordinate agent/block position error, below 20, together with wrapped block-angle error below pi/9 at the SAME post-action step. Independent agent<20 and block<20 thresholds are not equivalent. Initial t0 is excluded from recorded success. Noncanonical angles cause a review stop, not a silent alteration of historical labels.

Break down terminal failures into joint-position only, angle only, both, and recorded planner exceptions. Separately report whether block pose was ever close without satisfying the full task. Compute simultaneous joint margins rather than combining best positions and best angles from different moments. These descriptions localize symptoms, not causes.

A4. Report episode-loop and solver-call timing with explicit boundaries. Episode-loop time excludes initialization; solver time excludes some surrounding preprocessing. The old timing ratio is not an end-to-end or equal-budget superiority result.

## B. Controlled simulator interventions

Use only already evaluated references 0–1599 for development. Select 32 references by a declared SHA256 ordering independent of individual outcomes; the manifest accompanies this plan. Use its first four references for an engineering pilot. This small pilot is not the final efficacy study and does not replace the user's large-study objective.

Initial probe settings: H75/H150, fixed checkpoint block 7201, and decision anchors t=0 and t=30 in the unchanged VAD-continuation trajectory. If that trajectory terminated before t=30, record the anchor as unavailable; do not substitute a different record or force post-termination execution. Later broadening to additional checkpoint blocks and proposer families is development and must be recorded before those outputs are inspected.

### Reconstruct the branch point correctly

Start from the stored exact initialization request through R3 (the fresh-state initializer), then replay the actual delivered prefix from the original trajectory. Do not reconstruct a later branch point merely by assigning its seven observation coordinates. The replay must reproduce the prefix trajectory and capture fresh simulator/controller state and rendered observations. Repeat the replay in fresh processes. This is not proof that every opaque simulator cache has been reconstructed; any unverified state component and numerical tolerance must be disclosed.

At each anchor, regenerate the unchanged baseline planning call with its original RNG stream. First-bank actions, selected actions, and recorded plan hashes must agree before adding an intervention. Retain full raw and planner-coordinate candidates, continuation noise, predicted latents, adapter outputs, selected indices, source/checkpoint hashes, and actual branch actions—not hashes alone. A failed baseline replay is an engineering defect to resolve, not a negative result for diffusion.

### B1. Isolate continuation scoring on exactly the same first bank

Reuse one 64-candidate first bank. Compare greedy-64 selection with the existing 64-by-8 continuation choice. Both receive the identical current input and candidate actions. The existing greedy-300 and greedy-576 controls remain useful, but they do not isolate the score on an identical candidate bank.

Use declared common noise for each branch/continuation; do not let loop order, an early termination, or one arm's extra model call alter another arm's random stream. Store the noise banks so this can be checked directly.

### B2. Separate state-adapter and latent-prediction error

For each first branch, obtain the actual simulator successor by replaying from the verified anchor. Keep the first action chunk fixed across all conditions:

| Condition | Latent supplied to the second proposer | Ordinary state supplied to the second proposer |
|---|---|---|
| Baseline | LeWM-predicted | Adapter-predicted |
| State intervention | LeWM-predicted | Actual simulator state |
| Latent intervention | Encoded actual observation | Original adapter prediction |
| Joint intervention | Encoded actual observation | Actual simulator state |

The two mixed conditions can be internally inconsistent. They are diagnostic interventions, not deployable algorithms. Hold the original adapter output fixed in the latent-only condition; recomputing it would change two components at once. Compare the joint intervention and interaction, not only whichever marginal looks favorable. A large combined effect does not automatically identify which component should be redesigned.

Measured outputs: generated-branch adapter error, latent prediction error, changed continuation distribution, branch-selection agreement, actual short rollout quality, and outcomes under a fixed declared remaining-horizon policy. Expert-action imitation error alone must not decide whether an alternative action is useful.

### B3. Separate bad generation from bad ranking

On fixed candidate banks, compare predicted ranking with actual outcomes from executing those same branches. A short-horizon joint-distance oracle measures short-horizon ranking headroom only. To speak about distant-goal success, evaluate a declared tail policy through the remaining original action budget. A branch that fails under that tail policy is not proved irrecoverable under all policies.

The primary diagnostic oracle selects among candidates using realized outcomes and must never appear as the proposed deployable planner. Save both failed and successful branches and all selection rules. Compare coverage for diffusion, diagonal Gaussian, and the trajectory-level GMM using matched collection and scoring conditions.

### B4. Other hypotheses, separately labelled

Investigate deeper lookahead, temporal-history conditioning, and remaining-horizon scheduling only after the previous controls are interpretable. Report both controlled algorithmic work (candidate rollouts, model calls) and measured wall time. Changing history length may require retraining and changes the information supplied; it is not a trivial inference-only switch. Different action-bound behavior is a system difference to measure, not grounds to quietly clip SAGE after seeing its score.

## C. Choose one leading redesign

The leading hypothesis is that proposal quality and branch ranking degrade on imagined continuations. It remains a hypothesis, not a causal result from the current summary. Select the redesign from the completed interventions:

- An adapter bottleneck motivates training/evaluating on planner-generated branches or a demonstrably adequate latent-history interface.
- Good branches with poor predicted ranking motivate a better downstream value/ranking mechanism, with fixed-bank controls.
- Inadequate useful-action coverage motivates improving the proposal distribution; a more elaborate selector cannot select an absent action.
- A lookahead bottleneck motivates deeper or connected sequence planning, with model-error and compute controls.

Do not add all components at once. Include same-data and same-training-budget Gaussian/GMM controls and remove the proposed new mechanism in an ablation. Collecting simulator-labelled counterfactual branches changes the data budget and potentially the offline-learning setting; disclose that change and give relevant competitors equivalent access.

No failed proxy threshold permanently closes a research direction. Hard integrity failures make a run uninterpretable; weak expert-action MSE is not, by itself, proof of poor control. New data cannot be used repeatedly for model selection and then described as untouched confirmation merely by changing protocol names.

## D. Stronger publication evidence

After a mechanism works on development data, evaluate native full SAGE and separately named budget variants, strong non-diffusion proposal controls, and relevant diffusion baselines. Compare success–compute curves rather than choosing a convenient single budget after results. Preserve the strongest native baseline operating point.

Add informative non-ceiling tasks and a second world-model representation after checking interface feasibility. A separately retrained proposer on another backbone is evidence about approach robustness, not zero-shot transfer of one checkpoint. Choose task families for the scientific question before knowing which favors the new method.

Finally fix the method, training recipe, primary contrasts, evaluation population, success and timing rules, and sample-size rationale before new final outcomes are inspected. Account for independent reference clusters and training-seed variation. The remaining 4,400 collected references are a potential later resource, not an automatic continuation of the stopped study. No final population or sample size is frozen by this development document.

## Evidence and next executable step

Source code: `cluster/prometheus/analyze_independent_pusht.py`, `independent_pusht_evaluate.py`, `gdp_cem_e18_closed_loop.py`, E17 preflight protocol, and the independent PushT protocol at the base commit. The accompanying provenance file identifies the exact source paths and artifact digests.

A1–A2 are now completed locally on the pinned outcome archive; see PAIRED-RESULT.md. Next executable work is full backup revalidation and the A3–A4 raw-trajectory reduction. The simulator intervention runner must then be implemented against the pinned runtime, tested on the declared four-record engineering pilot, and expanded only with measured artifact integrity and resource use. No claim that those executions happened is made here.
