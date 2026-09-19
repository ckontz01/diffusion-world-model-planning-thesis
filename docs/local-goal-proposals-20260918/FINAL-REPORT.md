# LGP1 completed development result — 19 September 2026

**Diffusion did not establish an advantage over matched GMM in this shared
planner. Retain continuation; promote no model and launch no follow-up.**

All six fixed models, 384 main episodes, eight technical episodes and final
analysis completed. Authentication preceded aggregate access; the complete
historical/current archive was byte/member-verified on the designated external
THESIS_SSD before results were opened. The scientific source and analysis are
unchanged. The final-backup portability correction is documented separately.

## Primary native closed-loop result

| Proposer in the shared planner | H75 | H150 | Both horizons |
| --- | ---: | ---: | ---: |
| GMM | 16/96 (16.667%) | 12/96 (12.500%) | 28/192 (14.583%) |
| Diffusion | 14/96 (14.583%) | 12/96 (12.500%) | 26/192 (13.542%) |
| Diffusion minus GMM | −2.083 pp | 0.000 pp | **−1.042 pp** |

The frozen primary gives equal weight to each of **32 already-exposed source
references**, then both horizons and three seeds within each source. Its
10,000-resample source bootstrap gives a descriptive 95% interval of
**[−7.292, +5.208] percentage points**. This is not a confirmation test, a new
pass/fail gate, or evidence of equivalence. It includes effects favorable to
either family. Seeds, horizons and episode rows are not 384 independent sources.

Across the 192 paired reference/horizon/seed cases: both succeed in 10, only GMM
in 18, only diffusion in 16, and neither in 148. Source-mean differences are
positive on eight sources, negative on seven and zero on 17; their magnitudes,
not a vote over source signs, determine the primary. All 32 effects are in
[FINAL-SOURCE-EFFECTS.md](FINAL-SOURCE-EFFECTS.md), with all 384 endpoint rows in
[FINAL-AGGREGATE-PROJECTION.json](FINAL-AGGREGATE-PROJECTION.json).

### Every fixed seed and horizon

Each cell contains all 32 sources. No seed was selected or omitted.

| Horizon | Seed | GMM successes | Diffusion successes | Difference (pp) |
| ---: | ---: | ---: | ---: | ---: |
| 75 | 8301 | 5/32 | 6/32 | +3.125 |
| 75 | 8302 | 5/32 | 3/32 | −6.250 |
| 75 | 8303 | 6/32 | 5/32 | −3.125 |
| 150 | 8301 | 4/32 | 4/32 | 0.000 |
| 150 | 8302 | 5/32 | 4/32 | −3.125 |
| 150 | 8303 | 3/32 | 4/32 | +3.125 |

## What was actually compared

Two newly trained local-action proposer families received the same information
definition and generated-local-target function within the same fresh-state
planner. They shared LeWM, decoder, support projection, 300 candidates per round,
30 CEM rounds, 30 elites, 15-action chunks, native success predicate and physical
budgets of 150/300 actions for H75/H150. Goals switch to the final goal at the
cycle-final stage; schedule cycles restart without resetting physical budget.

The family-specific training objectives and proposal computation necessarily
differ. Equal rows, width/depth and update counts do not mean equal FLOPs or
optimization difficulty. There is no comparison here against unmodified native
SAGE or the historical continuation planner. Neither reference system was run.
Their earlier results must not be subtracted from these small-population rates.

This remains the distinct LGP1 comparison, not a renamed E14/CVD result. Local
targets are generated separately from the action proposer. Common FP32 CEM,
deterministic ties, action-support projection and episode-owned streams are
declared modifications to native SAGE, unchanged in this run.

## Endpoint and execution evidence

All main rows have no execution failure. Each saved compact episode record
contains start/goal identity, post-action raw state, delivered actions and
native flags. The frozen worker and final analyzer checked the native combined
agent/block position-norm and angle condition at the same post-action step,
excluded t0, and checked action counts, termination and absolute schedule fields.

GMM delivered 41,166 physical actions; diffusion delivered 40,932. All 164 GMM
and 166 diffusion unsuccessful episodes exhausted their full physical budgets.
Successful episodes can end earlier. Two GMM and three diffusion successes
occurred on the final budget step and were retained. No main first-chunk success
occurred; such successes remained valid under the unchanged rule. Full-budget
episode counts, including final-step successes, were 166 and 169 respectively.

Saved terminal flags count 28/26 for GMM/diffusion; truncation flags count 85/85.
These flag counts are not disjoint endpoint categories and do not replace the
native-state verification. The eight technical episodes were separate integration
checks, not extra observations in the primary denominator.

## Supporting measurements, not alternative endpoints

The fixed final checkpoints had the following validation diagnostics on the
same 8,000 rows. Action MSE is measured in the common training-standardized
action coordinates, taking the best of 300 samples against the recorded chunk.
It is sampled offline reconstruction coverage, not an oracle success value.
GMM NLL and diffusion velocity-MSE loss have different meanings and scales.

| Family | Seed | Own-objective validation loss | Best-of-300 action MSE |
| --- | ---: | ---: | ---: |
| GMM | 8301 | −4.190997 | 0.121345 |
| GMM | 8302 | −4.261189 | 0.120524 |
| GMM | 8303 | −4.163330 | 0.120998 |
| Diffusion | 8301 | 0.298400 | 0.101668 |
| Diffusion | 8302 | 0.305818 | 0.102483 |
| Diffusion | 8303 | 0.302150 | 0.103116 |

Diffusion's lower offline action error did **not** translate into better measured
native success. This does not by itself identify the cause: target mismatch,
world-model ranking/refinement, training allocation and the small development
population remain possible limitations, not established explanations.

The following summaries include every actually executed main planning stage.
They are stage/coordinate-weighted diagnostics, **not** the primary source-weighted
comparison. Trajectories and contexts diverge between arms, so predicted-cost
differences are not a paired common-state causal experiment.

| Diagnostic | GMM | Diffusion |
| --- | ---: | ---: |
| Executed planning stages | 2,753 | 2,732 |
| Recorded LeWM cost calls | 82,590 | 81,960 |
| Candidate trajectories scored, including refinements | 24,777,000 | 24,588,000 |
| Predicted primitive steps | 371,655,000 | 368,820,000 |
| Mean initial-bank minimum predicted cost | 50.151 | 48.341 |
| Mean last-population minimum predicted cost | 25.328 | 28.748 |
| Mean initial-bank population standard deviation | 0.75463 | 0.47059 |
| Mean unique candidates per population | 300/300 | 300/300 |
| Pre-projection exceeded coordinates / all scored coordinates | 1,262,475 / 743,310,000 | 360,852 / 737,640,000 |
| Post-projection boundary coordinates | 1,262,484 | 360,855 |
| Median proposal time per stage | 5.308 ms | 29.638 ms |
| Median full planning-stage time | 714.062 ms | 738.600 ms |
| Total physics/action-delivery time | 107.771 s | 107.729 s |

Last-population minima are not the predicted cost of the returned elite mean.
The timing includes actual stages and startup effects; it does not claim matched
FLOPs. Larger diffusion proposal latency is largely diluted by shared CEM cost.

## Actual accounting and preservation

The complete fixed grid has **204 successful coordinates**: one cache, six
fits/validations, four technical jobs, 192 main jobs and one CPU analysis.
There were **207 attempts**, including the three preserved historical failures:
206 GPU allocations and one CPU allocation. Final CPU job **302184** was
`COMPLETED 0:0`; all 192 main jobs 301992–302183 were `COMPLETED 0:0`.
The one scheduled Slurm snapshot reconciled all exact attempt IDs; the final
authentication helper made no additional scheduler request.

| Stage | Successful allocations | Allocation seconds | Summed worker process CPU seconds |
| --- | ---: | ---: | ---: |
| Cache | 1 GPU | 3,388 | 4,572.885 |
| Fit / validation | 6 GPU | 2,169 | 3,142.234 |
| Technical episodes | 4 GPU | 180 | 137.957 |
| Main episodes | 192 GPU | 9,558 | 7,544.625 |
| Preserved failures | 3 GPU | 320 | 284.043 |
| Final analysis | 1 CPU | 16 | 11.014 |

Total GPU charge is **15,615 seconds (4.3375 GPU-hours)** against 336,000;
CPU analysis used **16 allocation-wall seconds** against 7,200, at four CPUs and
8 GiB with no GPU. GPU jobs used one A6000, four CPUs and 24 GiB, serially.
Summed recorded worker process CPU time, including failed attempts, is
15,692.757 seconds; this is not GPU time or allocation-wall time.

Maximum recorded successful-worker RSS was 1,814,249,472 bytes (~1.690 GiB);
maximum recorded GPU tensor allocation was 342,891,520 bytes (~327 MiB).
These are worker measurements, not total device residency or a claim about
unrecorded failed-process peaks. Analysis RSS was 319,614,976 bytes.

There were exactly **72,000 unique optimizer updates / 9,216,000 row presentations**
over the shared 80,000 fitting rows. Validation used 8,000 rows per model.
The first GMM final model had already completed 12,000 updates before its
validation failed; the repair validated those exact bytes with zero retraining.
The later five models contributed 60,000 updates. The current policy recovery
performed **zero cache construction, training or repeated successful validation**.
Rows, windows and repeated presentations are not independent expert sources.

Historical failures remain charged and preserved: 301977 (46 s, recorded-action
support assertion), 301980 (252 s, strict-CUDA cumsum during validation after the
fixed final checkpoint), 301987 (22 s, missing policy seed interface before reset).
Their specific approved corrections and original artifacts remain in the prior
launch/recovery records. No unfavorable scientific result was retried.

The current controller's launch-to-final-terminal-record span was
11,915.973 seconds (3 h 18 min 35.973 s), including orchestration/waits.
Its process CPU/RSS were not captured before exit and are reported unavailable,
not inferred as zero from scheduler `TotalCPU` placeholders.

Post-archive remote usage was **3,466,064,528 bytes / 12,000,000,000**;
preserved worker roots were 1,722,327,813 / 5,900,000,000 bytes and
source/control/logs 9,025,053 / 200,000,000 bytes. Per-pair evidence remains under
20 MB, consistent with the 10 MB per-episode allowance. No storage cap increased.

The external archive is **1,734,420,480 bytes, 1,733 individually verified members**.
Creation and remote member verification took 9.886 s wall / 7.064 s process CPU;
transfer plus local byte/member verification took 56.813 s wall.
It covers all four source/run/control chains, not just the current main outputs:
cache, six models and their original provenance, failed/interrupted artifacts,
approvals, endpoint evidence, reports, accounting, logs and control records.
The new final-copy helper/source/authorization and publication receipts are
preserved separately; the original full archive is never rewritten.

Exact destination:
`D:/THESIS-BACKUPS/local-goal-proposals-20260918/run-b54a55b16bcb83a5/final.tar`.
THESIS_SSD UUID `0a2f1ba9-0000-0000-0000-100000000000` and >40 GB free were
verified before/after copying. No research archive was staged on laptop storage.
Small publication documents remain in the Windows Git checkout by design.

### Immutable identities

| Item | SHA256 |
| --- | --- |
| Scientific source manifest | `b54a55b16bcb83a5092f15703a63fadb81fdbce3fa91f4e6a21b907c934cf361` |
| Unchanged input lock | `b21bac97520696b8bb2008a3cfef3f5188d4c59dd117bc158cc2fe2e86ff5aaa` |
| Uploaded execution approval | `b10ba2f2de17efbb177114a94214023bdebad75c4d158b3aaa78a907fbe50df2` |
| Canonically serialized run approval | `deb7be0968fd8847df0178f19f081062e5b4d8993dfc531f4811456864302dea` |
| Original six-model freeze | `a8a5a0ff456cd870e540f838d2c8b62d00b542be6d7a2da53b377fbd91cbc305` |
| Aggregate seal | `c50cb8c14deedce42b393a968921e39f31e38bd4f4684ededf003c4560967f75` |
| Original aggregate (228,389,096 bytes) | `aabd43c167696c447651bc000925a479abdb3eb9b5425fe77d2fb83f5adb176f` |
| Complete SSD archive | `24609c83f6c21d99edc579229ab990db184c6e0fa1133ebad4336882c35189fd` |

[FINAL-AUTHENTICATION.json](FINAL-AUTHENTICATION.json) records every worker seal,
source/approval binding, original freeze ordering, counts and caps.
[FINAL-ACCOUNTING.json](FINAL-ACCOUNTING.json) and
[FINAL-BACKUP-VERIFIED.json](FINAL-BACKUP-VERIFIED.json) retain the receipts.
The compact JSON is explicitly a projection, not a renamed byte-identical copy
of the original 228 MB aggregate, which is kept unchanged in the archive.

## Finalization checks and boundaries

The original 47-test checkout/export/pinned-runtime evidence and successful
charged CUDA contract checks remain preserved. Four focused final-copy tests
passed in checkout and its separate export. The final publication checks verify
complete-grid, weighting, copied-statistic and accounting consistency only;
they introduce no scientific decision rule. The initial publication formatter
used a nonexistent `launch_unix` key; it was corrected to the actual process
record's `unix` field before any publication output was written.

The bytecode-preservation incident and Windows request-path correction are
fully recorded in [BACKUP-PORTABILITY.md](BACKUP-PORTABILITY.md). Local WSL Python
and a later stat command returned I/O errors; existing cluster computation and
SSH/SSD transfer were unaffected. No environment/permission changes or WSL repair
were attempted during finalization. The three E12 drafts were never opened,
edited, staged or removed; their latest existence recheck could not run because
of that local I/O problem. Prior launch checks remain the last successful check.

No protected payloads, BP1 evaluation data, reserved CVL closed-loop sources or
development references 1600–5999 were accessed. Historical CVL-1 stopping,
original_relative nomination, SI1/E14/E19 decisions and checkpoints remain intact.

## Bounded interpretation and recommendation

This fixed local-goal diffusion training/sampling recipe did not improve the
measured primary over matched GMM on this small exposed population. Better
offline action reconstruction alone is insufficient evidence for a stronger
closed-loop proposer. The wide interval does not establish that diffusion is
generally inferior or that no useful proposal-side mechanism exists.

**Retain continuation and close this bounded run without promoting either new
model or automatically expanding it.** Hand the completed evidence to research
review before deciding whether any different mechanism warrants a separately
specified study. This result does not resolve historical SAGE fidelity, provide
an untouched confirmation result, or by itself establish a publication contribution.
