# ACV mechanism replication: production runtime implementation

Research execution is disabled. This is implementation work against reviewed preparation `70e359258d0763a29be40831998696e2ca7a9d0d`, not a scientific redesign. The completed ACV0 package at `5d8666754ad8aa0507730f86cf3ee6caa32c105a` and the saved-data mechanism findings are unchanged, including worse conditional prediction metrics.

## Delivery status

The designated THESIS_SSD was reconnected on24September. `RECONCILIATION-LIVE.json` records successful fresh cluster identity-only authentication of the unchanged512-source proposal, with zero conflicts or reference-payload reads. All eight tracked role-ledger identities were also rechecked; no intervening ledger was found. The earlier `BLOCKER-20260924.md`, `RECONCILIATION.json` and `IMPLEMENTATION-RECEIPT.json` remain historical records, not current blockers.

`SOURCE-MANIFEST.json` defines the immutable runtime closure and `EXECUTION-APPROVAL.json` keeps authorization false. Delivery requires the source freeze, exact remote Git readback and `PACKAGE-VERIFIED.json` documenting the new small export's whole-file/every-member SSD verification. The final delivery receipt is outside this frozen closure at `docs/active-counterfactual-mechanism-replication-publication-20260924/preparation-runtime-v1/DELIVERY-20260924.md`. A later explicit execution instruction is required even after completed delivery. There is no command that enables approval automatically.

## Actual production entry points

All paths below are relative to this directory. Run from the complete repository-layout source export, not a collection of individual files.

| Entry | Purpose | Required interlocks |
|---|---|---|
| `prepare.py --reconcile-live` | Metadata-only512-role/registry reconciliation; preserves the pending receipt | Configured WSL/SSH; no reference payloads |
| `seal_package.py freeze` | Source closure, disabled approval template and source tar | Live reconciliation, passing tests, bounded preparation receipt |
| `seal_package.py backup-package` | Copy only the new small source package | Exact THESIS_SSD UUID/label,40GB free, whole/member readback |
| `transport.py stage --approval A --run R --bundle T --backup-receipt B --receipt X` | Exclusive new snapshot/control/run namespaces | Explicit enabled new-study approval, all input/source hashes, copied package hash |
| `transport.py launch --approval A --run R --receipt X` | One detached controller with PID/start_ticks receipt | Same new approval, staged identity, no prior launch intent/controller |
| `dispatch.py --approval A --run R --control C` | Serial Slurm campaign, exact8197 tasks | Pinned host Python/sbatch/sacct; durable claim before submission; full-future reservations |
| `run_worker.sh PACKAGE A R TASK GPU` / `supervise.py` | Bound entire container stdout/stderr and worker deadline | Allocated4CPU job; pinned container; clean existing runtime |
| `worker.py --approval A --run R --task KEY` | Four explicit fits,8192 evaluations, one analysis | Exact submitted allocation association; CPU/GPU role/hardware checks |
| `finalize.py --approval A --run R --control C [--resolution X]` | Independent full-grid acceptance and terminal accounting | Complete exact allocation set, all seals, model/tranche ordering; explicit fault resolution if needed |
| `preserve.py archive --approval A --run R --control C --acceptance C/FINAL-ACCEPTANCE.json` | One exclusive new-study archive | Final acceptance bound to package/approval; all accepted seals unchanged |
| `preserve.py backup --approval A --run R --request EXACT_REMOTE_POSIX_REQUEST` | One native-Windows streaming transfer | Exact SSD, deadline/bytes, whole archive and every member verified |

`A`, `R`, `C`, `T`, `B` and `X` are explicit paths, not guessed placeholders to pass literally. The disabled approval template supplies the exact manifest-derived run name. Source/staging names use the same manifest prefix. No original ACV0 capability is accepted for the new512 role. No research fitting, simulation, cluster stage or submission command was run in preparation; local synthetic optimizer tests used artificial fixtures only.

## Fixed scientific path

The original `model.py`, `policy.py`, `tree.py`, bridge, episode executor, endpoint verifier and192-update trainer are imported unchanged and source-hashed. The production selector duplicates the reviewed small subclass without importing the preparation helper that disables CUDA. Existing policy paths delegate directly to the old selector. `committed_feedback` retains static's prefix and always permits the actual response-conditioned local suffix after a nonterminal prefix, including prefix0; no suffix is queried after termination.

`models.py` explicitly injects94411/94412 and94421/94422 into the accepted trainer. It never calls the inherited hardcoded-original-seed `fit_job`, never fits a Bayesian extra model, and never recomputes preprocessing from evaluation. The original94011/94012 pair, exact saved fit/validation data and preprocessing are authenticated copies. Six model byte identities,192-update traces, seed associations and preprocessing are sealed before any new evaluation capability can return a reference. Validation is reporting-only. Inference fingerprints both loaded small-model tensors and LeWM tensors.

There are exactly512 ordered sources, five learned arms × three fixed seed pairs plus one early-replan execution/source. That is8192 unique episodes plus four CPU fits and one CPU analysis. The original64/16 roles remain separate; old32 outcomes never enter the new estimate. Each physical episode constructs a fresh world/history/action stream. Initial tree actions and predicted features must match across learned arms and pairs; later trajectories are not forced to coincide after decisions diverge.

The first source's16 scheduled episodes are the included technical tranche. Their endpoint/seal/resource/model/tree checks gate source2; successes and rankings do not. Analysis independently reopens sealed saved evidence with the accepted endpoint verifier and uses the reviewed seven-contrast estimator unchanged, averaging fixed seeds within source before whole-source bootstrap. `REPORTING-CONTRACT.json` records the uncertainty/certificate interpretation explicitly.

## Reservations and measured-cost scenarios

No proposed ceiling is spending authority. One exact NVIDIA RTX6000 Ada Generation at a time, authenticated `gpu09`/`gpu09.cluster` association,4CPU24GiB per GPU task,300s hard/240s work plus60s preservation. Four CPU fits and one CPU analysis each have4CPU8GiB and7200s. The scheduler name, ID, TRES, account, QOS, node and time limit are strict. The known exact pending placeholder has at most eight incomplete polls, not a general relaxation of identity checks.

| Arm | ACV0 allocation seconds /32 | New episodes | Direct historical-rate scenario, GPU hours |
|---|---:|---:|---:|
| static |1039|1536|13.8533|
| committed_feedback |**Unmeasured**; assumed static-mean proxy|1536|13.8533|
| no_update |1014|1536|13.5200|
| active |1031|1536|13.7467|
| ordinary |1050|1536|14.0000|
| early-replan |970|512|4.3111|

Total scenario73.2844GPU hours; assumed2×146.5689h; assumed3×219.8533h. Full GPU ceiling remains682.6667h. Queueing, new-control cost, changed verification overhead and future throughput are not established by these scenarios. Historical CPU allocations were17s joint fit,17s ordinary fit and18s analysis; four new fits and the much larger analysis remain unmeasured, with a10h aggregate CPU-stage ceiling. No timeout shortening, task rebatching or increased concurrency makes these forecasts appear better.

`FOOTPRINT.json` reserves16.384GB for8192 complete2MB workers (NPZ, metadata, hardware, technical and seal), and1GB for four100MB fit outputs,100MB analysis, all four per-task log streams, source/reused inputs, control/accounting/fault receipts and archive/request metadata. It reserves120000 archive members with368650240 bytes of tar/header overhead. Full live17.384GB, archive17.752650240GB, inclusive71.641950720GB remain below18/18.5/80GB. Hidden files and retained failures count; no deletion or cap reset is permitted. The inclusive contract allows retained failed-transfer bytes; it does not authorize a second attempt.

## Testing and unresolved live-runtime uncertainties

`bounded_run.py LABEL PYTHON -B test_runtime.py` applies a Windows8GiB job limit, four CPU cores/threads, an append-only cumulative four-hour wall budget and1GB output bound. All unsuccessful attempts remain in `ATTEMPTS.jsonl`. Artificial optimizer updates are allowed; none uses research data. No favorable toy outcome is required. The full8197-task dispatch state machine is exercised with a mocked scheduler; full-grid worker seals are mocked to avoid generating16GB of artificial evidence, while actual saved episode/endpoint/seal interfaces are tested separately on all six policies. This distinction is intentional and must not be described as8192 physical test episodes.

Fresh role/registry identity metadata was checked via the configured cluster connection after reconnection. This is not permanent source allocation: reconcile intervening role assignments again before any future launch, without replacing IDs silently. Still unobserved here: deployed container/runtime availability and hardware association; real payload/checkpoint read authentication at execution time; end-to-end actual GPU throughput and new-control timing; real task bytes and tail behavior on the new cohort; actual Slurm submission/accounting latency; the large final archive's transfer duration. Artificial tests do not certify these. The future included16 tranche and fail-stop resource/identity checks are the execution-time gates, not permission for an extra pilot.

Ambiguous submissions preserve their full claim. Terminal failures are charged before validation. An existing launch/controller cannot restart or repeat a successful task. A control-only missing acceptance can be finalized only with a separately explicit, hash-bound dated resolution and fully reconciled terminal suppliers. No automatic retry, replacement, scientific extension, promotion, AV1 launch or next experiment is provided. Old monitors remain paused; E12 and historical decisions are unchanged.
