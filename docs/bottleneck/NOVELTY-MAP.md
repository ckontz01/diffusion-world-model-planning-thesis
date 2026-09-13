# Initial novelty map — 13 September 2026

This is a screening map, not a completed novelty audit. The paper summaries below are grounded in the primary records inspected in this session. Most were checked at abstract level; implementation-level comparisons and a systematic search for additional recent work remain to be done before any novelty claim. No claim of being first is made.

| Work and primary source | What the inspected source supports | Consequence for this project |
|---|---|---|
| [Planning with Diffusion for Flexible Behavior Synthesis](https://arxiv.org/abs/2205.09991), Diffuser | Diffusion is used for trajectory-based planning. | Diffusion-generated plans themselves are not new. |
| [Diffusion Forcing](https://arxiv.org/abs/2407.01392), v4 | Independent per-token noise levels support sequence generation and variable-horizon guidance. | Variable horizons and noisy-context training cannot be claimed as new in isolation. |
| [Simple Hierarchical Planning with Diffusion](https://arxiv.org/abs/2401.02644), v1 | A higher-level temporally abstract diffusion planner guides a lower-level planner. | A diffusion hierarchy or coarse-to-fine planning alone is not sufficient novelty. |
| [Diffusion ReRoll](https://arxiv.org/abs/2607.19919), v1 | Structured re-noising allows different horizon segments to revise one another. | Cross-horizon revision alone is already an explicit contribution in nearby work. |
| [SAGE: Subgoal-Conditioned Action Generation for Latent World Model Planning](https://arxiv.org/abs/2607.17973), v1 | A generated local subgoal conditions action generation, then a frozen world model evaluates and refines proposals. | Better local objectives, proposals, and refinement are distinct explanations for its system-level advantage. |
| [PRISM `dp_prior_policy.py`](https://github.com/YuhaiW/prism-jepa/blob/main/dp_prior_policy.py), retrieved blob `171f114a901da16fcbc328a97db2cbfd2ce3eda1` | Its documented `best_of_n` mode samples diffusion-policy sequences and selects by world-model goal cost without MPPI iterations. | “Diffusion proposes; a frozen world model ranks once” is not a safe standalone novelty statement. This code inspection does not establish that the full DP baseline is independently runnable. |
| [When to Trust Your Model: Model-Based Policy Optimization](https://arxiv.org/abs/1906.08253), v3 | Short model-generated rollouts branched from real data address the model-usage/model-bias trade-off. | Limiting imagination depth or collecting branch data must be distinguished from existing model-based RL ideas. |
| [Model-Based Value Estimation for Efficient Model-Free Reinforcement Learning](https://arxiv.org/abs/1803.00101), v1 | Model-based value expansion limits imagined depth to manage model uncertainty. | A terminal value or bounded-depth rollout is not, by itself, a new planning principle. |
| [A Reduction of Imitation Learning and Structured Prediction to No-Regret Online Learning](https://arxiv.org/abs/1011.0686), v3 | The learning distribution can depend on the policy's own preceding actions; the paper studies training for that induced distribution. | Training on visited/planner-induced states is not a new general insight. It is not automatically DAgger without its supervision and learning assumptions. |

## Working contribution hypothesis

A possible contribution is a concrete mechanism that preserves action-proposal quality and reliable branch selection when a frozen latent world model supplies imperfect imagined context. To support that claim, the project needs a precise objective or inference procedure, ablations isolating it, matched access to training/branch data, strong generative controls, and gains across useful tasks and budgets.

That sentence identifies a target, not an already novel algorithm. The current implementation is a diagnostic package, not the proposed improved planner. If the adapter is not the dominant bottleneck, a different mechanism should be pursued rather than defending this hypothesis.

## Disambiguations and unresolved comparisons

The SAGE in this map is the July latent-world-model planner (2607.17973), not the separate March energy-gating SAGE (2603.02650). The latter was not re-audited here and should be included when the candidate mechanism becomes concrete. ACID's exact scoring baseline and its available implementation should likewise be re-audited before a new direct comparison; old reconstructed results stay labelled reconstructions.

The repository's E14 (long-horizon proposal development) already tested coupled subgoal/action diffusion. Reintroducing the same idea is not a new contribution simply because the study receives another identifier. E16/E17 tested a conservative state-interface bridge; their failures are useful design evidence, not a theorem against all continuations.

Next literature work should inspect full method sections and released code for the shortlisted mechanism, including inference-time optimization, multi-step model error, latent-state sufficiency, diffusion/flow proposal controls, and planning-aware training. The scope of this initial map is explicitly narrower than an exhaustive September 2026 literature review.
