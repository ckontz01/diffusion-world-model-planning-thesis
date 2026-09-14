# Complete saved-trajectory reduction

Outcome-informed development only. Historical decision remains
`stop_futility_strong_adverse_signal`. No planner rerun supplied these results.

Job300963 completed0:0 in11m10s on the pinned Python3.11.10 runtime. Its64
synthetic tests passed before canonical preservation, paired bootstrap,
independent outcome reaggregation and full trajectory reduction. All adjacent
seals passed before report interpretation. Sourcec567ccf; source manifest
689e559a85e60afdc65abc95e2f4d3782395a45127f47d283847b02253f835b0.
Full reportSHA256
dc4872e59bf4069fb07b3aed4cb8bc3e3dc1128975a7025aeb3cf5fc800c1fb6.

All450 shards and57600 unique reference/horizon/seed/arm runs passed hash,
action, initial-request, goal, planner-seed and recorded-success checks.
Every36 arm/horizon/seed block contains1600 records. Independent scalar
squared-position/modular-angle checks agree with recorded outcomes. There are
zero technical-invalid records and zero planner exceptions. Initial t0 is
excluded. No unevaluated-reference payload or protected metric was accessed.
The exact2pi admission correction and preserved failedjob300959 are documented
in ANGLE-GUARD-20260914.md, not silently treated as a historical change.

## Terminal categories

Each row is4800 paired measurements, not4800 independent references. Success
means the historical joint four-coordinate position norm<20 AND angle<pi/9
at the same post-action step. Other columns are mutually exclusive terminal
categories; supplementary component diagnostics do not replace this endpoint.

| Arm | H | Success | Position-only miss | Angle-only miss | Both miss |
|---|---:|---:|---:|---:|---:|
| VAD continuation |75|1017|1337|34|2412|
| VAD continuation |150|548|955|24|3273|
| VAD greedy300 |75|986|1236|32|2546|
| VAD greedy300 |150|367|949|16|3468|
| Gaussian continuation |75|837|1280|29|2654|
| Gaussian continuation |150|446|948|10|3396|
| VAD greedy576 |75|1029|1177|25|2569|
| VAD greedy576 |150|423|946|10|3421|
| GMM continuation |75|930|1292|15|2563|
| GMM continuation |150|539|918|14|3329|
| SAGE |75|1271|1237|40|2252|
| SAGE |150|749|983|28|3040|

VAD continuation's8035 failures comprise5685 both-misses,2292 joint-position-
only misses and58 angle-only misses. Thus terminal angular misalignment alone
does not describe most failures. This does not identify an adapter, proposer,
world-model or ranking cause. In1082 failed VAD-continuation measurements,
block pose was within the supplementary component thresholds at some time
without satisfying the full joint endpoint; that is not an alternative success.

Native truncation is recorded separately and can coincide with success at the
last step. AtH150 VAD continuation has4257 truncation flags,4252 without
success; SAGE has4052 flags,4051 without success. H75 ends at its150-action
driver budget before the300-step environment cap. These are not planner errors.
The machine-readable report preserves these counts for every arm/seed block.

## Timing boundaries

| Arm | H75 median episode-loop seconds | H150 median episode-loop seconds |
|---|---:|---:|
| VAD continuation |1.6622|3.4442|
| VAD greedy300 |1.2133|2.4313|
| Gaussian continuation |1.1971|2.4612|
| VAD greedy576 |1.2140|2.4329|
| GMM continuation |1.1975|2.4617|
| SAGE |10.5264|21.0934|

Episode-loop timing excludes initialization; solver-call timing excludes some
surrounding preprocessing. Median solver calls are about129.6/129.7ms for VAD
continuation and963.7/964.0ms for SAGE atH75/H150. Different success/termination
patterns affect episode workload. None of these ratios is a complete deployment
latency or equal-budget superiority result.

## Paired outcomes and interpretation

All15 pairwise contingency tables and20 exploratory contrasts/cluster standard
errors passed independent standard-library reaggregation in the pinned runtime.
Both horizons and all three fixed blocks remain inside each reference cluster.
The10,000-resample intervals remain post-result exploratory, not new sequentially
adjusted confirmation. The substantive findings in PAIRED-RESULT.md are unchanged:
VAD continuation minus greedy300 +2.2083pp, Gaussian +2.9375pp, GMM +1.0000pp,
greedy576 +1.1771pp, and SAGE -4.7396pp. The H150 GMM contrast is only+0.1875pp.
The between-policy VAD/SAGE union30.25% is a privileged whole-policy oracle,
not evidence of successful actions inside one shared candidate bank.

Next: the separately specified four-reference same-bank intervention pilot.
Do not select a redesign or claim a causal explanation from these categories.
