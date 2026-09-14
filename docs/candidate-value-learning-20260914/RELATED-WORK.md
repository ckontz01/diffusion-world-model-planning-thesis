# Closest mechanisms and what CVL-1 could establish

Primary-source review, 14 September 2026. This is a focused positioning review,
not an exhaustive novelty search or a benchmark comparison. None of these papers
is evidence that the proposed PushT experiment will succeed.

|Prior method|Relevant established ingredient|Difference in this proposed test|
|---|---|---|
|**IDQL** (Hansen-Estruch et al., 2023)|Decouples critic learning and diffusion behavior modeling; extracts actions by critic-weighted sampling or candidate argmax. This is especially close to the proposed selection mechanism.|CVL-1 uses directly observed finite-budget, fixed-continuation binary success targets for 15-action chunks, not generalized IQL Bellman targets. The existing proposer is frozen rather than trained for this study. [Paper, §4.2](https://arxiv.org/html/2304.10573v2).|
|**Select from Behavior Candidates / SfBC** (Chen et al., 2023)|Separates expressive generative behavior modeling from action evaluation, including diffusion behavior models and in-sample planning.|Separating proposal generation and evaluation is already known. CVL-1 tests a particular native-success target and frozen LeWM feature interface rather than proposing this decomposition. [Paper](https://arxiv.org/abs/2209.14548).|
|**Diffusion-QL** (Wang, Hunt & Zhou, 2023)|Learns an action-value function and incorporates value maximization into diffusion policy training alongside behavior modeling.|CVL-1 has no gradient through denoising, no changed diffusion loss, no actor update and no added Q-guidance during sampling. It reranks an unchanged bank. [Paper](https://arxiv.org/abs/2208.06193).|
|**Diffuser** (Janner et al., 2022)|Plans via trajectory denoising, using objective guidance and conditioning for flexible behavior synthesis.|CVL-1 does not diffuse states/entire plans anew, perform gradient-guided sampling or alter the generative objective; it predicts candidate outcome after sampling. [Paper](https://arxiv.org/abs/2205.09991).|
|**MBOP** (Argenson & Dulac-Arnold, 2021)|Combines a learned world model, behavior prior and a learned fixed-horizon value function; its value target avoids bootstrapping.|A learned finite-horizon evaluator alongside a behavior proposal and world model is not new. CVL-1's labels come from fresh candidate executions plus a declared original continuation policy, with native goal success through an explicit remaining budget. [Paper, §2–3](https://arxiv.org/html/2008.05556v3).|
|**TD-MPC2** (Hansen, Su & Wang, 2024)|Uses latent world-model planning with learned terminal value to estimate returns beyond the local planning horizon.|CVL-1 does not jointly learn the world model, reward/value system and policy, or bootstrap an optimized terminal value. It tests Monte Carlo policy-conditional candidate success with existing frozen components. [Paper, §3](https://arxiv.org/html/2310.16828v2).|

## Modest, testable contribution

The question is whether **full-remaining-budget native-success prediction under
the original continuation tail** improves candidate selection in this particular
frozen diffusion/LeWM planner, and whether that improvement survives repeatedly
using the new selector. The specific contribution would be empirical evidence
about the target, time/schedule conditioning, and the separation of evaluator
effects from proposer-family effects—not invention of diffusion plus value.

We are testing a Monte Carlo policy-evaluation-style target, followed by a
restricted candidate policy-improvement step. Learned receding-horizon deployment
departs from the label policy and can amplify error. IDQL's candidate-argmax
formulation is a particularly important precedent; MBOP is an important precedent
for the model/prior/fixed-horizon-value combination. Neither should be hidden
behind a comparison only with short-horizon distance.

## Interpretations to precommit

- Better prediction without better within-bank selection: calibration does not
  establish useful relative ordering.
- Better eight-way selection but worse full-64 closed-loop behavior: possible
  distribution shift, maximization error or mismatch between continuation-tail
  labels and repeated learned decisions; not permission to tune a mixture.
- Logistic matches the MLP: evidence for the target/features, not a need for
  neural complexity.
- Shared evaluator helps both diffusion and matched GMM: supports an evaluator
  effect rather than diffusion-specific advantage.
- Diffusion-only transfer works and GMM does not: first account for training
  proposal coverage and common VAD-tail target; do not claim intrinsic diffusion
  superiority from asymmetric data or out-of-distribution GMM features.
- Too few positive labels: an honest feasibility limit for this exact native-
  success experiment, not a reason to replace the target with distance afterward.
