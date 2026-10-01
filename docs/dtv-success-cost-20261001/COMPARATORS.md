# Frozen comparator and source identities

`BINDINGS.json` is the complete machine-readable authority target: all 2,880 worker IDs and orders, all cohort rows, 27 exact scorer checkpoint paths/hashes/configurations/parameter counts, three world checkpoints, recovered decoders, runtime hashes, and finite reservations. `COHORT.json` and `ROLE-RECONCILIATION.json` bind role/parent identity independently of later reference names.

| Configuration pair | Delegated callable | Weight / noise | Return |
|---|---|---|---|
| dtv30, dtv28 | v1 `SharedRolloutCostModel`, via accepted `make_wrapper(..., d1_sigma025)` | .07 / single fresh sigma .25 bank, original epsilon predictor | final elite mean |
| acid30, acid28 | accepted v3 `D2CostModel(arm=acid)` and `acid_literal_costs` | .07 / exact `acid_noise_seed(task, scorer_seed, planner_seed, call_index)` | final elite mean |
| forward30, forward28 | accepted v3 `D2CostModel(arm=forward)` | .005 / deterministic | final elite mean |
| plain30, plain28 | accepted v3 `D2CostModel(arm=b0)` goal rollout | no learned checker | final elite mean |

Every point uses the released 300-sample / 30-elite `CEMSolver`, changing only its declared 28 or 30 scored populations. Plain proposals differ across the three fixed planner seeds, so these are not redundant model-independent repetitions of one deterministic baseline; no result is counted as an independent source three times.

Historical scientific closures are `acid-alternative-core-v1-52acea39e4a1f6da` (manifest `52acea39e4a1f6dadfa5d5be4ec6206a9aefb46159e5def7355a8575f0062f1d`) and `acid-alt-v3-d2-2c8f890c31e9f5bf` (manifest `2c8f890c31e9f5bf5e8b6769ccc424d7cd565278c422405d507d1c702d3580ea`). Every member is checked before importing its scientific implementation. They are not edited.

Runtime is the authenticated Python 3.11.10 / Torch 2.5.1+cu121 / stable-worldmodel 0.0.6 environment and exact retained container `589af9b428527ae2d315fbd5eaf7ef991efb1aa7249e30a6d28e6731df40afb2`. `gpu09` and `gpu09.cluster` are the accepted hostname association; job name, allocation ID, Slurm node and exact single-GPU hardware checks remain strict. Additional native initializer dependency text was authenticated without instantiating physics.

Do not substitute the old three-noise .005 configuration for DTV, slice its middle noise bank, substitute D1's older .07 forward setting, or import later ACV horizons. No checkpoint is refitted, reselected, distilled or compiled. The single-level bank has shape `(1,5,latent_dim)` and is constructed as that shape with its private original seed.

DTV-EFF0's single-noise complete saved-input solve savings of approximately 4.2203–6.7165%, legacy range approximately -.5286–2.3261%, and failed 10% screen remain historical timing evidence, not new closed-loop success/cost results. Its boundary excluded raw observation processing, physical action decoding and physics. It is not labeled observation-to-action latency here.

Model fitting costs are inherited, not zero. `PLANNING-EVIDENCE.json` retains all 27 exposed training summaries with provenance hashes and reported process elapsed times. These are not independently reconciled Slurm training allocations, energy measurements, or timing of the new study. Unknown allocation/training components remain null, not zero. No training is run to fill a missing cost.
