# Independent PushT reachable-goal benchmark: prospective protocol v1

Status: implementation/test stage; final execution enabled only after the
collector, common-driver and analysis regression checks pass. User authorized
end-to-end implementation and a large study on 6 September 2026.

## Population and collection
Generate 6,000 independent accepted reference trajectories under namespace
`final-20260906-primary-v1`, distinct from `pilot-20260906-v1` and unit-test seeds.
Maximum 30,000 attempts. Same committed weak block-near random-action collector
as the 24-record technical pilot. Uniform agent xy in [50,450], block xy in
[100,400], angle in [0,2pi); zero initial velocities/forces/contact history.
Reject only initial penetration, nonfinite reference state, or position outside
[0,512]. Record every attempted index/reason; no comparison-model filtering.
Start at reference t0, goals at t75/t150. Keep actual state/action/dynamics
arrays and hashes. Reference action replay must reach its own endpoint.
H is a temporal offset, not the minimum number of actions required.
This is a NEW distribution, not a reproduction of the original expert dataset.
Newly generated trials are not original SAGE or LeWM training episodes; this
does not imply that their state distribution is novel or unsupported by training.

## Models and interfaces
Five unchanged E18 arms plus released full SAGE are the final six arms.
All E18 seeds 7201/7202/7203 and their normalization/checkpoint identities stay
frozen. SAGE uses its released single generator/prior checkpoint and three
paired evaluation-seed blocks, not three independently trained SAGE models.
Common native swm006/Pymunk environment with immutable R3 fresh initialization.
E18 uses its original FP32 runtime; SAGE uses released BF16 LeWM source and
historical pickle mappings, generator, GMM, 300-candidate/30-round/30-elite CEM.
No inherited model parameter, action prior, guidance, denoising or score is tuned.
Native SAGE accepts finite unbounded commands; preserve that original execution
behavior in the main arm. E18 is intrinsically bounded. Both use the SAME native
step function without imposed clipping. Record action-bound excursions.
The explicitly projected `sage_box` is a PILOT sensitivity check, not a selected
replacement for native SAGE or a final primary arm.
Each record/arm/horizon/seed has a fresh policy, solver, cache and RNG.
Matched initialized raw inputs; own model-specific preprocessing. Independent
computation batch1. No legacy dataset evaluator or recorded-image overlay.

## Execution
Six arms x two horizons x three seed blocks per independent reference.
At most 2H primitive actions; native goal predicate includes agent and block xy
norm<20 and wrapped angle<pi/9. Stop at first termination/truncation/budget.
No success before first action. E18 retains its H-cycle delta restart. SAGE
retains native remaining=max(H-elapsed,15); do not silently harmonize algorithms.
No model results from the final data may be inspected for tuning.

## Large sequential design, not a small-study fallback
Prespecified cumulative looks at N=1,600, 3,200, and 6,000 distinct references.
D is each episode's mean paired success difference over both horizons and the
three fixed seed blocks. Primary contrasts: VAD continuation minus greedy300,
minus Gaussian continuation, and minus native full SAGE.
Three separately reportable superiority nulls E[D]<=0. Per-comparison one-sided
alpha spending at the looks: .001, .004, and (.05/3-.005). Total across all
looks and all three hypotheses is .05. Episode-level Student lower bounds use
t(1-alpha_look,N-1)*SD(D)/sqrt(N). Positive lower bound rejects that null.
+5 percentage points is the TRUE effect to detect, never a required observed
point estimate. No post-hoc endpoint/horizon weighting or sample-size changes.
Stop successfully before the next stage only if all three nulls have crossed
a prespecified boundary. Also stop for futility if, at a completed look, any
primary contrast has mean + t(.999,N-1)*SE < 0: a strong adverse signal. This
is a prespecified resource rule, not a confirmatory claim of inferiority.
Otherwise continue to the next fixed look up to N6000. Final data do not yet
exist when this rule is specified. False-futility probabilities under true
+5-point effects are included in the design diagnostics. Report every
look and final sample size, including negative results. An ordinary unadjusted
final confidence interval is not the sequentially valid primary interval.
Planning includes variance .25/.5/1 and cumulative-look simulations; at the
last look N6000 gives approximately 84% lower-bound joint power using the
conservative normal variance-one approximation and a union bound over three
false-negative probabilities. This is not a universal finite-sample guarantee.
Greedy576/GMM contrasts and per-horizon summaries are descriptive secondaries.
No inference about a population of retrained checkpoints from three fixed seeds.

## Integrity and failures
Before any look, require its complete registered episode/horizon/arm/seed grid,
model/source/input hashes, valid traces and independently recomputed success.
Finite native commands are required; no outcome-based execution retries.
Planner exceptions count unsuccessful and are categorized. Evaluator bugs or
missing/corrupt runs block inference and are not silently scored as a model loss.
Interrupted infrastructure work may be resumed with unchanged sources/seeds;
completed logical runs are never repeated to select better outcomes.
Raw arrays live on Prometheus with a separate local artifact backup; manifests,
code, stage decisions, summaries and recovery context are committed to GitHub.
Do not alter the old E11--E19/R1--R3 records or claim SAGE paper fidelity.

## Resource envelope
Maximum216,000 logical arm/horizon/seed runs at N6000; first look57,600.
Conservative full-budget envelope:1.3s/SAGE planning call,0.3s/E18 call,
10ms per delivered simulator/action/render step, plus20% startup/I/O allowance:
about180 allocated A6000-hours through N1600 and670 through N6000. These are
planning assumptions, not measured future cost or completion-time promises.
At most four GPUs requested concurrently, subject to scheduler availability;
each64-reference worker has a two-hour cap. No new model training.
