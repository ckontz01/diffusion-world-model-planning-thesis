# Primary sources checked — 23 September 2026

This ledger records both overlap and access limitations. Exact novelty is NOT
established by failing to find an identically named method.

1. Frazier, Powell, Dayanik (2009), The Knowledge-Gradient Policy for Correlated
   Normal Beliefs. Primary journal page retrieved.
   https://pubsonline.informs.org/doi/10.1287/ijoc.1080.0314
   Established: correlated learning across alternatives and decision-valued
   information acquisition. The toy contingent selector is a standard Bayes rule.

2. Harrison, Sharma, Pavone (2018), Meta-Learning Priors for Efficient Online
   Bayesian Regression (ALPaCA). Primary abstract retrieved.
   https://arxiv.org/abs/1807.08912
   Established: learned features/prior with Bayesian linear online updates.
   Strong same-data baseline; low-rank update alone is not novelty.

3. Baltussen, Heemels, Katriniok, Dual MPC for Active Learning of Nonparametric
   Uncertainties. Primary abstract retrieved; preprint Nov2025, journal2026 listing.
   https://arxiv.org/abs/2511.08542
   Established: active GP uncertainty reduction within control, learning/control
   tradeoff and safety assumptions. No claim our method invents dual control.

4. An et al. (2026), Feedback World Model Enables Precise Guidance of Diffusion
   Policy. Full HTML v1 inspected, especially equations8–16.
   https://arxiv.org/html/2605.15705v1
   It holds residual e_t fixed within guidance and adds L e_t to action-conditioned
   velocity predictions; actual execution updates feedback. Also action-aware
   diagonal latent weighting. Our proposal is not first inference-time feedback.

5. CheckVLA (2026), Execution-Time Verification with Action-Conditioned World Model
   for Long-Horizon Mobile Manipulation. Full HTML v1 retrieved.
   https://arxiv.org/html/2607.26789v1
   Execution mismatch monitoring and suffix repair; calibrated first-intervention
   scope. A full robot comparison requires equivalent observations and repair.

6. IMPLY (2026), arXiv2609.12441. Primary indexed abstract retrieved; full page
   failed. Alternative imagined pushes checked through inferred physical
   parameters, anchored by two observed calibration pushes.
   https://arxiv.org/abs/2609.12441
   Do not claim its full method lacks an active/evidence-transfer variant.

7. ACID (2026), Action Consistency via Inverse Dynamics for Planning with World
   Models. Full HTML v1 and authors' page retrieved.
   https://arxiv.org/html/2607.02403v1
   https://gawon1224.github.io/ACID/
   Inverse-action consistency scoring within planning, not a real prefix test.
   This prototype does NOT reproduce its inverse model or reported benchmarks.

8. qEUBO (2023), A Decision-Theoretic Acquisition Function for Preferential Bayesian
   Optimization. Primary abstract retrieved.
   https://arxiv.org/abs/2303.15746
   Existing decision-theoretic acquisition; explicit relation to knowledge
   gradient. Do not claim expected utility of an information-dependent choice
   as an original acquisition principle.

Other inspected/search leads (not relied on to assert a new gap): ReDRAW latent
residual adaptation; OnlineWM active interventional collection; CoCo counterfactual
consistency; UWM-JEPA structured uncertainty. Their existence further rules out
broad claims of first adaptation/intervention/belief-aware world model.

Repository context read in this turn through GitHub connector:
https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/02a6157ecb11ff2a9cf6ced6ce0523b181805db0/docs/action-verification-testbed-20260922/CANDIDATE-MECHANISM.md
It documents the old static proposal's reduction to known controls. No repository
file, research model, research artifact, or historical decision was edited.
