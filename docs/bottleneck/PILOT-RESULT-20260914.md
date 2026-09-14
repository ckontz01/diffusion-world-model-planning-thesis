# Four-reference engineering pilot — completed 14 September 2026

The scoped pilot passed the combined runner, independent arithmetic, repeat,
and supplementary semantic checks. It provides a local same-bank selection
counterexample and mixed intermediate-context effects, **not** a resolved SAGE
gap, a new efficacy estimate, or evidence for a particular architecture change.
Historical decision remains `stop_futility_strong_adverse_signal`.

## Executed scope and evidence

References1269,582,525,722 were fixed by the earlier identifier-only SHA ordering
within exposed0–1599, not selected using their individual outcomes. Both H75/H150,
anchors0/30, checkpoint7201 and two fresh-process repeats ran. All16 distinct
reference/horizon/anchor points were available (32 including repeats). These are
four development references, not16 independent samples or32 independent repeats.

Simulation source commit `b1c9633e72b1b52f03ed32de9e875f4912eea411`:

- Launch manifest: `897dba9f318c48ae2e0889c8bf78ccf22808ccbe6132af7aee4e7648bfe8163f`.
- Runner: `a5791a8ecb69c3f0a94fe15616d66b227eca4550048cff0b1cec81d300ddca49`.
- Historical/pilot model-state identity: `f0c666cc011ab057390f7e1571cf3d8bde905d13ff11f1d406f6d3dd8575340d`.
- Run root: `/lustreFS/data/superworld/ckontzias/thesis/experiments/diffusion-bottleneck/pilot-20260914-b1c9633`.

| Jobs | Disposition |
|---|---|
|300964_0|COMPLETED0:0; ref1269 repeat0;71s|
|300965_1–7|All COMPLETED0:0; remaining seven;68,67,67,68,68,67,67s|
|300966|FAILED1; original independent decoder check; preserved|
|300973|COMPLETED0:0; corrected offline verifier;7s|
|300974|COMPLETED0:0; separate semantic/provenance supplement;6s|

No failed simulator run was rerun. Source/output directories and both earlier
verifier outcomes remain preserved. Bulk files are outside Git.

## Validation and its limits

The runner constructs R3 fresh worlds from original requests, replays delivered
prefixes, checks physical/controller state to absolute1e-10 and checks observation,
goal, action, historical selected-plan and proposal/GMM RNG identities. It checks
baseline regenerated second banks and rollout equality and common second noise.
Model-state hashes are checked before/after execution. Those are **runner
assertions**, not a separate reimplementation of the neural network or physics.
Raw historical banks were never saved: the new banks are explicitly regenerated.

Independent NumPy checks validate seals, all3184 paired arrays bit-for-bit across
fresh repeats, exact unchanged inputs and action decoding, declared normalization
and cost reductions, score/argmin rules, physical endpoint arithmetic and counts.
They do not independently regenerate neural outputs or reconstruct hidden physics.
Existing FP32 independent-reduction tolerances were not widened.

Job300966 exposed a checker-only omission of sklearn's coefficient cast to the
input dtype before in-place decoding. Correcting that offline implementation,
not the production decoder, produced job300973's aggregate. See
[decoder correction](PILOT-VERIFIER-CORRECTION-20260914.md).

The reasoning-chat source review then demonstrated additional checker omissions
using synthetic counterexamples. No real pilot corruption was demonstrated by
those examples. Separate source9240097 and job300974 checked:

- Greedy immediate costs from saved predicted first endpoints and raw goal;
  selection still uses the original stored reduction and first-index tie rule.
- Full15/30-action caps unless terminal at the last action; no postterminal steps;
  greedy and selected-prefix flags, success/activity/delivered report fields.
- Exactly four unique anchor rows per process; availability against authenticated
  historical episode lengths; expected evidence for all available anchors.
- Float64, finite, shaped states/goals; state angles in[0,2pi] with only the exact
  endpoint admitted, goal angles strictly[0,2pi); no clipping or normalization.
- Branch and primitive-step reconstruction from trace/prefix lengths plus main
  baseline advancement; historical-model and launch-manifest provenance linkage.

All passed. The initial aggregate was read before this review finished. Those
interpretations were explicitly treated as provisional until the supplement
passed; the supplement changed neither outputs nor findings. This is transparent
post-run validation, not retrospective preregistration.

Receipts (adjacent seals verified remotely, copied hashes matched locally):

| Receipt | SHA256 |
|---|---|
|[Aggregate300973](receipts/PILOT-AGGREGATE-300973.json)|`58c75c57e87a5736e6a9065334beeef57a682e9193153b6c19f2e08b80ff749a`|
|[Supplement300974](receipts/PILOT-SUPPLEMENT-300974.json)|`af7f9b1a67cd95b44d3a46cf1b7312dcf92851e187c63798e18bacd79eb2b2ac`|
|[External pilot backup](receipts/PILOT-BACKUP-VERIFIED.json)|`6f85d09dbd758fa228d8e5c13d005bf0d62456c24faee5734a1570be67bccb6b`|

Supplement manifest: `662b54f7cfa2fbb7015da634dae5a6d3dc69c78560b4455f3854155c79dcb989`.
Current local suite95 passed; supplementary12 passed locally and in pinned
Python3.11.10; corrected decoder verifier7 passed remotely. Prior deployed pilot
suite20 passed per successful execution; these counts refer to different scopes.

## Findings, including unfavorable cases

All conditions share one64-first-action bank. State/latent interventions change
second-proposer conditioning, not the original first-terminal scoring latent.
The lowest-mean-best-two continuation score selects the first chunk; a fixed
minimum-cost second chunk with first-index tie rule is committed. Inactive first
branches retain baseline conditioning and remain selectable without oracle bonus.

| Intervention | First-selection changes /16 | Two-chunk closest-margin better / worse / equal vs baseline | Short successes /16 |
|---|---:|---:|---:|
|State-only|3|8 /3 /5|0|
|Latent-only|5|6 /7 /3|1|
|Joint|6|6 /7 /3|1|
|Baseline|—|—|0|

Lower closest joint margin is better; improvements need not cross the unchanged
success boundary. Greedy64's **first-chunk-only** success was1/16. This is not a
fair15-versus30-action efficacy comparison; the aggregate separates first-chunk
quality from the committed two-chunk consequence.

At ref722/H75/t30,14 of64 first chunks achieved native success. The other15 banks
had zero successful first chunks. Baseline selected first27/second5 and failed
its30-action committed sequence. Latent/joint selected first31 and succeeded
after4 actions: **no second chunk executed**. Its terminal branch retained baseline
inputs; changed costs of other active candidates can still change its rank.
Greedy64 also selected a successful first chunk. Thus a successful action was
present but missed by baseline continuation in this one shared bank. This is
local selection evidence, not distant-goal coverage or a deployable oracle.

Effects are not uniformly favorable. At ref1269/H150/t30, the closest two-chunk
margin was11.3398 baseline,11.3320 state,12.8992 latent,16.8782 joint. At
ref582/H75/t0, latent/joint changed the first selection but worsened the committed
margin. No condition was tuned using these outcomes.

Active-branch adapter normalized-state RMSE ranges0.02015–0.98790; raw latent
RMSE ranges0.11991–0.50172 across anchors. Their units differ: magnitude comparison
does not rank causal bottlenecks. Immediate-cost/physical-first-margin Spearman
ranges−0.1534–0.9836; continuation-score/first-margin ranges−0.6162–0.6561.
Continuation scores target two chunks, not that first-chunk proxy; disagreement
alone is not a scoring defect. Reported marginal interventions may be inconsistent
contexts; retain the joint results and interaction rather than attributing the
whole benchmark gap to a single marginal contrast.

## Measured workload and preservation

Independent counts:2208 branch rollouts,68360 primitive steps including prefixes.
Summed runner wall338.606s (5.643min): starts after model construction and includes
bank compression but precedes final report/seal writing. Mixed CPU/GPU wall time,
not GPU kernel time. Sum of Slurm allocations543s (9.05min), excluding queue wait.
Maximum batch MaxRSS1709436K (~1.63GiB); maximum PyTorch allocated189994496bytes,
which excludes device context/other allocations. No separate GPU-kernel/CPU-time
profiling was performed, so no such timing claim is made.
See the [Slurm accounting record](receipts/PILOT-SLURM-ACCOUNTING-20260914.json).

External backup `D:/THESIS-BACKUPS/bottleneck-20260914/pilot-b1c9633` has all24
files,76764087bytes including seals. Byte-only verifier matched all16 payload
files (76762855bytes) to the authenticated aggregate's canonical seals. No bulk
pilot archive was placed on C:. The separate completed450-shard archive remains
verified; the older375-shard backup and partial directory remain explicitly
incomplete. Model/reference backups are not claimed.

No training, protected payload, unevaluated1600–5999 payload, long-budget tail,
full second-bank physical oracle, SAGE grid or architecture change occurred.
The [32-reference proposal](32-REFERENCE-PROPOSAL-20260914.md) is for review only.
