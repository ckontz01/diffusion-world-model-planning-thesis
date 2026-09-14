# Approved additional-28 execution contract — frozen before launch

User authorized the exact additional28 extension after accepting the four-reference
pilot. Preserve and reuse all eight completed pilot processes, bytes and source.
Historical stopping decision remains `stop_futility_strong_adverse_signal`.

## Scientific invariants

The fixed32 identifier ordering in BRANCH-PILOT-SELECTION.json is unchanged.
New references are its last28, each two fresh processes:56 jobs, indices8–63.
The first four/eight processes are never resubmitted. Both H75/H150, checkpoint7201,
anchors0/30,64 first candidates,8 second candidates,15-action chunks, best-two
score, lowest-index ties, fixed minimum-cost committed second chunk, normalization,
decoder, common noise, R3 initialization, prefix replay and all terminal/budget
rules are unchanged. No new tail policy. Unavailable anchors are not replaced.

The extension runner is a separately named exact copy of the accepted runner
with only its reference tuple and identifier-prefix length changed. A regression
checks the entire text against those two substitutions. The original runner and
all immutable snapshots remain unchanged. This is development, not confirmation.

## Dispatch, cost, storage, failures

One A6000 allocation at a time; account superworld, a6000/normal-a6000,4CPUs,
24GB RAM,one GPU,5-minute wall limit/job. Submit the next fixed job only after
the prior one is COMPLETED0:0. No automatic retries, replacements or new cases.

The additional56 jobs have a7200-second aggregate allocation ceiling, excluding
the already spent543 pilot seconds and excluding queue wait. Before every dispatch,
reserve the full300-second next-job cap against the measured completed Slurm
ElapsedRaw sum. Stop rather than submit if the reservation cannot fit. Ambiguous
submission/accounting or nonzero/failed terminal state stops dispatch for diagnosis.
Controller interruptions do not auto-resubmit; inspect the preserved ledger and
exact possibly active job before deciding recovery. No unrelated jobs are changed.

New run-root regular-file storage watermark1,000,000,000bytes, including logs,
temporary files and outputs. Require64,000,000bytes headroom before dispatch.
Each worker has a16MiB per-file write limit. Controller checks sizes every15seconds;
crossing the watermark cancels only its current job and stops dispatch. This is a
monitored fail-stop watermark, not a filesystem quota: sampling can overshoot
transiently, which must be reported, not hidden. No permissions/quota changes.
External backup is a separate replica; reserve at least2GB free on healthy D:.
No new bulk data on C:. Source trees and final compact reports are outside this
run-root watermark; report their sizes separately if material.

The controller performs only lightweight scheduler and file-size operations on
the login node. Models/physics run in the existing pinned Apptainer environment
on Slurm. Logs and outputs stay preserved; no automatic deletion or compression
that changes existing records. Stop on a material execution defect, not weak
scientific results.

## Information and verification boundary

Until all56 new jobs complete successfully, inspect only scheduling, exit codes,
existence, byte counts and checksums of new scientific output. On exact failure,
report its job/reference first, then read only that failed execution's technical
logs. No partial-effect-based stopping or tuning. Cost/storage dispatch does not
use outcomes. After completion, verify all64 bundles' seals before arrays.

Create a combined read-only view linking the four original and28 new directories;
check that original symlinks resolve to the exact pilot paths and match the
authenticated pilot aggregate seals. Never copy over or regenerate pilot files.
Run the decoder-corrected independent reducer and repeat-array comparisons, then
the accepted supplementary helpers on every bundle: greedy costs, flags/caps,
angle/shape domains, historical availability, unique coverage and reconstructed
counts. Tie each cohort to its actual runner/source manifest and each model hash
to authenticated historical result files. Preserve a failed decoder aggregate if
a later supplementary stage fails; do not interpret it as completed acceptance.
Write new sealed combined reports. No independent neural/hidden-physics claim.

## Reporting frozen before extension outcomes

Return combined32, explicitly additional28, and reused pilot4 cohort summaries.
Use repeat0 only for effect estimation; repeat1 checks exact reproducibility.
Within each reference, average available fixed anchors within each horizon and
weight H75/H150 equally. Require both horizons for an effect; retain missingness
counts rather than silently imputing or replacing. For state/latent/joint versus
baseline report paired committed-two-chunk margin improvements and success
differences. For greedy64 compare ONLY matched first-chunk endpoints against
baseline-selected first chunks, not15-versus30 efficacy. Positive margin improvement
means baseline margin minus intervention margin. Report every reference's effect,
means/medians/ranges and positive/negative/zero counts. Fixed10,000 reference
bootstrap resamples (NumPy seed20260914), percentile95% intervals, exploratory
only. Do not count anchors, horizons or repeats as independent references.

Keep active-state/latent errors in their own units, candidate selection changes,
the joint interaction, unfavorable effects, and the distinction between one-bank
short-horizon success and distant-goal coverage. Use actual Slurm accounting,
runner wall boundary, allocator-vs-total-memory caveat, sizes and reconstructed
physics counts. Recommend exactly one next mechanism experiment based on these
results, but do not launch it, training, SAGE, a tail policy or a larger grid.
All payload access remains within already exposed0–1599; no protected outcomes.
