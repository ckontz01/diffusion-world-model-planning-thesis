# CVL-BP1 count, cost and storage envelope

Preparation estimate, not measurements of a new run. All new real execution
requires approval of the exact protocol and immutable source manifest.

## 1. Outcomes, candidates, sources and unavailable anchors

| New component | Distinct sources | Ref×H jobs | Nominal new bank-index rows | Draws per row | Maximum new outcomes |
|---|---:|---:|---:|---:|---:|
| B additional training |96|192|6,144|2|12,288|
| C additional precision |96 existing|192|0 (same original rows)|2 extra|12,288|
| Common new evaluation |32|64|2,048|4|8,192|
| Total |128 new +96 existing|448|8,192 new|—|**32,768**|

Independent factorization: B/C each96×2H×4slots×8indices×2newdraws;
evaluation32×2×4×8×4. A collects **zero** new labels. Nominal B/C data increments
are matched in outcomes, not independent sources or unique action chunks.
Original A has709 live banks,5,672 sampled index rows and11,344 outcomes.
Its59 unavailable slots remain unavailable in C, fixing C's actual increment
at **11,344** and C's total at22,688. B's total is at most23,632 including A.
The known-adjusted new-outcome ceiling is therefore **31,824**, before new B/E
unavailability. Do not fill the difference with new cases or extra draws.

Original C final-budget banks:157. Their157×8×2=2,512 extra outcome records
carry **zero additional stochastic-tail evidence**. Original A/C have96
independent analysis source units, B192, common evaluation32; never count draws,
horizons, model seeds or candidate rows as additional independent sources.

## 2. Physical-work bound (including prefix replays)

Each branch starts from fresh initialization and replays its original prefix;
no simulator snapshot/restore shortcut is introduced. A max-length branch is2H
steps, not merely the post-anchor remainder. For each new source/H, one standalone
prefix captures the anchor banks; C reuses saved prefixes and has no extra one.

| Stage | Standalone prefixes | Maximum physical steps | Of these, post-anchor branch steps |
|---|---:|---:|---:|
| Breadth |192|2,808,000|1,681,920|
| Precision |0|2,764,800|1,681,920|
| Evaluation |64|1,857,600|1,121,280|
| Total |256|**7,430,400**|4,485,120|

Bounds use96×(64+1)×450,96×64×450 and32×(128+1)×450. The summed
post-anchor remaining budgets over the two horizons/four slots are1,095 steps
per candidate/draw/source. Prefix replay adds2,887,680 steps, plus57,600 standalone
prefix steps. Native early termination and unavailability reduce work, not
change the registered grid. A completed subepisode is not necessarily a distinct
source or a full-length episode.

At most495,360 solver calls:429,312 full continuation calls and66,048
cycle-final first-only calls. This is924,672 proposal batches /9,246,720
diffusion forward iterations under the unchanged ten-step proposer. These are
analytical upper bounds, not new inference measurements. Actual traces/call
ledgers retain steps, solve times and available-bank counts.

## 3. One bounded staged envelope

| Allocation | Fixed jobs | Limit per job | Total reserved |
|---|---:|---:|---:|
| A6000 breadth |192|600s,4CPU,24GiB|32h|
| A6000 precision |192|600s,4CPU,24GiB|32h|
| A6000 evaluation |64|1,200s,4CPU,24GiB|21h20m|
| CPU all18 fits + training diagnostics/freeze |1|5,400s,4CPU,8GiB|1h30m|
| CPU common analysis/report |1|1,800s,4CPU,8GiB|30m|

Single concurrent GPU job. **448 GPU jobs +2CPU jobs =450 allocations.**
GPU reservations sum85h20m, within the proposed **86 GPU-allocation-hour** cap;
the remaining40m is not permission for extra cases/retries. CPU cap is **two
allocation-wall-hours at4CPUs** (at most8CPU core-hours), not two aggregate
CPU-core-hours. Associated GPU-job CPUs are charged in their GPU allocation;
they are not free or hidden CPU-only training allocations.

Limits include initialization, runtime/source authentication, proposal/LeWM
calls, simulator work, trace writing, technical verification, failed work and
scheduler-recorded allocation overhead. CPU stages include saved-data reads,
preprocessing, all18 fits, prediction/reporting and sealing. No separate real
preflight, new diagnostic, closed loop, extra model fit, backup GPU job or
historical-controller restart is budgeted. File transfer/backup and lightweight
controller execution use no Slurm/GPU allocation; their wall time and bytes are
reported separately, not misrepresented as zero total elapsed time. No monetary
price is asserted without a verified billing tariff.

### Included initial tranche and stop controls

The first four breadth and four precision sources, both H, are16 registered
jobs inside the above counts. They are fixed by the ID ordering, not outcomes.
Proceed only if the ordinary technical checks pass, observed RSS≤16GiB, and
conservative full-run projections fit. Projection: twice the slowest observed
allocation for each H, multiplied by256 source-equivalent jobs for that H
(96B+96C+64E-equivalent because E has twice the draws). Storage projection:
worst included job bytes×512≤8GB. These are explicit conservative feasibility
checks, not claim-based scientific advancement gates. Reject a projection that
does not fit; do not adjust cases, sampling, time limits or resource caps.

Before every submission, reserve the **entire fixed remaining workload** within
the total GPU/CPU limits. Debit terminal `ElapsedRaw` even on failure; retain a
full per-job reservation for cancelled/ambiguous/nonterminal accounting until
reconciled. No automatic resubmission. A technical or controller stop preserves
partial files and cancels a known live job. Terminal-state reconciliation and
failure-artifact sealing/backup precede any later user-approved recovery. A
source mismatch, changed C bank or missing required artifact is not scientific
permission to substitute another source or bank.

## 4. Planning scenarios

Accepted CVL-1 accounting supplies54,982 GPU-allocation seconds over3,366,078
physical steps, including its setup/I/O: approximately0.016334s/step. Applying
that crude rate to the full physical-work upper bound gives:

| Effective throughput | Maximum-work projection | Fits86h aggregate envelope? |
|---|---:|---|
| Accepted collection rate |33.71 GPUh|Yes, estimate only|
| Half that throughput |67.43 GPUh|Yes, aggregate only|
| One-third that throughput |101.14 GPUh|**No**|

Per-job600/1,200s limits can bind even when the aggregate estimate fits.
Authentication, shared-cluster variability and changes in actual trajectory
length make these uncertain estimates. The included tranche checks actual
costs; success does not establish that every later job will fit. The accepted
60-fit CPU study completed in201 allocation seconds, but this18-fit study
includes larger tables and detailed reports: retain the explicit2h CPU ceiling
rather than promise linear runtime scaling.

## 5. Artifact/storage plan

No raw images/datasets/checkpoints are copied into Git. New source closure and
control files reserve50MB; the total **10,000,000,000-byte remote ceiling** covers
that reserve plus new source transport/extraction, bank tensors, prefix/branch
traces, call ledgers, reports, model weights, seals, temporary files, stdout/
stderr and partial failed output. Accepted old artifacts remain read-only and
are not duplicated or deleted. C stores old-member hash references and its new
branch traces, not replacement banks. Approximate payload scaling from accepted
collection is1.5–2GB for this extension, not a measured guarantee.

Per-job total output+temporary+log cap500MB; file-size limit256MiB. Dispatch
checks bytes every20s and stops/cancels on overrun; this is a monitored cap,
not a hard filesystem quota, so transient overshoot is possible and reported.
Leave the per-next-job500MB reserve inside the10GB ceiling. Do not prune traces
or delete failed artifacts to manufacture compliance.

Require `/mnt/d` mounted, Windows D: label `THESIS_SSD`, and≥40GB free before
dispatch. Incremental tar backups go only to
`D:\THESIS-BACKUPS\candidate-value-breadth-precision-20260915\run-<source-hash16>`;
no fallback to laptop storage. Back up/authenticate training outputs, frozen
models, common evaluation and terminal report at four barriers. The accepted
archive verifier checks exact member/seal hashes; no extraction or credential
copying. Stages are nonoverlapping to avoid repeated full archives. Preserve
existing backups. If the SSD is absent/full or backup acknowledgement fails,
stop before the next compute stage. Failed-run backup is performed only after
reconciling terminal job state, never by copying a still-changing allocation.

## 6. Decision requested at the next review

Approve or reject **this exact source/role/protocol/envelope** for a later run.
This preparation does not consume any of it. The remaining decision is launch
authorization, not a fresh method redesign or permission to inspect evaluation
outcomes early. There is no promise that breadth or extra tail precision will
improve ranking; that is what the fixed development comparison would measure.
