# ACID-alternative E6: quantile-constrained CEM protocol

Date frozen: 2026-08-16  
Role: post-E3/E5, exposed-D2 method development  
Confirmation status: **not confirmation**  
Protected data: **C1 and I1 remain sealed and must not be read**

## Question

E3 established that residual diffusion (`RDX`) ranked failed imagined
trajectories strongly on fixed candidate pools but lost to the
published-equation ACID reconstruction when its continuously weighted score
was optimized in closed loop. E5 established that a same-model
counterfactual-successor difference did not repair the problem. E6 asks a
narrower question: can the already trained RDX model improve CEM when it is
used only as a bounded feasibility veto, after goal-directed search has found
a promising basin?

E6 does not train a new model. It changes only the frozen planner integration.
It uses the previously exposed D2 starts and therefore cannot support a
confirmation or publication claim by itself.

## Fixed data, model, and planner

- Tasks: PushT, Reacher, Cube.
- Starts: the 50 frozen D2 starts per task created by job `297535`.
- Scorer seed: `6101`; paired planner seed: `8301`.
- Released Le-WM checkpoints, datasets, preprocessing, action
  standardization, environment implementation, and evaluation starts are
  exactly those used by E3.
- Goal offset: 25; evaluation budget: 50.
- CEM: 300 candidates, 30 iterations, 30 elites, horizon 5, action block 5,
  receding horizon 5.
- RDX: the frozen seed-6101 true-action or shuffled-action residual-diffusion
  checkpoint from E3, sigmas `{0.25, 1.0, 4.0}`, eight fixed draws per sigma.
- ACID and deterministic-forward controls use the same seed-6101 checkpoints
  and literal cost implementations as E3.

No C1 or I1 path may be opened. No D3 data may be selected until this study
has been analyzed and its frozen promotion rule applied.

## Quantile constraint

For each independent CEM cost call, verifier costs are ranked within that
one 300-candidate population. Lower verifier cost is treated as more
feasible. At rejection fraction `q`, exactly `300*q` worst-ranked candidates
are made ineligible for the 30-member elite set. Feasible candidates retain
their original Le-WM goal costs exactly; rejected candidates receive a finite
sentinel cost strictly larger than every feasible cost. Thus the verifier
cannot improve the relative ordering of feasible candidates and cannot enter
as a continuously scalable reward.

For a tail-five arm, calls 1--25 of every 30-call CEM solve return the goal
cost bit-for-bit. The quantile veto is active only on calls 26--30. For an
all-iterations arm it is active on calls 1--30. The implementation must record
the solve-relative iteration, feasible count, threshold, and number of the
goal-only top-30 candidates vetoed on every call.

## Frozen arms

1. `b0`: original goal-only CEM.
2. `acid_cont`: E3's continuously weighted published-equation ACID
   reconstruction.
3. `forward_cont`: E3's continuously weighted deterministic forward verifier.
4. `rdx_cont`: E3's continuously weighted true-action RDX verifier.
5. `rdx_gate_tail5_q20`: true-action RDX, worst 20% vetoed in iterations
   26--30; cutoff sensitivity only.
6. `rdx_gate_tail5_q40`: true-action RDX, worst 40% vetoed in iterations
   26--30; **sole primary E6 endpoint**.
7. `rdx_gate_all_q40`: true-action RDX, worst 40% vetoed in all iterations;
   timing/integration ablation only.
8. `rdx_shuffled_gate_tail5_q40`: matched shuffled-action residual-diffusion
   checkpoint with the primary integration; causal null.
9. `acid_gate_tail5_q40`: ACID score with the primary integration; score-family
   control.
10. `forward_gate_tail5_q40`: deterministic-forward score with the primary
    integration; non-diffusion learned-control.

All ten arms are rerun rather than borrowing old E3 outcomes. The primary arm
cannot be replaced by the q20 or all-iterations arm after outcomes are known.

## Frozen analysis and pilot promotion rule

The unit is a paired D2 start within task. Report every task separately and an
equal-task mean. Report paired task-stratified bootstrap intervals using
100,000 replicates and seed `2026081606`, but do not demand interval exclusion
in this one-scorer-seed pilot.

The primary endpoint advances to a three-scorer-seed exposed-D2 replication
only if all of the following point-estimate gates pass:

1. `rdx_gate_tail5_q40 - acid_cont > 0` on the equal-task mean;
2. `rdx_gate_tail5_q40 - rdx_shuffled_gate_tail5_q40 > 0` on the equal-task
   mean;
3. `rdx_gate_tail5_q40 - b0 >= 0` on the equal-task mean;
4. it is no more than 0.10 below either `acid_cont` or `b0` on any task, and
   exceeds `acid_cont` on at least two of the three tasks;
5. `rdx_gate_tail5_q40 - forward_gate_tail5_q40 >= -0.02` on the equal-task
   mean.

All gates are evaluated even if an earlier gate fails. A failure stops this
endpoint before D3. Passing authorizes only a separately frozen multi-seed D2
replication; it does not authorize a claim. Only after that replication may a
single endpoint be frozen for fresh D3 evaluation.

## Interpretation boundaries

- E6 is explicitly influenced by E3, E5, and exploratory same-pool D2
  analyses. It is method development, not independent evidence.
- A q20 or all-iterations success after a primary q40 failure is hypothesis
  generation only.
- A true-RDX gain without a gain over shuffled RDX does not establish a
  diffusion mechanism.
- A true-RDX gain without competitiveness against the forward gate does not
  establish that diffusion is needed.
- The ACID arm is an audited reconstruction from the publication, not authors'
  unreleased official code, and must be described that way.
- No sign inversion, task-specific cutoff, post-outcome arm deletion, pooled
  task substitution, or protected-data inspection is allowed.

