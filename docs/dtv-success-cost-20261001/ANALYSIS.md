# Fixed source-paired success and cost estimation

Independent unit is a canonical parent trajectory. There are 320/task; the three checkpoint/proposal blocks are fixed repeated measurements within that unit, not 960 independent sources/task. Training-seed generalization to all possible models is not established by these three historically selected frozen checkpoints.

The source-cluster bootstrap assumes independent, exchangeable parent trajectories within each eligible task population, conditional on its reconciled developmental roles and fixed models. Unique episode labels alone do not prove this assumption. SHA ordering is outcome-independent selection without replacement from those finite pools; no finite-population correction or universal superpopulation/untouched-confirmation guarantee is asserted.

Average each configuration's three block measurements within parent, then average parents within task. Show each task first and all fixed blocks separately. Aggregate tasks with weight 1/3, never by episode count or selected favorable task. Include every declared episode and every unsuccessful **scientific outcome** in cost summaries. A technical failure is neither a fabricated success=0 nor a silently dropped case: full-grid analysis remains blocked until an explicitly authorized finite recovery resolves it, with attempts/costs preserved.

Two primary axes are (a) native success difference and (b) complete cumulative observation-to-action planning seconds/episode. DTV30 minus ACID30 is the matched-work primary. DTV30 minus ACID28, forward30 and plain30 are the three key practical contrasts. Negative planning difference means lower cost; report paired absolute differences and configuration means, not a success-per-second ratio as the sole endpoint. All eight predefined points are retained.

Use 10,000 shared whole-parent bootstrap resamples, fixed seed 20261001, separately within each task. Every draw carries all eight configurations and all three blocks together. Equal-task contrasts average the three within-task draw estimates. Report nominal percentile 95% intervals and two-sided Bonferroni percentile intervals for the **32-cell family** (four contrasts x three tasks plus equal-task x two axes), alpha .05. The bootstrap intervals, even Bonferroni-adjusted, are not finite-sample guarantees; tails at this resample count are relatively coarse. No favorable declaration is required for publication. Other point/diagnostic intervals are explicitly descriptive, not an unlisted family of significance claims. Record all source contrasts and the complete episode summary grid.

The implemented estimator also reports solver-only, first-decision, later-decision, episode, action-count, decision-count, audit and scoped CPU summaries. First-decision costs are common-start comparisons (zero for initial-success cases); later calls are actual visited-state comparisons, not matched-state benchmarks. No success-conditioned timing filter is allowed. Savings caused by fewer plans/actions or early termination must be separated from solve-speed claims.

No application-based success-loss margin has been provided. This is therefore an **estimation study**, not a non-inferiority test. No invented acceptable-loss flag, automatic expansion, model promotion, equivalence-from-nonsignificance, new 10% threshold, or post-outcome percentage criterion is authorized.

## Why 320 parents per task

The limiting reconciled PushT pool has 380 eligible parents. A fixed 320 gives equal tasks, all three blocks, and exact balanced eight-position ordering, with remaining eligible parents unallocated; it is not a sample expansion trigger. Historical small D1/ACV success pairs are not transportable variance estimates here: canonical source roles, short horizon, checker settings and prospective reset/terminal semantics differ. They are not pooled or used to presume zero losses. Instead use a declared range of paired discordance `q=Pr(gain)+Pr(loss)` = .02/.05/.10/.20/.40, and differences .01/.02/.03.

For planning only, the binary paired-source variance upper proxy is q-d²; averaging fixed seed blocks does not multiply n. Normal-approximation half-width is 1.96 sqrt((q-d²)/320), and equal-task proxy 1.96 sqrt((q-d²)/(3*320)), assuming independent source sets and no task covariance. These are not guarantees and do not replace the frozen bootstrap estimator.

| Plausible discordance | Task half-width near a 2pp effect | Equal-task half-width |
|---|---:|---:|
| .02 (1pp effect; gains 1.5%, losses .5%) | 1.55pp | .89pp |
| .05 | 2.44pp | 1.41pp |
| .10 | 3.46pp | 2.00pp |
| .20 | 4.90pp | 2.83pp |
| .40 | 6.93pp | 4.00pp |

`PLANNING-EVIDENCE.json` gives all 13 feasible positive-loss q/d combinations including 1–3pp effects, with gains (q+d)/2 and losses (q-d)/2. The impossible q=.02,d=.03 combination and the q=.02,d=.02 zero-loss boundary are excluded, not treated as planning assumptions. At q=.05 the 1–3pp effects correspond to gains 3–4% and losses 2–1%; at larger q, both gains and losses increase. A one-point difference can easily remain unresolved; a task-specific three-point difference is not reliably distinguished when discordance is substantial. This limitation is accepted prospectively, not fixed by dropping losses, treating seeds as sources, or expanding until an interval passes. For cost-axis precision there is no compatible new-interface variance estimate: preserve paired bootstrap uncertainty and actual raw timings rather than inventing a precision guarantee from cached-latent repetitions.
