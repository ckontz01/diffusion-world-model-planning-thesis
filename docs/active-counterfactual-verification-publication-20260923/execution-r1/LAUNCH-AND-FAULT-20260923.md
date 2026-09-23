# ACV0 R1 — successful replacement worker; controller acceptance fault

## Outcome

R1 is **stopped and incomplete**. The one authorized replacement, Slurm304193 / `collect-fit-490` attempt2, completed0:0 in80 allocation seconds. Its exact-device gate, physical replay/native technical checks, unchanged Le-WM fingerprint and complete worker seal passed. The controller then rejected its hardware allocation receipt because it compared the runtime's fully qualified hostname `gpu09.cluster` literally with Slurm's node name `gpu09`.

This is a control-plane acceptance defect introduced by this R1 implementation, not a GPU-name, renderer, replay, training or scientific-outcome failure. The mocked tests used matching artificial hostname strings and did not cover short-name/FQDN differences. Passing those tests did not establish that live name association.

The successful490 output MUST NOT be rerun. It remains sealed and unchanged in the R1 run. No545 allocation was submitted, no third source opened, no fitting/evaluation/analysis ran, no technical-tranche marker exists and no scientific-task acceptance entry was written. Thus a successful sealed worker is distinguished from controller acceptance; the490/545 tranche has NOT passed. No scientific aggregate, native-success values or effects were opened or interpreted.

## Immutable execution and authority

- Recovery implementation/approval commit: `92d2ae4f260b0d15e59310e42674934e94f732c4`, pushed and exact remote branch readback verified before transport.
- Transport/SSD/namespace receipt commit: `cfc1cb647c2f86b1300e6721faa5562c75a63fa5`, pushed and exact remote readback verified before launch.
- Source manifest: `c2c6fcbe8c41fed22d0fde17bcb5f8cd456a74c1cb0d77039f4df94d86e0d468`.
- Enabled recovery approval: `e1e4b6f6d0e0d1fbb83e89d165be793128f02130647e21a1c12c5892d7d90460` in both separate control approval and run APPROVAL.json.
- Exact supplied instruction: `1ac7a04083c2ccce2ea399bacc6eb407b21dca1e3da21b378281d7aa460d8214`. Authority is the selected reasoning direction supplied by the user under standing delegation, NOT a fresh direct user signature.
- Old source/approval remain `5630b222e8a88d0eaa45408876929724734d1f992afa657131ac770fb0400fa9` / `7ea5f67225ee1bff091e705e7515a4ed8f3589694e6093f1c2e7c607d27a6a88`.
- New canonical grid: `2b893c8a1c13eb2e0add6d80b61814c573b884f94fabfbde89e05804950298f5`; only490 seconds1800→1740 differs from the old canonical grid `f9b4986c9f674122c253cff9aaf802e8d4b181180553d0e5643c0c92bb175a2a`. Scientific modules/input/roles remain byte-identical.

Remote source:
`/lustreFS/data/superworld/ckontzias/thesis/snapshots/active-counterfactual-verification-recovery-r1-c2c6fcbe8c41fed2`

Remote control:
`/lustreFS/data/superworld/ckontzias/thesis/staging/active-counterfactual-verification-recovery-r1-c2c6fcbe8c41fed2`

Remote run:
`/lustreFS/data/superworld/ckontzias/thesis/experiments/active-counterfactual-verification-pilot-v1/run-c2c6fcbe8c41fed2`

Controller PID684587, Linux start ticks893012584, launched Unix1790173236.9181964. Job304193 submitted Unix1790173240.7746174. The controller charged its completed allocation at1790173332.0064685 before failing acceptance. At final direct reconciliation1790173410.9429038 the exact controller was inactive, both campaign allocations were terminal, no live ACV0 job or unresolved submission existed, and the original v2 member set and copied provenance authenticated unchanged. No other ACV0 namespace/allocation was found in the bounded checks.

## Accounting and hardware

| Allocation | Scientific task / attempt | Scheduler result | GPU allocation seconds | CPU-stage seconds |
|---|---|---|---:|---:|
|304189|collect-fit-490 /1|FAILED1:0|23|0|
|304193|collect-fit-490 /2|COMPLETED0:0|80|0|
|Campaign to date|2 allocations;1 failed,1 scheduler-successful|Controller stopped|103|0|

Authorized replacement count1; automatic retry count0. The historical failed attempt supplies no data or scientific denominator. Neither charge has been reset. Queue time is excluded. Only one new allocation occurred, against its1740-second hard/1620-second work limit; full initial campaign reservation was220763/220800 GPU seconds. The fixed338 remaining tasks were not submitted. There is no permission to spend saved seconds on an extra attempt.

304193 measured **NVIDIA RTX 6000 Ada Generation**, CUDA available, one visible device, runtime hostname `gpu09.cluster`, actual Slurm job ID304193, compute capability8.9,142 multiprocessors, total memory51010207744bytes, UUID `ad8f1d75-4710-4a93-9782-26f29a0c5487`. This is separate from partition `a6000`, QOS `normal-a6000`, account `superworld`, scheduler node `gpu09`. R1 used80/3600=0.0222222 GPU-allocation hours on NVIDIA RTX6000 Ada Generation. The old304189 device string was NOT measured; no retroactive device attribution or historical speedup is claimed.

Worker72.28277449199231 wall-seconds through payload;95.543304291 process-CPU seconds; Python high-water RSS1294032896bytes; Torch allocated/reserved peaks84553728/113246208bytes. Scheduler TotalCPU101.246seconds (batch101.245), batch MaxRSS1322800K: separate scheduler/process scopes, not whole-machine RAM or interchangeable timing. Technical records report16 branches,997 physical actions,1029 image encodings and unchanged Le-WM tensor fingerprint `ceaa62f4aa977f3244da424079a9044a3ab69c86014295c9d48e236d49a398c7`; these are technical/resource observations, not efficacy or cohort-throughput claims.

## Evidence and preservation

Four payload members total4623428bytes; including seal4624057bytes, below10MB. The hash-only worker seal verification did not expose payload contents. Relevant hashes:

- Worker SEAL: `c280ffb2e71288e8ea40fc5db34ff42fb464a928f42ab388e8e9b14abb8b3b6a`.
- HARDWARE: `44729aa05006bead67008711e31c6448678f2181076b0040c8fde3bb25cdec07`.
- TECHNICAL: `6eb9997d681fa98953f6e0917ad89933b30cc9ef3c28934ba65db01be4ad6a7b`.
- DISPATCH: `c629e2896b231fcf0fe19abf9a6e0cb6cfc826e52e720387b9f66b9473b4e793`.
- CAMPAIGN-ATTEMPTS: `1697457dcc5186d975081d40ef6a6314f3f7b7f27d62ac93239602f8c803a017`.
- STOP: `298615b25325a74d113cbda540528bc4b64508a0273b8dd1f1428b1c733f38fe`.
- Controller error: `11ca54515a77d822394f9146fd01d4dc77f91a03c911cd7d12f1bd5f2f69214c`.

The fault is at frozen dispatch.py line138, the conjunction checking `h['hostname']==terminal[0]['node']`. The job identity matches; the string comparison fails. The exact traceback, terminal charges, scope-separated scheduler measurements, hardware/technical receipts and hashes are retained in FAULT-RECONCILIATION.json. Worker stderr has a Gymnasium array-casting warning; scheduler stderr has Apptainer bind-mount informational messages. These did not cause a worker failure.

Current source/control/model accounting1729217bytes includes550511 original failed-v2 bytes,559437 bytes of separate prior provenance, and39148 external R1 control bytes. Worker4624057bytes is separate. Full future live reservation1812000000bytes; inclusive live/archive/partial reservation7248000000bytes remains within8GB. No deletion, overwrite, patch of executed source, relaunch, retry, resume, archive regeneration or historical study transfer was performed.

The new small preparation source package alone was SSD-verified:34files/901373bytes at `D:/THESIS-BACKUPS/active-counterfactual-verification-20260923/bindings-r1`, designated THESIS_SSD, delivery receipt SHA `87948aa5a729bb2834d5a03917ae0a05b9cea5bde60bda178c6eb767c3be907a`. This is NOT a final scientific-run backup. The incomplete run has no final archive or verified final SSD backup; successful/partial cluster evidence is retained. Existing v1/v2, LGP/AV0 packages and E12 drafts are untouched.

## Scope of the next decision — recommendation only, not executed

R1's any-further-fault clause stops dispatch. Its no-resume/no-further-replacement terms do not authorize changing this frozen controller and restarting it. A separately scoped **control-only continuation** decision would need to specify authenticated short-name/FQDN association (or distinct hostname/node evidence linked by exact allocation ID), preserve the exact GPU-name gate, reuse the existing successful sealed304193 output without recomputation, carry all103 charged GPU seconds, and authorize only the338 never-submitted task keys with unchanged science/caps/gates. Tests should explicitly cover actual short-name/FQDN representations plus genuinely mismatched nodes/allocations. This recommendation has not been implemented or launched.

Until that explicit decision, preserve both run namespaces and STOP, do not rerun490, do not submit545, do not interpret partial effects, and do not reactivate closed historical-study monitors or launch a follow-up study.
