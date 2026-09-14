# Current status — 14 September 2026

Active branch: `bottleneck-diagnostics-20260913`, scientific base `001aad99`.
Package integration `a58a17c` and stronger audit `327c94d` were pushed and read
back from GitHub. Diagnostic-only angle inventory committed/pushed `cf6f492`.
Original historical result remains `stop_futility_strong_adverse_signal`.

## Authorized extension — current work

Latest: all56 new jobs and combined verifier301071 COMPLETED0:0; all64 bundles
passed decoder-corrected, repeat and supplementary semantic/provenance checks.
Both output seals matched before results were read. All56 new and8 original
pilot bundles are source-matched on externalSSD. Local101 tests passed.
The [combined32/additional28 report](EXTENSION-RESULT-20260914.md) and full-precision
receipts are prepared: new28 greedy first-only margin improvement+0.5730,
25/28 references positive, but no added successes. Context replacements are mixed;
latent/joint lose one new-cohort baseline success. No scientific efficacy claim.
GPU-job MaxRSS accounting and final reasoning-chat handoff remain pending; no
simulation or analyzer rerun is needed. The next rank-only experiment is proposed,
not frozen or launched. Earlier execution milestones below are chronological.

The user approved the exact additional28 design after accepting the pilot.
Source265b618 and unchanged [execution contract](EXTENSION-EXECUTION-20260914.md)
are frozen. All101 tests passed in the locally extracted package, and all60
source-manifest entries verified. Manifest
`160d0dfc93c32ce578f6aa1fed55b6c615dcf984f60229d44c7fbf2b756abbee`.
Previous job301003 (ref567/repeat0) FAILED1:0 after11seconds in pre-run tests:
two existing archive/audit helper files were omitted from that package. No
model/simulator ran, and the dispatcher stopped without submitting another job.
The failed source/run is preserved. Corrected CPU package preflight301009
COMPLETED0:0 in5seconds; all101 tests passed in the pinned remote runtime.
The metadata-only sequential dispatcher enforces5min/job,7200s allocation
reservation (including the prior11seconds) and1GB storage watermark;56 exact
scientific jobs total, no automatic retries/replacements.
Run `.../experiments/diffusion-bottleneck/extension-20260914-265b618` launched
at2026-09-14T10:18:44Z via controller session17250. First job301010 is submitted
for index8/ref567/repeat0. No terminal scientific completion is claimed yet;
the append-only ledger records subsequent exact submissions and accounting.
After a temporary externalSSD disconnection, WSL/SSH access was restored by the
user reconnecting D:. Local session17250 is closed, but the original remote
controller remains alive (PID1140172); no restart/resubmission occurred. Scheduler
confirmed28/56 processes through301040 successful,1996seconds including prior11.
Scientific outputs remain unopened; use remote process/ledger metadata to monitor.
All56 new processes are now confirmed COMPLETED0:0. Their allocation total is
3941seconds,3952 including the prior11second packaging failure, below7200.
DISPATCH-COMPLETE reports540242493bytes, below the1GB watermark. Combined
verification job301071 has been submitted once; success is not yet asserted.
The dispatcher is complete and must not restart. Original four references/eight runs remain reused unchanged. No new outcome
read before complete successful dispatch and combined verification. See
[launch chronology](EXTENSION-LAUNCH-20260914.md), including the preserved initial
Python3.6 compatibility failure before any job submission. Combined32/additional28
analysis, backup and next-mechanism recommendation are pending, not completed.

The earlier pilot-only statuses below describe the state before this new user
authorization; they do not override this approved extension.

## Current execution

- Package: SHA256 and all24 seals verified;18 additive files integrated once.
- Local supplied tests51 passed; expanded source/endpoint tests59 passed.
- Paired reaggregation: all15 pairs and20 contrasts/cluster SEs verified locally
  and in the pinned remote Python3.11.10 runtime, without new model execution.
- CPU job300959: FAILED2 after6m49s, specifically the strict canonical-angle
  guard in full trajectory reduction. No completed report exists from that job.
  Canonical preservation and paired stages completed before that failure.
- Canonical preservation: all450 stage0 shards,22 source files,13 model files,
  four compact analysis files and1600 exposed reference files passed.
  Receipt SHA256 `0c406ca98e051d0f5aa9d8d701f5bc6bc299d67b38906bb2c6bbc39e6d5362ee`.
  This does not claim every transitive runtime dependency or model backup was
  independently archived. No unevaluated reference payload was read/hashed.
- CPU jobs300960 and300962 completed0:0. Complete supplementary inventory
  proves unique57600-run coverage, float64 states/goals,1766 exact2pi samples
  in24 runs, no other range anomalies, and zero unmasked angle-category or
  combined success disagreements. Receipts are committed under `receipts/`.
  Source126d079; supplementary receiptSHA256
  `1cf790828d24c964026bc9e7568e7f2aeb9eca21c757ecc2a137056d53e21684`.
  Guard-only correctionc567ccf admits exact2pi states without changing saved
  arrays, goal admission, historical predicate or labels. See ANGLE-GUARD.
- Corrected full CPU reduction300963 COMPLETED0:0,11m10s. All57600 runs,
  450 shards and36 seed/horizon/arm blocks passed; zero technical-invalid
  records/planner exceptions. Independent scalar endpoint checks passed.
  Full report and execution receipts committed; see TRAJECTORY-RESULT.
  Source manifest
  `689e559a85e60afdc65abc95e2f4d3782395a45127f47d283847b02253f835b0`;
  output `.../experiments/diffusion-bottleneck/audit-20260914-c567ccf`.
- Old WSL backup:375 indexed shards rehashed with zero errors; incomplete.
  Its slow directory copy to externalSSD was stopped and preserved PARTIAL at
  `D:/THESIS-BACKUPS/bottleneck-20260914/final-20260906-4a608e5`.
  This does not damage or complete the old375-shard backup.
- COMPLETE new externalSSD archive:
  `D:/THESIS-BACKUPS/bottleneck-20260914/completed-stage0.tar`.
  Packjob300961 completed0:0 in6m21s. All116555 members of450 shards and the
  compact analysis verified locally against the authenticated canonical
  receipt; archiveSHA256
  `d02d918017b9f9903b2b4a4bf6522e64776c6580f604ee5782f5d5beaec65e0b`.
  Size3126661120 bytes. No extraction needed. Receipt
  `receipts/ARCHIVE-BACKUP-VERIFIED.json`. This archive does not back up the
  model checkpoints or reference collection; their canonical identities were
  checked separately and no such backup is claimed.
- Pilot: implementation/specification2f48668+b1c9633 committed before execution.
  All eight jobs300964_0 and300965_[1-7] COMPLETED0:0. All16 distinct anchors
  available; exact3184 paired array repetitions; no simulation rerun.
  Source manifest897dba9f318c48ae2e0889c8bf78ccf22808ccbe6132af7aee4e7648bfe8163f.
  Output `.../experiments/diffusion-bottleneck/pilot-20260914-b1c9633`.
  Original offline verifier300966 FAILED1 on checker-only sklearn coefficient
  casts; correctione7188b7 and offline300973 passed on unchanged saved bundles.
  Source9240097 separate semantic/provenance supplement300974 passed; authenticates
  launch/model/history, reconstructs greedy costs, caps/flags/angle domains,
  unique coverage and2208 branches/68360 primitive steps. No tolerances changed.
  AggregateSHA25658c75c57e87a5736e6a9065334beeef57a682e9193153b6c19f2e08b80ff749a;
  supplementSHA256af7f9b1a67cd95b44d3a46cf1b7312dcf92851e187c63798e18bacd79eb2b2ac.
  All24 pilot files source-matched on externalSSD at
  `D:/THESIS-BACKUPS/bottleneck-20260914/pilot-b1c9633` (76.764MB).
  See [completed pilot](PILOT-RESULT-20260914.md) for evidence and limitations.
  State/latent/joint first-selection changes3/5/6 of16, effects mixed. One
  shared bank had14 successful first chunks; baseline missed them, latent/joint
  and greedy64 selected successful first chunks. Not SAGE-gap resolution.
  Summed runner338.606s versus543s Slurm allocation, different timing boundaries.
  [32-reference proposal](32-REFERENCE-PROPOSAL-20260914.md) estimates72.4min
  allocated for full32 (63.35min additional28), with a proposed2hour review
  envelope. NOT launched or approved; no training/redesign/unused payload access.

The installed native `_get_obs` uses angle modulo2pi; its source SHA256 is
`d8d0de35aaab5b846db4e79b0fbfd6b17375178cce40a25df5301c8030ca6d68`.
The endpoint-admission issue is now classified narrowly; no claim that every
unrecorded native body angle was reconstructed. Full reduction passed.
Current local helper/validation suite95 passed; corrected remote audit suite64
passed; pilot deployed suite20 passed per successful job, corrected verifier7
and supplementary12 passed remotely. Counts denote different source scopes.

## Latest chronology

- c75b378: full trajectory result and pilot launch record published.
- e7188b7: preserved failed300966, corrected independent decoder only;300973
  passed. Aggregate was read before external source review finished; findings
  were explicitly provisional until the additional semantic checks passed.
- 9240097: independent review counterexamples addressed by a separate saved-
  artifact supplement, not changes to the runner or old verifier.300974 passed.
  New receipt and checked physical counts complete the combined acceptance.
- Final deliverable: completed preservation/full reduction/pilot, mixed findings,
  and measured proposal for review. No active diagnostic simulator jobs or
  unattended monitoring mechanism; no32-reference expansion submitted.

Original three E12 drafts and unrelated E14 pending jobs remain untouched.
Bulk artifacts are outside Git on Prometheus/external SSD. No credentials,
permissions, connectors, protected payloads or historical artifacts changed.

## Archived package status — 13 September 2026 (superseded deployment details)

The first diagnostic package is implemented and tested locally. The completed study's full outcome tensor and summary were checksum-verified and analyzed. All 15 pairwise contingency tables and all 20 point contrasts and reference-cluster standard errors passed a separate standard-library reaggregation. There are 51 passing local synthetic regression tests.

## Not yet deployed

Desktop Commander reported the registered computer offline (last seen 11 September UTC). A GitHub branch-creation request was blocked before execution. No command subsequently reached Prometheus, no new GitHub commit exists, and no background monitoring process was started. Read access to GitHub worked.

The package is supplied as additive source files and a patch. It changes no existing repository file. The planned branch is `diffusion-bottleneck-analysis`, based on `001aad99a2e2e6a141797e0c516604e7188d706a`.

## Completed versus pending

| Item | Status |
|---|---|
| Pinned summary and tensor integrity | Passed locally on real archived files |
| Paired outcome and horizon analysis | Completed locally; exploratory only |
| Independent count/contrast/standard-error check | Passed; no independent bootstrap-quantile or physics rerun |
| Raw-trajectory failure reader | Implemented and synthetically tested; real traces not accessed |
| Full indexed-backup rechecker | Implemented and synthetically tested; real backups not rechecked |
| Read-only cluster launcher | Shell syntax passed; pinned remote runtime not exercised |
| Simulator branch protocol and case selection | Written; no branch simulator runner or execution yet |
| Novelty map | Primary-source screening, mostly abstract-level; not exhaustive |
| New diffusion method/training or final benchmark | Not implemented or launched |
| GitHub publication | Blocked; zero commits created |

The next cluster work is backup verification and complete raw-trajectory diagnostics, followed by same-bank selection and intermediate-state interventions after exact branch-point replay checks. The already evaluated 1,600 references are development evidence for this new work. The 4,400 unevaluated references are untouched.

See PAIRED-RESULT.md for actual findings, PLAN.md for the controlled interventions, RUNBOOK.md for execution details, and PROVENANCE.json for exact identities and limitations.
