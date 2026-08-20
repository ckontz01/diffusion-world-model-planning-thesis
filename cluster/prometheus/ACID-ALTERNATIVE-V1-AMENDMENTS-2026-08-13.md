# ACID-alternative v1 implementation amendments

This log applies only to `ACID-ALTERNATIVE-V1-PROTOCOL-2026-08-12.md`.

## AA-001 — task-scoped legacy-contamination scan

Date: 2026-08-13  
Classification: pre-development implementation erratum  
Outcome state: no D1 scorer or D1 closed-loop outcome had been run or inspected

The first PushT manifest job (`296413`) scanned the broad historical `repro`
directory and therefore treated paths explicitly labelled `cube` or `tworoom`
as if their `(episode_id, start_step)` pairs were prior PushT observations.
Those identifiers are local to a dataset, so cross-task numeric collisions are
not evidence of PushT reuse.

The invalidated manifest was preserved at:

`manifests/acid-alternative-v1/pusht-invalidated-job-296413-unfiltered-task-paths`

Its `summary.json` SHA-256 is:

`ead1b162486980063110c6d09f9440645f4849331b83cb866c201c30dbf65c7b`

Before any development run, manifest discovery was changed to support explicit
case-insensitive other-task path exclusions. The PushT invocation now excludes
`cube`, `reacher`, and `tworoom`, records the tokens and skipped-file count, and
continues to include unlabeled historical PushT P2/P3 directories. Job `296416`
produced the corrected manifest. Its `summary.json` SHA-256 is:

`f8ac84d665741cc5c46c5a03a3a89f1669f5b52965c69ffd4559f5d4849c4c17`

The correction changed the unique legacy-pair count from 4,748 to 4,740 and
skipped 11 files. It did **not** change any selected start: the R0, D1, and C1
TSV SHA-256 values remain, respectively:

- `232c71ec2c69c2f130d2506cc8b720448975728f6eb3ad763f648e74df13cd79`
- `948a5e0dc1f79551845a9ef039908729d3d0c4c4bee5deb8445fe465f694814e`
- `1f7bad9e944d583b2610a874d30854db1261c5dce0db458a2116b5ff9b20339d`

The corresponding regression test verifies that a missing optional legacy root
is nonfatal and that paths labelled as another task cannot contaminate the
current task's exclusion set. Cluster test job `296417` passed all nine tests.

## AA-002 — native ACID latent/action coordinates

Date: 2026-08-13  
Classification: pre-development implementation erratum  
Outcome state: no D1 development or confirmatory closed-loop outcome had been
run or inspected

The first implementation standardized frozen encoder latents for every learned
arm and evaluated the ACID action residual in standardized IDM-target
coordinates. The primary ACID source instead specifies frozen encoder latents,
states only that actions are standardized for training, and explicitly says
that actions are de-normalized at inference. Accordingly, A1 now:

- feeds the native frozen Le-WM/PLDM latent coordinates to the IDM;
- retains per-dimension action standardization for flow-matching training;
- de-standardizes the one-step IDM output before computing the residual against
  the candidate in planner-coordinate action space.

D1, F1, and R1 retain their predeclared latent standardization. The frozen
protocol file itself was not modified; its SHA-256 remains:

`57696804f058805efbf830648dcf4fa70f05dc6bec47ad9b4bad92b3fcb27e3c`

The affected source SHA-256 values changed as follows:

| File | Before | After |
|---|---|---|
| `costs.py` | `77a5fb57289792bcc7f1123bc95dc3e66505c5308b8ffdc6ce51ad6bb56f9da4` | `6fb3e08f834967decb8a24beae60ec57b8921032c56b1d31f9e71432ba3b70c6` |
| `train_transition_scorer.py` | `6818b6393e1029cc5fb03683ab802a03437180786a530152cbdabfe13b368c55` | `9fe3c0c413a18680748c71cefc771a7a7efce60768a0d5697f5970548f3647af` |
| `tests/test_models.py` | `1cea89d8f16e1e855bfcfed6bb0766c1f46f5ff273aa38d9e8dcc4f6cf48fbf6` | `792256cdef8fc99d8fb9fc2e969babd705c0c1ebd2336fafe8fd5a836fbd5fba` |

The new regression test asserts both native-latent input and inference-time
action de-standardization. Cluster job `296423` passed all 12 then-current
tests, and the corrected real-stack smoke `296424` completed successfully. The
earlier 50-step job `296422` is classified only as a stack smoke and is
ineligible for any scientific result.

## AA-003 — PushT TRM under-specified reconstruction details

Date: 2026-08-13  
Classification: pre-development outcome-independent reconstruction lock  
Outcome state: no D1 development or confirmatory closed-loop outcome had been
run or inspected

The TRM primary source states that PushT uses a task-state target combining
end-effector position, object position, and wrapped object angle, but it does
not publish the exact scalar expression, pair sampler seed, training duration,
learning-rate schedule, or early-stopping rule. Before running R1, the
reimplementation locks the following choices:

- R1 consumes native frozen-encoder latents; the paper describes encoded state
  pairs and does not specify latent standardization.
- The PushT target is
  `sqrt(||agent_xy_i-agent_xy_j||^2 + ||object_xy_i-object_xy_j||^2 +
  wrap(object_angle_i-object_angle_j)^2)`. Velocity is excluded.
- The 100,000 training and 10,000 validation pairs come from disjoint P1
  train/validation episodes. Pairs are unique; an episode is sampled uniformly,
  then a separation uniformly over `[1,L-1]`, then a valid start uniformly, and
  input order is swapped with probability 0.5.
- Published optimizer settings are retained: two 256-unit SiLU layers,
  Softplus output, label scale 224, Smooth-L1, AdamW LR `1e-3`, weight decay
  `1e-4`, and batch 1024. The unpublished schedule is locked to a constant
  learning rate, maximum 200 epochs, and validation-only early stopping after
  20 epochs without an improvement greater than `1e-8`.
- The shuffled-label null permutes training labels only; validation labels and
  every other setting remain unchanged.

The selected distance is also the most literal wrapped-angle correction of the
released PushT environment's Euclidean state distance: it combines the first
four position coordinates and angle while excluding velocity. These choices
are attributed to this reconstruction, not to the TRM authors.

`costs.py` changed from the AA-002 post-state
`6fb3e08f834967decb8a24beae60ec57b8921032c56b1d31f9e71432ba3b70c6`
to
`bcbbd0b3e115d7540c878d54f7fe29f8db158e1fb24b8a5e2ba7496ace36839d`.
`tests/test_models.py` changed from
`792256cdef8fc99d8fb9fc2e969babd705c0c1ebd2336fafe8fd5a836fbd5fba`
to
`dfaf07cc01a8a14971462c9ee74232d0892d71e059308a990c4dbe7711e3f61c`.

The newly locked sources have SHA-256 values:

- `build_reachability_pairs.py`:
  `0cf1b8b31a36d75a7d9359e1a374ac0efb52139682250f4ca09094554e31e040`
- `train_reachability_head.py`:
  `5db656c8690967e6800a1988204cb429e61e1176b4b62ce8a0a3ee6cacd2070d`
- `run_acid_alt_pusht_reachability_pairs.slurm`:
  `ed3cad965bd8828e4c835f7acf0874a1d4d16424c4507408dcab1fd423a46148`
- `run_acid_alt_pusht_reachability_heads.slurm`:
  `7479b7abfb704cac2edb9fb7037b7073b51a9d67ae068a9a4eb7e683983dc14c`

Cluster job `296428` passed all 14 tests after this lock, including native R1
latent-coordinate and task-state-pair-cache regression tests. Pair-cache job
`296429` and R1 true/shuffled training array `296430` were submitted behind the
fresh latent and transition-cache dependencies.

## AA-004 — immutable source snapshot and pre-result job restart

Date: 2026-08-13  
Classification: pre-development provenance repair  
Outcome state: no D1 scorer or closed-loop outcome had completed or been
inspected

The first full PushT chain referenced the mutable shared `scripts` directory.
Although its code had been tested, a queued Slurm job could therefore import a
later edit rather than the source that existed when it was submitted. The
running latent job `296425` was cancelled after 11 minutes, before producing a
complete latent cache, and its dependent jobs `296426`, `296427`, `296429`,
`296430`, and `296431` were cancelled without running. Their incomplete or
empty job-ID namespaces are retained and ineligible for analysis.

All Python sources were then copied into the read-only cluster snapshot:

`snapshots/acid-alternative-v1-23a24ba9ead5966b`

Its canonical tree SHA-256 is:

`23a24ba9ead5966bd9bf8c29d96f30f16339855f527e709111aaa50190b88c0d`

The snapshot manifest SHA-256 is:

`8b2907103d192848280a18a5536172cd6ed5693fc0649a1000da5e8f549e3b3c`

Every file in that manifest was verified with `sha256sum -c`, the snapshot was
made non-writable, and job `296432` passed all 14 tests directly from it. The
valid restarted data chain is latent job `296433`, transition-cache job
`296434`, TRM-pair job `296436`, core-scorer array `296445`, R1 array `296441`,
and diagnostic-control array `296442`.

A second preflight-only issue was caught by evaluator job `296439`: writing a
source-provenance file into an output directory before invoking a program that
requires the directory to be empty caused an intentional refusal. Provenance
is now staged in job-local temporary storage and moved into the result only
after the program succeeds. Pending arrays `296435`, `296437`, and `296438`
were cancelled before execution and resubmitted with the repair. Evaluator
smoke `296443` then completed on all 50 frozen R0 starts using a deliberately
tiny `4 x 1` CEM budget; its zero successes are not an efficacy result.

The full B0 R0 gate uses the published PushT B0 value of 0.96 and fails unless
the reproduced rate is at least 0.86. A 30-second pre-gate attempt (`296444`)
was cancelled before completion so the summary could explicitly retain the
Slurm ID and enforce this threshold. Full attempt `296446` produced the valid
scientific summary but subsequently encountered the wrapper issue in AA-005.

## AA-005 — B0 wrapper post-check portability restart

Date: 2026-08-13  
Classification: pre-development execution-wrapper repair  
Outcome state: no D1 scorer or D1 closed-loop outcome had completed or been
inspected

Full PushT B0 evaluator job `296446` completed all 50 frozen R0 starts and
wrote a successful summary with 48/50 successes (`0.96`), exactly matching the
published Le-WM PushT value. The Slurm wrapper then exited `127` because the
compute-node host does not provide `jq`; consequently, source provenance and
final checksums were not moved into that result directory and Slurm correctly
did not release its `afterok` dependents. The outcome is retained as an
incomplete wrapper attempt and is not the dependency-authorizing gate.

Before any A1 or D1 evaluation ran, the wrapper-only JSON threshold check was
replaced with Python 3 standard-library parsing, preserving the frozen
`success_rate_fraction >= 0.86` rule. Pending jobs `296448`, `296449`, and
`296450`, whose dependencies could never be satisfied after job `296446`, were
cancelled without execution. A fresh full B0 job and all downstream jobs are
submitted under new IDs: B0 `296451`, A1 array `296452`, R0 aggregate gate
`296453`, and dependency-gated D1 primary array `296454`. No result file is
overwritten.

## AA-006 — Reacher archive extraction portability repair

Date: 2026-08-13  
Classification: benchmark-staging execution repair  
Outcome state: no Reacher evaluation had run

Reacher staging job `296447` verified both the 23.75 GB archive and official
model weights against their frozen SHA-256 values, then failed before
extraction because the compute node's GNU tar 1.30 does not recognize the
newer `--zstd` convenience option. The same node provides `/usr/bin/zstd`.
The staging script now streams `/usr/bin/zstd --decompress --stdout` into tar
for both the path-safety listing and extraction. This changes no dataset,
model, task, or analysis choice. The verified archive is retained, the failed
job is preserved, and new staging job `296455` writes a distinct provenance
record.

## AA-007 — same-candidate mechanism-audit execution lock

Date: 2026-08-13  
Classification: pre-development under-specified diagnostic lock  
Outcome state: no D1 scorer or D1 closed-loop outcome had completed or been
inspected

Section 9 required a frozen same-candidate audit but did not fix its exact pool
or its statistical gate. Before any learned development outcome completed, the
PushT implementation locks the following:

- use all 24 fresh D1 starts and planner seed `7101`;
- capture all 300 candidates in each B0 final CEM population after iteration
  30, not a result-dependent subset;
- assert that the mean of the 30 captured final elites is bitwise equal to the
  action returned by the released CEM implementation;
- roll each frozen population through Le-WM once and make every learned scorer,
  including shuffled/action-ablated controls, consume that exact predicted
  trajectory tensor; private scorer-specific world-model rollouts are zero;
- inverse-transform each candidate exactly as the released policy does and
  physically execute all `24 x 300 = 7,200` action sequences for 25 primitive
  PushT steps from the frozen dataset state and goal;
- encode executed frames at primitive steps `{0, 5, 10, 15, 20, 25}` and
  report raw and standardized predicted-versus-executed latent RMSE, final and
  minimum PushT task-state distance, environment success, same-pool selected
  candidate outcomes, and oracle-best rank;
- define the primary mechanism statistic as within-pool Spearman correlation
  between raw verifier cost and mean standardized successor-latent rollout
  RMSE;
- resample the 24 pool/start identities while retaining all three scorer seeds,
  using 10,000 cluster-bootstrap repetitions and seed `2026081301`;
- require the two-sided 95% lower bound to exceed zero for true D1 correlation,
  true D1 minus shuffled-action D1, and true D1 minus action-ablated D1. An
  undefined correlation caused by cost or outcome collapse fails the relevant
  gate and is reported rather than discarded.

This is a development mechanism diagnostic. It cannot change the frozen C1
primary methods or weights, and its within-B0-pool selected candidate is not
misrepresented as the action found by a separately optimized learned-arm CEM
run. Closed-loop evaluation remains the endpoint for actual optimized plans.

## AA-008 — closed-loop bootstrap implementation lock

Date: 2026-08-13  
Classification: pre-development under-specified analysis lock  
Outcome state: no D1 scorer or D1 closed-loop outcome had completed or been
inspected

Before the five-arm D1 matrix ran, the Section 11 cluster bootstrap was made
executable as follows:

- require the complete `5 arms x 3 paired seeds` matrix for every included
  task; a partial matrix is an error, not missing-at-random data;
- verify identical start identities, manifest hash, dataset hash, and frozen
  world-model checkpoint hash within each task;
- resample start identities independently within each task and retain all
  three paired training/planner-seed outcomes for every sampled start;
- compute each task's mean paired success difference, then use equal task
  weight for the task-stratified pooled estimate even if manifest sizes differ;
- use 100,000 repetitions, D1 bootstrap seed `2026081302`, and a separately
  frozen C1 seed `2026081303`;
- report two-sided percentile 95% intervals for D1-minus-B0 and D1-minus-F1,
  and both two-sided intervals and the one-sided 95% lower bound for
  D1-minus-A1 non-inferiority;
- report an exact two-sided paired discordance test on raw paired
  episode/seed outcomes only as a sensitivity analysis, because it does not
  replace the start-clustered primary interval;
- never silently pool task episodes; every pooled result is accompanied by
  per-task rates and intervals.

The same analysis program may summarize D1, but D1 claim-gate values are
explicitly developmental. Only the locked C1 invocation is confirmatory.

## AA-009 — finite action-statistics parity with released evaluator

Date: 2026-08-13  
Classification: pre-scorer implementation erratum  
Outcome state: no transition cache, learned scorer, or D1 closed-loop outcome
had completed or been inspected

A source audit found that the released evaluator removes action rows containing
NaN values before fitting its `StandardScaler`, while the first transition
cache implementation fitted primitive-action statistics over the unfiltered
HDF5 column. Stable-worldmodel datasets may use a non-finite final-action
sentinel at an episode boundary. Even though valid five-action blocks exclude
the episode's final row, including a sentinel in the global fit would make all
normalization statistics non-finite.

The cache builder now matches the released evaluator: it fits primitive-action
mean and population standard deviation over rows for which every action
dimension is finite, then asserts that every within-episode action block used
for training is finite. It also rejects a dataset with no finite action rows,
non-finite fitted statistics, or a near-zero fitted dimension. Regression tests
cover a final-row NaN sentinel and an all-invalid action column.

The repaired full source snapshot is:

`snapshots/acid-alternative-v1-28ca7d9c0863ceb9`

Its canonical filename-sorted tree SHA-256 is:

`28ca7d9c0863ceb98203c1a6e4c59bff2bc960188f376bed9a5274a2f0777093`

The snapshot manifest SHA-256 is:

`8950d6eb7985bde4dfc805f6e4f7f87e98940ac673943bd47fcf1a894f3b31a6`

All files except `build_transition_cache.py` and its regression-test file are
byte-identical to snapshot `23a24ba9ead5966b`. The already-running frozen
latent extraction is therefore reusable: it reads only pixels and episode
metadata, and its extractor bytes are identical in both manifests. Dependent
cache/training/evaluation jobs from the first chain are ineligible and are
cancelled or allowed to fail without analysis; they are restarted under new
job IDs from the repaired immutable snapshot. No output namespace is reused.

## AA-010 - external confirmation-identification set and C1 execution lock

Date: 2026-08-14  
Classification: pre-confirmation leakage repair and analysis lock  
Outcome state: no C1 closed-loop, I1 scorer, or I1 identification outcome had
been run or inspected

Section 11 requires held-out correct-action identification to support the
diffusion-specific gate. The first executable analysis reused P1 validation
transitions, which are also used for checkpoint selection. Those values are a
useful D1 development diagnostic, but relabelling them as confirmatory would
be leakage. A temporary proposal to split P1 after prior development was also
rejected because a new hash namespace could overlap episodes whose validation
outcomes had already informed implementation work.

The repair leaves the original 90/10 P1 training/validation split byte-for-byte
unchanged and adds a separate identification namespace, I1:

- I1 contains 200 whole P3 episodes per task, selected in ascending order of
  `SHA256(task + NUL + 2026081314 + NUL + I1 + NUL + episode_id)`.
- An episode is ineligible if any recoverable historical result contains any
  `(episode_id, step)` pair from it, or if it supplies any R0, D1, or C1
  evaluation start. Exclusion is therefore episode-level, not merely pair-level.
- The I1 TSV and its contamination-scan summary are both hashed into the C1
  authorization. The summary declares that no I1 outcome has been computed.
- Frozen Le-WM encodings and I1 transitions are generated only after the C1
  primary closed-loop analysis is complete. The I1 cache reuses the released
  primitive-action standardizer and latent/action statistics from P1 training;
  it does not refit any statistic on I1.
- A normal dataset terminal-action NaN sentinel is allowed globally but is
  rejected if it occurs inside any valid five-action I1 transition.
- Scorer checkpoints remain those selected without I1. Identification scores
  are computed for true D1, capacity-matched true F1, and shuffled-action D1,
  for all transitions from all 200 episodes, all three training seeds, and all
  three tasks, with fixed derangement seed `2026081312` and fixed
  evaluation-noise seed base `2026081313`. A transition-count cap is forbidden
  in C1.
- Each result binds task, source snapshot, authorized world-model checkpoint,
  authorized scorer checkpoint, I1 latent/cache hashes, and the C1
  authorization. The analyzer refuses mixed identities or provenance.
- I1 outcomes are produced only after the C1 primary analysis is locked and
  may not alter models, weights, starts, or the primary closed-loop analysis.

P1 validation identification remains explicitly D1-only. I1 is the only input
eligible for the confirmatory correct-action component of gate 3. Local static
checks and the non-GPU integrity suite passed on 2026-08-14 (14 tests); the
complete torch/GPU suite must pass from the new immutable cluster snapshot
before any C1 authorization is created.

## AA-011 - ACID reconstruction-attribution clarification

Date: 2026-08-14  
Classification: pre-development documentation and provenance correction  
Outcome state: no learned D1 scorer, D1 closed-loop outcome, C1 outcome, or I1
outcome had been run or inspected

A line-by-line check against arXiv:2607.02403v1 confirms that the primary source
fixes the four-layer, three-head, width-192 prefix/suffix transformer; the
prefix/suffix attention relation; the `Beta(1.5, 1.0)` flow schedule; task-wise
offline transitions; per-dimension action standardization and inference-time
de-standardization; a 90/10 validation holdout; 200,000 steps; batch size 256;
AdamW with peak learning rate `1e-4`, betas `(0.9, 0.999)`, and weight decay
`1e-4`; a linear-warmup/cosine-decay schedule; and one Euler step for the three
Le-WM tasks. The paper does not specify every implementation degree of freedom.

Accordingly, the following are frozen local reconstruction choices and are not
attributed to ACID's authors: a 1,000-step warm-up; gradient-norm clipping at
1; bf16 autocast on CUDA; validation every 5,000 steps over the first 100,000
deterministically ordered P1-validation transitions; best-validation checkpoint
selection; PyTorch's `TransformerEncoderLayer`; pre-layer normalization; GELU;
MLP expansion ratio 4; zero dropout; a learned three-token position embedding;
one shared biased latent projection for both prefix tokens; biased action and
velocity projections; a final LayerNorm; the standard sinusoidal embedding of
`tau` with maximum period 10,000; and a fixed common Gaussian inference-noise
bank reused across candidates and CEM iterations. The last choice is a
variance-reduction design for matched candidate ranking because the paper does
not state its inference-noise reuse policy.

The released Le-WM planner operates in normalized primitive-action coordinates
and flattens five primitive actions into one model-step action block. This
reimplementation constructs the IDM target in that exact planner coordinate
system, applies the paper's additional per-block training standardization, and
de-standardizes the IDM output back into planner coordinates before computing
the action residual. The R0 reproduction gate remains necessary: failure to
recover the published direction of the ACID gain is reported as a failed
reimplementation, never as evidence against ACID.

## AA-012 - container-bound provenance writers

Date: 2026-08-14  
Classification: pre-submission execution erratum  
Outcome state: no job from the three-task ACID-alternative D1 graph had been
submitted and no result from that graph had been observed

The Python virtual environment used by the study is deliberately constructed
inside the pinned Apptainer image. Its `bin/python` link resolves to
`/opt/conda/bin/python`, which exists inside that image and is not required to
exist on the Prometheus host. A pre-submission resource check exposed two
provenance-only Python invocations that attempted to use this link directly on
the host after their substantive preflight commands had completed.

Both invocations now execute inside the same pinned image with the study root
bound read-write: the diagnostic preflight's gate writer and each task
preflight's gate writer. Their Python bodies, inputs, output schema, hashes,
and pass/fail conditions are unchanged. This correction changes no model,
dataset, seed, hyperparameter, evaluation start, statistic, or claim gate.
The superseded orchestration snapshot was never used to submit the D1 graph.

## AA-013 - physical dataset path correction

Date: 2026-08-14  
Classification: pre-submission execution erratum  
Outcome state: no job from the three-task ACID-alternative D1 graph had been
submitted and no result from that graph had been observed

The frozen registry correctly retained the released evaluator's logical
dataset identifiers, `dmc/reacher_random` and
`ogbench/cube_single_expert`, but initially reused those identifiers as
physical HDF5 paths. Stable-worldmodel resolves those logical names to the
cache-root files `reacher.h5` and `cube_single_expert.h5`; the official
staging scripts use those same filenames.

Only `dataset_relative_path` is corrected for Reacher and Cube. The logical
`dataset_name`, official archive/model revisions and hashes, checkpoints,
partitions, seeds, models, hyperparameters, evaluation starts, statistics,
and claim gates are unchanged. The error was found by a file-existence check
before submission of the D1 graph, so no study output used either incorrect
path.

## AA-014 - I1 source-partition feasibility repair

Date: 2026-08-14  
Classification: pre-scorer data-eligibility erratum  
Outcome state: no task GPU preflight, learned scorer, R0 evaluation, D1
evaluation, C1 evaluation, or I1 outcome had run or been inspected

AA-010 selected 200 episode-disjoint I1 episodes from P3. A preparation-only
contamination scan then established that legacy PushT candidate-pool and
candidate-execution artifacts had already referenced all 1,810 PushT P3
episodes before this study. Consequently, zero PushT P3 episodes were eligible
for a genuinely external identification set. This is a data-availability fact,
not a scorer outcome.

I1 now uses P4 for all three tasks. Each I1 manifest still contains 200 whole
episodes selected in ascending order of
`SHA256(task + NUL + 2026081314 + NUL + I1 + NUL + episode_id)`, after
episode-level exclusion of every recoverable legacy pair and every episode in
the locked R0, D1, and C1 evaluation manifests. The pre-change audit found
1,697 eligible PushT P4 episodes after those exclusions. Using one frozen
source partition across all tasks preserves the matched design; I1 and C1 are
episode-disjoint even though both originate from P4.

All other AA-010 safeguards remain unchanged: I1 statistics are never fitted,
I1 outcomes are generated only after the primary C1 analysis is locked, and
I1 cannot alter any model, weight, start, or primary result. The source
partition is now a task-registry field checked by manifest creation,
preparation verification, and C1 authorization.

The first D1 submission state,
`d1-20260814T144447Z-2705190.tsv`, was cancelled after preparation exposed this
error. Its diagnostic unit-test gate passed, PushT and Cube preparation failed,
and the running Reacher preparation was cancelled; no downstream task
preflight, training, R0, D1, C1, or I1-outcome job ran.

Before resubmission, the cancelled Reacher partial partition/evaluation
directories and an older Cube partition directory whose logical dataset name
was `cube_single_expert` were moved without deletion to the checksummed
quarantine
`manifests/quarantine/acid-alt-preparation-20260814`. PushT's valid master,
P1, R0, D1, and C1 manifests were not rewritten. Reacher and Cube preparation
must recreate their manifests from the frozen rules and pass the same verifier.

## AA-015 - legacy PushT summary-schema compatibility

Date: 2026-08-14  
Classification: pre-scorer metadata-verification erratum  
Outcome state: no task GPU preflight, learned scorer, R0 evaluation, D1
evaluation, C1 evaluation, or I1 outcome had run or been inspected

The preserved PushT master and P1 manifests predate two redundant summary
fields added by the current preparation code: `kind` and, for the master
summary, `dataset_sha256`. Their TSVs deliberately retain 51 P0 episodes that
were observed before partitioning. Regenerating the partition without those
historical P0 inputs would risk returning previously observed episodes to a
study partition.

The verifier now accepts those two metadata keys only when absent. If either
key is present, its value must exactly match the current schema. All substantive
checks remain mandatory: the verifier hashes the current HDF5, checks every
episode identity and length, re-derives every seeded partition and P1 role,
checks P0 reasons, counts and manifest hashes, verifies R0/D1/C1/I1 disjointness
and coordinate rules, and binds the evaluation and I1 summaries to the dataset
and partition hashes. No TSV, episode assignment, evaluation start, or I1
selection was changed by this compatibility repair.

## AA-016 - relative legacy paths and A6000 execution lock

Date: 2026-08-14  
Classification: pre-scorer test-harness and hardware-routing erratum  
Outcome state: no latent extraction, learned scorer, R0 evaluation, D1
evaluation, C1 evaluation, or I1 outcome had run or been inspected

The task GPU preflight runs its temporary directory under a task-labelled path.
The legacy-contamination helper initially matched other-task exclusion tokens
against each file's absolute path, so the Reacher and Cube unit-test fixtures
were both excluded when `reacher` or `cube` appeared in the temporary ancestor.
The helper now matches against the path relative to each supplied legacy root.
An explicit regression fixture places the supplied root under a
`reacher-parent` directory and verifies that only a relative `cube` path is
excluded. Actual contamination remains conservatively episode-level.

Pytest cache creation is also disabled in both immutable preflights because the
snapshots are intentionally read-only. This removes cache warnings without
changing any test or pass/fail condition.

The same preflight exposed that generic `defq` routed GPU work to an RTX A5000.
PushT preflight job 296562 passed there; Reacher 296581 and Cube 296600 stopped
at the path-regression unit test before their wrapper smokes. All 55 downstream
jobs were held before the preflights completed, and submission state
`d1-20260814T151023Z-2722223.tsv` was then cancelled. No task proceeded to
latent extraction, training, or evaluation.

Every frozen Slurm program that requests a GPU, including future C1 and all
latency programs, is now pinned to Prometheus partition `a6000`. CPU-only
preparation and analysis remain on `defq`. This prevents scheduler-dependent
mixing of GPU models and enforces the protocol's same-hardware requirement for
the reported comparison block.

## AA-017 - A6000 QOS routing

Date: 2026-08-14  
Classification: pre-submission scheduler-routing erratum  
Outcome state: the scheduler rejected the A6000-only preflight submission
before creating any job

Prometheus partition `a6000` accepts QOS values `normal-a6000`, `long-a6000`,
and `preemptive-a6000`; it rejects the generic `normal` QOS used by `defq`.
The live account association confirms that `ckontzias`/`superworld` is allowed
to use `normal-a6000`, whose one-day maximum covers every frozen GPU job
(maximum requested wall time: 24 hours). Every A6000 GPU script is therefore
pinned to QOS `normal-a6000`. CPU-only `defq` jobs retain QOS `normal`.

## AA-018 - headless NVIDIA EGL vendor binding

Date: 2026-08-14  
Classification: execution-environment erratum; no scientific setting changed  
Outcome state: all task preparation and GPU preflight gates had passed and the
three frozen P1 latent extractions were running. PushT B0 job 296634 had
completed, but its numerical result had not been inspected. Reacher B0 job
296653 stopped during simulator import before creating an environment or an
evaluation summary. Cube B0 and every not-yet-run Reacher/Cube job that opens a
simulator were held before execution. No learned scorer, A1 R0, D1, mechanism,
or C1 outcome had run or been inspected.

The A6000 node exposes the allocated RTX 6000 Ada, NVIDIA device nodes,
`/dev/dri`, and the host GLVND declaration
`/usr/share/glvnd/egl_vendor.d/10_nvidia.json`. Apptainer `--nv` exposed CUDA
and the driver libraries but did not place that GLVND vendor declaration in the
container. Consequently, `dm_control` could not select NVIDIA EGL and Reacher
B0 terminated with `Cannot initialize a headless EGL display`.

An allocation-local diagnostic reproduced the missing container declaration.
Binding the host declaration read-only at the identical container path made
both automatic EGL device selection and an explicit device-zero import pass.
The repair therefore adds only this read-only bind to every generic Slurm
program that opens a simulator. The task preflight now performs and hashes an
explicit `dm_control` EGL import in addition to its existing unit and released
wrapper smokes, so this infrastructure requirement is checked before any
future simulator evaluation.

The world-model and scorer code, checkpoints, datasets, manifests, candidate
pools, seeds, planner budgets, weights, episode starts, metrics, and claim
gates are unchanged. Replacement Reacher/Cube simulator branches must use a
new immutable orchestration snapshot and new preflight gates. Valid latent,
cache, and scorer jobs from the original D1 submission remain reusable because
they neither import a simulator nor depend on EGL. Original and repair job IDs
are retained in separate checksummed submission-state files.

## AA-019 - official logical dataset aliases

Date: 2026-08-14  
Classification: execution-environment path-resolution erratum; no dataset or
scientific setting changed  
Outcome state: AA-018 Reacher and Cube preflight jobs 296687 and 296699 had
passed, including the new EGL import. Reacher B0 job 296688 then initialized
the simulator successfully, proving the AA-018 repair, but stopped before
dataset construction or evaluation because its official logical dataset path
did not exist. It created no evaluation summary. Cube B0 job 296700 was held
before execution. Reacher and Cube latent extraction and transition/pair cache
construction had completed; no learned scorer, A1 R0, D1, mechanism, or C1
outcome had run or been inspected.

Stable-WorldModel resolves `dmc/reacher_random` as
`data/stablewm/dmc/reacher_random.h5` and `ogbench/cube_single_expert` as
`data/stablewm/ogbench/cube_single_expert.h5`. The verified archives had been
staged as `data/stablewm/reacher.h5` and
`data/stablewm/cube_single_expert.h5`, respectively. The physical paths were
correct for partitioning and latent extraction, but the upstream evaluation
loader uses the official logical name and therefore could not find Reacher.

Read-only logical aliases now resolve to the same already verified files:

- `dmc/reacher_random.h5 -> ../reacher.h5`, size 98,905,882,624 bytes,
  preparation hash
  `85a7dddfa1801302abcb175a80a23bb69c78291dd977ce40d69aedcb9123da06`;
- `ogbench/cube_single_expert.h5 -> ../cube_single_expert.h5`, size
  101,942,558,720 bytes, preparation hash
  `0664d507c4ff12009010644c9ae950836f954e700c172ccf22e7423af1a55625`.

These are symbolic links, not copies; they do not change file content or
allocate a second dataset. Their targets and exact sizes were checked against
the checksummed preparation records before creation. The task preflight now
constructs an upstream `HDF5Dataset` from the official logical name, asserts
that its resolved path equals the declared physical dataset, and hashes this
resolution result into the preflight gate.

The task registry deliberately retains both identities: `dataset_name` is the
official upstream logical name, while `dataset_relative_path` is the physical
staged file. Checkpoints, episode partitions, starts, models, seeds, planner
budgets, weights, metrics, and claim gates are unchanged. A new immutable
orchestration snapshot and replacement Reacher/Cube preflight/B0 linkage must
record the repair; completed non-simulator artifacts remain reusable.

## AA-020 - explicit immutable orchestration-manifest path

Date: 2026-08-15  
Classification: post-D1 orchestration/provenance erratum; no scientific
setting changed  
Outcome state: all scorer training was complete. The PushT and Cube primary D1
matrices had completed, but their efficacy summaries had not been inspected.
Their candidate-capture programs created candidate artifacts and then failed
while constructing the provenance checksum. All PushT and Cube sensitivity
tasks failed before simulator construction. Reacher had not reached D1. No
candidate-score, candidate-execution, mechanism, global sensitivity, global
closed-loop, C1, or I1 outcome had run.

Several D1/C1 diagnostic programs derived the immutable orchestration
manifest as `dirname($0)/SOURCE-MANIFEST.sha256`. Slurm executes a private copy
of each submitted script from `/var/spool/slurmd/job...`, so that expression
does not identify the content-addressed snapshot. Sensitivity jobs stopped at
their required-file check. D1 capture jobs completed the expensive capture
and then stopped when their checksum list referenced the nonexistent spool
manifest.

Affected programs now require an explicit `ORCH_SNAPSHOT` and construct the
manifest path only as `${ORCH_SNAPSHOT}/SOURCE-MANIFEST.sha256`. Both D1 and C1
submitters export that exact immutable path to capture, score, execute,
sensitivity, C1 primary, I1 latent, I1 transition-cache, and C1 identification
jobs. The submission-graph test now makes the scheduler stub reject any of
those programs when the explicit export is absent. Failed job-specific output
directories remain preserved and are never reused; replacement jobs receive
new IDs and new output paths.

This repair changes no source dataset, partition, start, checkpoint, scorer,
candidate budget, seed, lambda, sigma, metric, or gate.

## AA-021 - exact legacy-float32 Reacher action-statistic provenance

Date: 2026-08-15  
Classification: post-training numerical-representation erratum; evaluator
semantics and scientific settings unchanged  
Outcome state: Reacher native-ACID R0 jobs 296718_0 through 296718_2 initialized
the released simulator and dataset, then stopped before CEM planning because
the exact action-standardizer equality guard failed. Reacher D1 and every
downstream Reacher/global job had not run. PushT and Cube primary D1 matrices
had completed, but their efficacy summaries had not been inspected. C1 and I1
outcomes had not run.

The released Reacher HDF5 stores primitive actions as float64. The frozen
transition-cache builder converted the same action column to float32 before
fitting `StandardScaler`, whereas the released evaluator fits the original
HDF5 dtype. Read-only diagnostic job 297048 established all of the following:

- the source action dtype is float64 with shape 2,010,000 by 2;
- cached statistics exactly equal a fresh float32 refit of those same finite
  rows;
- released-versus-cached maximum absolute differences are
  `7.827033461735734e-12` for the mean and
  `1.1183831638561514e-11` for the scale.

The evaluator still uses the released source-dtype standardizer. Its integrity
guard now accepts either exact equality or one narrowly defined compatibility
case: checkpoint statistics must exactly equal a fresh float32 refit of the
same source rows, and both released-versus-checkpoint differences must be no
larger than four float32 epsilons (`4.76837158203125e-7`). Arbitrary nearby
statistics do not pass. The chosen mode, both statistic vectors, exact-match
flags, differences, row counts, source dtype, and envelope are written to the
resolved configuration and evaluation summary. Unit tests cover exact mode,
the legacy mode, rejection of unrelated nearby statistics, and rejection of a
large cast discrepancy.

No scaler is substituted, no checkpoint is edited, and no score, action,
candidate, start, seed, budget, weight, sigma, metric, or claim gate changes.
Because the core source manifest changes, all three D1 primary matrices will
be rerun under one new immutable core snapshot, with new preflights and R0 gate
records, before any global analysis. The already trained scorers remain frozen;
the code change is evaluation-only. C1 remains locked.

## AA-022 - preserve the actual source lineage of frozen validation artifacts

Date: 2026-08-15  
Classification: provenance erratum; diagnostic definition and scientific
settings unchanged  
Outcome state: development-validation job 297087 exited before writing an
analysis summary because the frozen scorer summaries identify core manifest
`3074081ea1ebadd9ef08fef68ce1d81e6b7db656d873ef9d8470690b6fd0c1fc`,
whereas the AA-021 evaluator uses core manifest
`52acea39e4a1f6dadfa5d5be4ec6206a9aefb46159e5def7355a8575f0062f1d`.
The failed job did not alter any scorer artifact. C1 and I1 remained locked.

The frozen P1-validation examples are products of the scorer-training source,
not of the later evaluator-only repair. A recursive comparison of the two
read-only core snapshots found exactly three source-tree differences: the new
`acid_alternative/action_standardization.py`, its new unit test, and the
AA-021 edit to `acid_alternative/evaluate_matched.py`. Every scorer-training
source file is byte-identical. Rather than relabel old training artifacts as
products of the new evaluator snapshot, replacement analysis job 297125 ran
the unchanged validation analysis against the exact manifest recorded by all
input scorer summaries. Its output therefore retains the real training-source
hash. The newer core hash remains attached to every rerun R0 and D1
closed-loop evaluation.

These are two explicit source lineages: frozen scorer training and repaired
closed-loop evaluation. The current single-source C1 authorization path must
not be used to blur that distinction; any later authorization must reconcile
the lineages explicitly or use newly generated, properly attributed training
artifacts. No model, data, seed, comparison, bootstrap, threshold, or claim
gate changes. The result of job 297125 was inspected, so the protocol's
post-D1 rule now forbids outcome-driven method improvement in this study.

## AA-023 - pre-Python Reacher A1 array-launch restart

Date: 2026-08-15  
Classification: outcome-independent scheduler/launcher restart; scientific
settings unchanged  
Outcome state: AA-021 Reacher A1 array job 297064 completed task 0 normally.
Tasks 1 and 2 each exited with status 1 after two seconds, before Python,
simulator construction, CEM planning, or creation of a result directory. Their
logs contain only the cluster accounting epilogue and no Python traceback.
All immutable inputs, both seed-specific checkpoints, and the matching
preflight gate were subsequently verified present. The exact launcher failure
could therefore not be identified from the retained Slurm output.

Replacement array 297111 used the same immutable core and orchestration
snapshots, frozen checkpoints, evaluation starts, planner seed, lambda,
budget, and evaluator command. The sole execution-level mitigation was
`--array=0-2%1`, serializing the three shell/container launches. All three
replacement tasks completed, and gate 297112 passed. The superseded impossible
Reacher downstream jobs and global aggregations were cancelled; their logs and
any artifacts remain preserved. New outputs use new job-specific namespaces.
No failed or successful result directory was overwritten.

## AA-024 - apply the AA-021 action-statistic guard to Reacher diagnostics

Date: 2026-08-15  
Classification: post-D1 diagnostic implementation erratum; diagnostic meaning
and scientific settings unchanged  
Outcome state: the effective three-task D1 closed-loop matrix and its global
analysis, job 297129, had completed and been inspected. Development validation
job 297125 had also been inspected. Reacher candidate capture and realized
candidate execution used the repaired AA-021 evaluator lineage. Candidate-score
job 297115 stopped before writing any score artifact because a diagnostics-only
exact-equality check rejected the already documented float64-versus-legacy-
float32 action-statistic difference. Reacher episode-latency job 297120 was
cancelled before execution because the same guard would fail. C1 and I1 remained
locked and unseen.

The candidate scorer and end-to-end latency programs independently reimplemented
the pre-AA-021 exact action-standardizer comparison. They now load the declared
raw dataset action column and call the centralized AA-021 validator. Acceptance
therefore remains limited to exact equality or to a checkpoint that exactly
equals a fresh float32 refit of the same finite source rows while staying within
four float32 epsilons of the released source-dtype fit. The validator's full
report is recorded in every affected output. No standardizer, checkpoint,
candidate, score equation, noise draw, action, seed, planner setting, timing
scope, statistic, or gate was changed.

Only `score_candidate_pools.py` and `benchmark_episode_latency.py` changed in
the diagnostics source. The repaired immutable snapshots are:

- diagnostics manifest
  `2a55d07d912bf1b6c39f36219c603e3b45c38c3a0a4ccdb475c5bc0d93971614`;
- orchestration manifest
  `4a2083f6b4e44d25e8ca1bc6a63b64fe62cfdd5a0cf69a41cf75451287ca073d`;
- unchanged evaluator-core manifest
  `52acea39e4a1f6dadfa5d5be4ec6206a9aefb46159e5def7355a8575f0062f1d`.

Repaired diagnostic preflight 297161 passed. Replacement Reacher candidate
score 297162, episode latency 297163, and task mechanism audit 297164 completed
with exit code zero. All 24 scorer/control standardization reports in job
297162 record `exact_legacy_float32_refit`, source dtype float64, 2,010,000
source rows, 2,000,000 usable rows, maximum mean difference
`7.827033461735734e-12`, maximum scale difference
`1.1183831638561514e-11`, and the frozen envelope
`4.76837158203125e-7`. Global mechanism analysis 297165 then completed from the
effective PushT, Cube, and repaired Reacher audits. Superseded logs and result
namespaces remain preserved; no prior output was overwritten. C1 remains
locked, and the inspected D1 outcomes cannot be used to tune this v1 method.

Some job-local checksum ledgers also name Slurm's temporary execution copy,
`/var/spool/slurmd/job*/slurm_script`, through `$0`. That path disappears after
job completion even though the stable outputs and read-only submitted snapshot
remain. Finalization therefore adds a provenance-only external ledger that
binds every effective job to its immutable script path and SHA-256 and copies
the stable summaries/checksum ledgers without modifying any scientific result.

## AA-025 - final SSD-backup destination-parent repair

Date: 2026-08-15  
Classification: post-analysis backup/provenance erratum; no scientific source,
artifact, result, or interpretation changed  
Outcome state: all D1 scientific jobs, the four global analyses, the final
result report, and the first read-only final audit were complete. C1 and I1
remained unauthorized and unseen.

The first SSD-backup attempt exited at its first `rsync` call because the
script created `${BACKUP}/workspace` but asked `rsync` to create the
two-level destination `${BACKUP}/workspace/cluster/prometheus`. `rsync` does
not create all missing destination parents in that form. The attempt copied
no file, created only a 36 KiB directory skeleton, and never created a
`BACKUP-MANIFEST.sha256`.

The repair changes the initial `mkdir -p` target to
`${BACKUP}/workspace/cluster/prometheus`. Before retry, the exact incomplete
directory was resolved and verified to be
`/home/chris/thesis-backups/prometheus/acid-alternative-v1/20260815-final`, to
contain only the newly created empty directory skeleton, and to have no backup
manifest. Only that incomplete directory is removed. A new immutable final
audit is generated from the corrected control plane, and that later audit is
the one copied into the completed SSD snapshot.

The first corrected-control-plane upload attempt also stopped before replacing
any file because the prior staging copies had already been set to mode `0444`.
The uploader now temporarily adds owner-write permission only to regular files
directly inside the exact final-control-plane staging directory, replaces the
15 named files, and restores every staged file to `0444` before audit
generation. This staging-permission repair does not touch a source snapshot,
result directory, prior audit, or scientific artifact.

No cluster scientific output is rerun, edited, deleted, or reinterpreted by
this repair. The first sealed audit also remains intact on Prometheus; it is
superseded only as the control-plane record because it contains the faulty
backup helper.
