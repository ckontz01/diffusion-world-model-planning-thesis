# Additional28 and combined32 bottleneck diagnostic — 14 September 2026

Scientific verification and source-matched external backup **passed**. The additional28
supports a repeatable **first-chunk margin-ranking signal**, not a demonstrated
success-rate improvement. Intermediate-context replacement is not a consistent
repair. Historical decision remains `stop_futility_strong_adverse_signal`.

Final read-only RAM accounting is complete. The reasoning-chat handoff is pending;
no further model execution is needed.

## Scope and verification

The four accepted pilot references1269,582,525,722 and their eight original runs
were reused in place, unchanged. The fixed last28 SHA-ordered exposed references
ran twice each in fresh processes:56 new jobs,64 combined runs. Both H75/H150,
anchors0/30, checkpoint7201,64 first candidates,8 second candidates,15-action
chunks, minimum-mean-best-two score, lowest-index ties and the fixed minimum-cost
committed second chunk are unchanged. All128 distinct anchors were available
(112 new,16 pilot). These are32 reference clusters, not128 independent observations
and not64 independent replicates.

All56 new jobs COMPLETED0:0; CPU verifier301071 COMPLETED0:0. The frozen verifier
checked both source manifests, all64 adjacent bundle seals, the original pilot
paths/seals, model identity, historical availability, repeated arrays, exact
decoder arithmetic, normalization, costs/selection, caps/flags, angle domains,
unique coverage and independently reconstructed branch/step counts. All25,472
paired arrays were bit-identical across fresh repeats. All101 synthetic tests
passed in the pinned verifier runtime. No tolerance was changed.

These are independent saved-artifact arithmetic/semantic checks plus the runner's
assertions. They do **not** independently regenerate neural outputs or reconstruct
hidden simulator state. No protected or unevaluated reference payload, training,
new tail policy, SAGE benchmark or historical decision change occurred.

- Frozen source: `265b618`; source manifest:
  `160d0dfc93c32ce578f6aa1fed55b6c615dcf984f60229d44c7fbf2b756abbee`.
- Unchanged [execution contract](EXTENSION-EXECUTION-20260914.md):
  `7ad78113edc32053890bf2ec22dc4f2127aa79cd85bb21c9b893fd17ff74123a`.
- Model-state SHA:
  `f0c666cc011ab057390f7e1571cf3d8bde905d13ff11f1d406f6d3dd8575340d`.
- Run: `/lustreFS/data/superworld/ckontzias/thesis/experiments/diffusion-bottleneck/extension-20260914-265b618`.
- Analysis: `/lustreFS/data/superworld/ckontzias/thesis/experiments/diffusion-bottleneck/extension-analysis-20260914-265b618`.

## Primary descriptive results: additional28 kept separate

Positive margin improvement means baseline closest joint margin minus intervention
closest joint margin; larger is better in this normalized joint-margin quantity,
not pixels, radians or percentage points. Use repeat0 only; average fixed anchors
within each horizon, then weight H75/H150 equally per reference. Both horizons
are required and all32 references meet this requirement.

Intervals are the frozen10,000 reference-bootstrap percentile95% intervals,
seed20260914. They are exploratory development intervals, without multiplicity
control or a confirmation interpretation. A zero-width success interval here
reflects no observed differences in a sparse sample, not proof of equivalence.

|Cohort|Contrast|Mean margin improvement [exploratory95% interval]|Positive/negative/zero references|Mean success difference (pp)|
|---|---|---:|---:|---:|
|combined32|state (30 vs30)|-0.0164 [-0.0568, 0.0238]|17/15/0|0.0000|
|combined32|latent (30 vs30)|0.0082 [-0.1646, 0.1866]|15/17/0|0.0000|
|combined32|joint (30 vs30)|-0.0269 [-0.2155, 0.1677]|12/20/0|0.0000|
|combined32|greedy64 (15 vs15)|0.5652 [0.3769, 0.7533]|29/3/0|0.7813|
|additional28|state (30 vs30)|-0.0348 [-0.0733, 0.0004]|14/14/0|0.0000|
|additional28|latent (30 vs30)|0.0400 [-0.1317, 0.2266]|14/14/0|-0.8929|
|additional28|joint (30 vs30)|0.0326 [-0.1428, 0.2264]|11/17/0|-0.8929|
|additional28|greedy64 (15 vs15)|0.5730 [0.3657, 0.7856]|25/3/0|0.0000|

State/latent/joint comparisons use committed sequences capped at30 actions;
terminal success can stop earlier. **Greedy64 compares first chunks only, capped
at15 actions on both sides.** Its margin advantage must not be presented as a
15-versus30 efficacy win or an equal-compute policy comparison.

The new28 contributes no new success advantage from greedy ranking: both greedy
and baseline first-chunk selection succeed at the same one of112 anchors.
Latent and joint interventions each lose the baseline success at ref70/H75/t30.
Their new-cohort success difference is therefore−0.8929pp after reference weighting.
In combined32, the previously known ref722 gain cancels this new loss.

## Selection, context and adverse cases

|Cohort|Intervention|First-index changes|Two-chunk margin better/worse/equal|Two-chunk successes|
|---|---|---:|---:|---:|
|Combined32 (128 anchors)|Baseline|—|—|3|
|Combined32|State|19|48/45/35|3|
|Combined32|Latent|66|56/55/17|3|
|Combined32|Joint|71|54/57/17|3|
|Additional28 (112 anchors)|Baseline|—|—|3|
|Additional28|State|16|40/42/30|3|
|Additional28|Latent|61|50/48/14|2|
|Additional28|Joint|65|48/50/14|2|

Context interventions change second-proposer conditioning, not the original
predicted first-terminal latent used for scoring. Common second noise is retained.
Inactive first branches keep baseline conditioning and remain selectable without
an oracle bonus. Marginal state/latent interventions can create mixed contexts;
the joint condition is not simply their sum.

For new28, average absolute change in raw second-bank actions is0.002571 state,
0.029659 latent,0.030190 joint. Active adapter normalized-state RMSE ranges
0.012125–0.865210; raw latent RMSE0.121055–0.777281. Combined ranges are
0.012125–0.987904 and0.119911–0.777281 respectively. Different units prevent
ranking causal importance by comparing those magnitudes.

Define descriptive interaction on the per-reference improvement scale as
joint−state−latent. Mean interaction is+0.027422 for new28 (range−0.291239
to+0.327046), versus−0.018736 combined (range−1.008906 to+0.327046).
These interactions and sign changes rule out treating the marginal contrasts as
additive fixes. No interaction hypothesis or threshold was selected after results.

New-cohort mean anchor Spearman correlation with physical first-chunk margin is
0.3651 for predicted immediate cost and0.0587 for continuation score; combined
means0.3777 and0.0544. These are descriptive first-chunk proxies: continuation
targets two chunks, so weaker first-chunk correlation alone is not a scoring bug.

Only3/128 first banks contain any successful15-action candidate:
ref722/H75/t30 (14/64, pilot), ref567/H75/t30 (1/64, new), and
ref706/H75/t30 (1/64, new). New28 therefore has2/112 such banks.
At ref567 both baseline and greedy select the same successful first chunk.
At ref706, neither baseline nor greedy selects the successful candidate:
baseline first margin3.6035, greedy1.8906, bank best0.9764. Better margin
does not necessarily reach success. The ref722 counterexample remains valid
but did not generalize into a new success advantage.

Adverse evidence is retained: new ref432 has state/latent/joint reference-average
improvements−0.2825/−0.9656/−0.9531; greedy worsens ref860 by−0.8195.
The pilot's ref1269 joint effect remains−1.2000. Conversely new ref867 latent
improves+1.2546 and ref98 joint improves+1.3757 without new success gains.

## Every reference's effect magnitude

All rows average four available anchors through equal H75/H150 weighting.
Success columns are ordered state/latent/joint/greedy, in percentage points.
The first four rows are preserved pilot references; all remaining rows are the
explicit additional28. Full-precision per-horizon values, medians, ranges and
intervals are in the authenticated combined JSON.

|Reference|State margin|Latent margin|Joint margin|Greedy first-only margin|Success differences S/L/J/G (pp)|
|---|---:|---:|---:|---:|---|
|1269 (pilot)|-0.0177|-0.1734|-1.2000|0.9890|0 / 0 / 0 / 0|
|582 (pilot)|0.3238|-0.9702|-0.8670|0.3944|0 / 0 / 0 / 0|
|525 (pilot)|0.0098|-0.2737|-0.2456|0.2743|0 / 0 / 0 / 0|
|722 (pilot)|0.1348|0.5600|0.5388|0.3819|0 / 25 / 25 / 25|
|567|-0.0509|0.0326|-0.3095|0.7212|0 / 0 / 0 / 0|
|716|0.0056|-0.6564|-0.6295|1.2657|0 / 0 / 0 / 0|
|630|0.0136|-0.5342|-0.4772|0.7485|0 / 0 / 0 / 0|
|1066|0.0079|-0.1064|-0.1022|0.0393|0 / 0 / 0 / 0|
|1074|-0.0901|-0.1336|-0.1328|0.1685|0 / 0 / 0 / 0|
|1565|0.0167|-0.2816|-0.2802|0.3908|0 / 0 / 0 / 0|
|70|-0.1869|-0.1826|-0.1349|0.1618|0 / -25 / -25 / 0|
|867|-0.0446|1.2546|1.2067|0.9075|0 / 0 / 0 / 0|
|221|0.0578|-0.3247|-0.3438|0.7517|0 / 0 / 0 / 0|
|905|0.0355|0.1748|0.1800|0.3737|0 / 0 / 0 / 0|
|1287|-0.2833|0.1366|0.1124|1.3348|0 / 0 / 0 / 0|
|621|0.0238|0.0094|0.0546|0.2618|0 / 0 / 0 / 0|
|428|-0.0598|0.8155|0.7952|1.0606|0 / 0 / 0 / 0|
|288|0.0945|0.1746|0.2629|1.0230|0 / 0 / 0 / 0|
|1488|0.1059|0.3184|0.2625|0.9746|0 / 0 / 0 / 0|
|757|-0.0133|-0.6084|-0.6089|-0.0897|0 / 0 / 0 / 0|
|641|-0.0960|-0.0862|-0.0759|0.4444|0 / 0 / 0 / 0|
|855|-0.0136|0.1338|-0.0051|0.3578|0 / 0 / 0 / 0|
|1280|0.0408|-0.0638|-0.0481|0.7163|0 / 0 / 0 / 0|
|420|-0.1578|-0.0970|-0.0927|0.0438|0 / 0 / 0 / 0|
|860|-0.1915|-0.2714|-0.2654|-0.8195|0 / 0 / 0 / 0|
|98|-0.0483|1.0969|1.3757|0.2490|0 / 0 / 0 / 0|
|886|0.0350|0.6545|0.5707|1.8393|0 / 0 / 0 / 0|
|432|-0.2825|-0.9656|-0.9531|0.2852|0 / 0 / 0 / 0|
|181|0.0452|-0.0911|-0.0892|-0.0127|0 / 0 / 0 / 0|
|783|0.0518|0.0133|-0.0031|0.6018|0 / 0 / 0 / 0|
|706|-0.0011|0.2465|0.1927|1.8449|0 / 0 / 0 / 0|
|989|0.0111|0.4608|0.4513|0.4015|0 / 0 / 0 / 0|

## Actual resource accounting and preservation

|Quantity|Additional28|Combined32 / other scope|
|---|---:|---:|
|Successful GPU jobs|56|64 including8 original pilot|
|Successful GPU allocation seconds|3941|4484 including543 pilot|
|Charged extension allocation including failed packaging11s|3952|65.867min of120min cap|
|Runner wall seconds (different timing boundary)|2382.883|2721.489|
|Physical branch rollouts|15456|17664|
|Primitive physics steps including replay/prefix accounting|480362|548722|
|Maximum PyTorch allocated GPU bytes|189994496|Allocator peak, **not total VRAM**|
|Maximum reported PyTorch reserved GPU bytes|201326592|Allocator reservation, **not total VRAM**|
|Maximum Slurm batch-step resident RAM|1686004K (1.607899GiB)|Job301023.batch; all56 batch records present|
|CPU package preflight301009|5 allocation seconds|2CPUs/4GB request|
|CPU combined verifier301071|44 allocation seconds|2CPUs/4GB request; MaxRSS89080K|

Every simulation allocation requested one A6000,4CPUs,24GB RAM and5min maximum.
Additional successful requested CPU allocation is15,764 CPU-seconds (4×3941),
not measured CPU busy time. The prior11-second packaging failure is separately
charged; CPU preflight/analyzer cost is separate from the GPU budget. Queue time
is excluded. Runner timing excludes parts of process setup and teardown; it is
not substituted for Slurm allocation. Total device memory was not measured.
The [read-only Slurm accounting receipt](receipts/EXTENSION-SLURM-ACCOUNTING-20260914.json)
retains all queried rows and independently confirms56 successful jobs and3941s.
Batch-step MaxRSS ranges1645580K–1686004K, interpreting K/M as binary units.
This is Slurm-reported resident RAM, not GPU memory, total node RAM or summed
concurrent usage; sampling can miss instantaneous peaks. Blank allocation-level
MaxRSS fields are not treated as zero. No jobs were rerun for accounting.

Completion ledger size was540,242,493bytes, below1,000,000,000. Final copied run
directory is540,243,437bytes across338 files; the944-byte difference is the
completion JSON written after the ledger's measurement. New payload files total
537,698,162bytes; copied metadata/logs/seals account for the remainder.
The separately copied analysis directory (including backup receipt) is599,646bytes.
The1GB limit is a monitored fail-stop watermark, not a filesystem quota; no
watermark stop or budget reservation failure occurred.

Source-matched backup verified all56 new bundles and all8 original pilot bundles:
`D:/THESIS-BACKUPS/bottleneck-20260914/extension-265b618` and
`D:/THESIS-BACKUPS/bottleneck-20260914/pilot-b1c9633`.
The original pilot payload totals76,762,855bytes (seals excluded).
All338 new run files, including dispatcher metadata and logs, were transported;
the byte-only verifier specifically authenticates the56 scientific bundles,
not every log byte against an independent remote receipt. No bulk C: copy.
The complete historical450-shard archive and older incomplete375-shard copy
remain preserved; model/reference backups are not newly claimed.

Two pre-scientific infrastructure attempts are preserved: the Python3.6 dispatch
compatibility failure submitted no job;301003 spent11seconds failing pre-run
package tests before model execution. Both missing existing helpers were included
in the corrected freeze. The later SSD disconnection interrupted local SSH, but
the original remote dispatcher survived; no job was restarted or duplicated.
See [launch history](EXTENSION-LAUNCH-20260914.md).

|Authenticated receipt|SHA256|
|---|---|
|[Combined301071](receipts/EXTENSION-COMBINED-301071.json)|`820f027f7313c4179d95f99e5eda54d2172469eb4a3cd8541883aa5f8a0e0a54`|
|[Decoder301071](receipts/EXTENSION-DECODER-301071.json)|`334dca60b952d1fb8436e3c9af009f2159dd863e5d402e15f917cb6da55a8a21`|
|[External backup](receipts/EXTENSION-BACKUP-VERIFIED.json)|`d4254707162e536c81aaa730680207e790517c93a314661610b53ab2fff92b63`|

## One recommended next mechanism experiment — proposed only

**A paired, same-bank first-ranking ablation with a common continuation/replanning
policy and equal charged compute.** Freeze this separately on the same exposed32
references; do not consume new or confirmation references. Compare immediate
first-endpoint ranking with the unchanged continuation ranking, keeping the first
candidate bank, model/checkpoint, initial state, common RNG and delivered budget
identical. Evaluate both rankers from the same bank in both arms and retain the
same continuation-generation workload, discarding the unused decision, so ranking
rather than compute allocation is the intervention. Deliver the selected15-action
chunk, then use the same unchanged downstream policy and termination rules.
Prespecify first-chunk and subsequent common-policy outcomes as distinct endpoints,
paired by reference with equal horizons; do not tune a hybrid weight or new tail.

Rationale: the new28 repeats the immediate-ranking margin signal (25/28 references)
more clearly than the mixed context interventions. The next question is whether
that margin advantage survives actual common downstream execution or merely trades
away later opportunity. Sparse success coverage and the ref706 miss mean a
stronger-planner conclusion is premature. The rank-only test targets this question;
it does not assume immediate ranking is globally superior or that diffusion
architecture is the bottleneck. This recommendation is **not launched or frozen**.
