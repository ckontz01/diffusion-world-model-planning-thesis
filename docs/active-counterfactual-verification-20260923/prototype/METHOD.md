# Active counterfactual feedback verification — candidate specification

Date: 23 September 2026. Working research proposal, not a paper/priority claim.

## Decision

Investigate an **evidence-acquiring action verifier**: take a short, budgeted
prefix of an existing plan, observe its real consequence, use a learned
cross-action response model to revise the ranking of available continuations,
and then execute a continuation. Choose the prefix for the expected improvement
in the eventual decision, not for the magnitude of surprise alone.

This is an explicit change from purely pre-execution verification. No world-model
weights or action-proposer weights need change at deployment. The effective
controller, observation schedule and amount of commitment do change. They must
be compared to equally instrumented passive and early-replanning controls.

The intended new *system component* is a learned **prefix-observation to
counterfactual continuation-success model**, shared across the action bank. The
Bayesian/contingent decision rule itself is established. No claim of first active
control, first feedback verifier, or new distribution-free guarantee is made.

## Why the old architecture could not supply this capability

With a fixed observation h and fixed predictions, changing a calibration threshold
can keep the baseline or choose the same already preferred alternative. It cannot
reveal an episode-specific hidden response. A real prefix observation can supply
such evidence. This is conditional on useful hidden information actually being
present: RB2 does NOT establish it is the cause of its negative result.

## Variables and deployable information

h: observed history, action history, goal and remaining action budget.
p: a permitted short control prefix from a fixed candidate tree.
r_p = E(o_after_p) - F(h,p): observed-minus-predicted latent response.
a_i: a continuation available after prefix p, NOT an action from an unchanged
counterfactual starting state.
Y_{p,i}: native task success after p, continuation i, then the fixed baseline tail
until the ORIGINAL remaining budget. It includes any early native success.

The learned model estimates the JOINT law of r_p and each Y_{p,i}:
    rho_phi(r | h,p), q_phi(i | h,p,r) = P_phi(Y_{p,i}=1 | h,p,r).
Candidates share the response law and optional latent error modes; outputs are
not unrelated confidence intervals. Observations, predictions and residuals are
all deployable inputs; true hidden physics and unexecuted outcomes are not.

A concrete bounded neural realization to test (NOT implemented here):
- Shared frozen E,F; context encoder on h, p and predicted prefix/terminal latents.
- Four-component conditional diagonal Gaussian response mixture. Fit response
  mean/variance in training-only normalized residual coordinates.
- A shared candidate encoder outputs one Bernoulli success probability per
  response-mixture component for each available continuation.
- After r, update component weights by Bayes' rule, and average candidate
  probabilities using those shared weights.
- Fit response likelihood plus per-candidate binary cross entropy, averaging
  within source and prefix. Composite per-candidate likelihood does NOT assert
  independence of the coupled branch outcome labels.
- No deployment optimizer steps; reset the evidence state at episode boundaries.

This model may underfit or be misspecified; it has no automatic calibration or
safety guarantee. A sufficiently expressive ordinary history-conditioned model
may match it and MUST be a same-data/same-information control.

## Decision rule

For every allowed prefix, evaluate
    V(p) = integral rho_phi(r|h,p) max_i q_phi(i|h,p,r) dr.

Choose the prefix with highest V, observing all real execution costs, changed
physical state, attainable suffixes and remaining budget THROUGH q's outcome
law. Include a direct/no-extra-test baseline option. A separate probe penalty
must not double-charge a cost already included in the terminal utility.

Execute only the chosen prefix; observe r; choose i maximizing q_phi(i|h,p,r).
Execute that continuation, then the fixed reference tail in the first bounded
study. At most one active verification operation per episode initially. Applying
it repeatedly is a distinct policy and is not justified by fixed-tail labels.

Do not simulate an unexecuted physical branch during deployment or reset the
robot after measuring a prefix. Sensor calls, control steps and planning calls
are charged. The prototype uses exactly two abstract control stages for EVERY
policy. Its prefix-dependent cost is in terminal success probability; it is not
a physically simulated movement.

## Candidate-tree implementation boundary

Continuous action banks almost never share exact prefixes by accident. Therefore
prefix/continuation grouping MUST be explicit, not inferred from approximate
hash matches. A practical shared tree can use a small fixed set of selected
prefixes and constrained vanilla-CEM suffix search, with the original baseline's
actual returned plan included. All experimental controls must receive the same
tree and search allowance. This changes search packaging, not learned proposer
weights; it must not be labelled a rank-only intervention on an unchanged flat
bank. Costs and action associations need separate tests.

An alternative is to regenerate continuations after the observed prefix. Then
the pre-prefix value model must represent that actual future generation rule;
it may NOT assume availability of a bank from a different predicted state. The
first design should use the explicitly fixed tree to avoid that hidden change.

## A useful exact reduction, not a new theorem

For a jointly Gaussian approximation to utility vector U and observation residual
r, only the contrasts D U (each alternative minus baseline) matter for argmax of
conditional MEAN utility. Let C = Cov(DU,r), S = Var(r)=L L^T and W=C L^{-T}.
Whiten r, and retain the right singular subspace of W. Its dimension is at most
K-1 for K choices. The conditional contrast mean and covariance are unchanged:
    E[DU|r] = D mu + W L^{-1}(r-mu_r)
    Var(DU|r) = D P D^T - W W^T.
The code implements this sufficient statistic. A common utility-error component
vanishes from D. This is ordinary Gaussian conditioning and linear algebra.

This statement applies to the specified Gaussian utility law and posterior-mean
ranking. It does NOT prove sufficiency for an arbitrary nonlinear Bernoulli
mixture, chance constraint, risk-sensitive utility or real latent representation.
It does NOT guarantee a speedup: learning and computing the covariance also cost
work, and a good low-rank GP/ALPaCA implementation is a strong comparator.

## Mathematical scope of the action-selection benefit

Under a correct joint model and fixed p,
    E_r max_i E[Y_{p,i}|r] >= max_i E[Y_{p,i}].
This follows by allowing the adaptive decision to emulate any fixed continuation.
It does not make arbitrary probes free: the success law depends on p. Maximizing
across p only dominates the best committed plan when that committed plan is in
the available choices and the joint model is correct. This is standard Bayesian
experimental design/dual control, not a novel optimality theorem.

## Closest prior art and contribution boundary

- Correlated knowledge gradient: already prices information by its effect on the
  best later choice. Our contingent equation reduces to it in the appropriate
  finite Gaussian setting. Exact Bayes is not a method we claim to beat.
- ALPaCA and Bayesian/GP dual MPC: already learn transferable dynamics beliefs
  and choose informative actions. Must compare a good implementation supplied
  equivalent data, not only static verifiers.
- Feedback World Model: corrects future latent predictions with a shared feedback
  state while keeping weights fixed. Our proposed cross-action update predicts
  distinct, potentially opposite effects on candidate outcomes and chooses which
  prefix to measure. The common-offset *toy ablation* is not a reproduction of
  FWM; a shared latent offset can still change nonlinear goal rankings.
- CheckVLA: detects execution mismatch and rewrites a suffix. Our proposed test
  is selected in anticipation of discriminating action consequences, with learned
  cross-candidate transfer. More frequent replanning is an essential control.
- IMPLY: uses observed calibration pushes to anchor physical hypotheses across
  predicted trajectories. Strong overlap with physically grounded verification;
  full manuscript was not retrievable, so exact priority remains unresolved.

Candidate empirical contribution: a small, deployable prefix-to-counterfactual
success operator for a frozen visual planner, with contrast-focused compression,
that improves decisions at matched control/observation/data/compute budgets.
A general 'active verification is new' claim is invalid. This package establishes
an executable mechanism candidate, NOT literature priority or robot efficacy.

## Decisive next real question and controls

Before a large study: does an actual prefix response improve held-out prediction
of differences between its feasible continuations, BEYOND the actual new state
and history that ordinary replanning already receives?

Controls, using the same candidate tree, data and budget:
1. Original/static decision, with correct control-time accounting.
2. Fixed early observation/replanning plus a strong history-conditioned predictor.
3. Passive Bayesian/GP or ALPaCA-style feedback with the same observed prefix.
4. Active generic information gain with comparable posterior/data.
5. Full proposed cross-action feedback and decision-valued prefix choice.
6. Ablations: same chosen prefix but no cross-action transfer; same learned
   transfer but prefix chosen without information value; full-vs-compressed
   observation handling under matched uncertainty models.
Literature native systems ACID/FWM/CheckVLA must be faithfully implemented or
explicitly called adaptations; none is represented by these toy controls.

Three requirements for progression: an informative physical signal exists on
unseen source histories; the response model improves ranking over strong
same-information controls; full-budget native success improves with all control
steps and compute counted. Improved latent error or selected toy success alone
cannot advance a robot efficacy claim.

No new source allocation, protected payload reading, Prometheus work, model
loading, research training or physical/simulator rollout was performed or is
authorized by this package. AV0 and AV1 status remain unchanged. A runtime pilot
needs a separately pinned implementation and finite scope; do not rerun the
old studies or use this proposal to reopen their decisions.
