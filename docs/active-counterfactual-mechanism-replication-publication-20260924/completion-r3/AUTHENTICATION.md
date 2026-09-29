# ACVM1 final authentication and preservation

Final status, 29 September 2026: computation, independent acceptance and designated-SSD preservation completed. This supersedes the pending-transfer state in the historical COMPLETION-STATUS-20260929.md receipt. Publication and any later handoff are separate records, not new research execution.

## Exact completion

- Scientific manifest: `9f91156fd11a5d54172e8cec79d37ca50199c132780b5aee3636f34b0dd2e916`.
- Original scientific approval: `22cf11af0742c4a17987d783cf984c313dfc45beaff2a7ba32d1b2c6f36f3d27`.
- R3 control manifest: `59e41de0f12c14af9eaba86b74e8699d3151b6e0e45554627864b54bc4466741`.
- R3 approval: `2eaab9a462eb36d5f73eb61acee259bc8afeba8a79cd928edfe9ec99e8c3fbc7`.
- Completed at 2026-09-29 13:57:03 UTC: 8,197 successful unique tasks, including 8,192 evaluation episodes over the unchanged 512 sources. All 8,199 allocations reconciled. Final CPU analysis allocation: 312870.
- Historical failed allocations 304589/0 CPU seconds and 304591/8 CPU seconds remain included. Successful R2 fit 304593/11 seconds was carried without recomputation. No evaluation failed or was repeated.
- GPU allocation: 265,130 seconds. CPU-stage allocation-wall: 6,496 seconds including failed attempts. Both remain within their cumulative authorized limits.
- Original R3 PID 2859603/start_ticks902007058 exited, controller stderr empty, R3 STOP absent, no unresolved or unaccepted tasks in the final observation. No controller was restarted for loss of laptop SSH access.
- Frozen R3 finalizer ran once and passed; FINAL-ACCEPTANCE.json SHA256 `8f896135824a282294de61d2aa1c20d331595bd2ce031e49789825e0844cea23`.
- COMPUTE-COMPLETE.json SHA256 `5f1f409844e4b37787293de4a919c7f55cc14fd06fe7a8c23c3ed49438b4b835`.
- Six-model freeze SHA256 `84b170e84e835a0e9748f1a9742fcfad8625b8f2d5bfdc2046d7f749cd941550`; preprocessing SHA256 `44f591ac7fe450fbe4c2c79431d1831b63706196c7ea056316d1aec17fb2d514`.
- Included first-16 gate SHA256 `e98887c713efcdbf9f4883a8b42855c423f0740bd6d4674ab08a8f23df2f4375`. Finalization authenticated that model freeze preceded evaluation access and that source2 followed the gate.
- Accepted carried-fit receipt SHA256 `62c59d0d8afd473fda8c1fb11a9faa540d5653a7205018edfb1ae98088fc4b42`.

## One final archive and one successful transfer

Remote final archive: `/lustreFS/data/superworld/ckontzias/thesis/experiments/active-counterfactual-mechanism-replication-v1/run-9f91156fd11a5d54-preservation/final.tar`.

Native SSD archive: `D:/THESIS-BACKUPS/active-counterfactual-mechanism-replication-v1/run-9f91156fd11a5d54/final.tar`.

- 10,440,048,640 bytes; 90,382 regular members.
- Whole-file SHA256 `02e55e2bd0c6a1671e4da179869ac5ac4cfd3475e9d712b1a3f420e357370310`.
- Request SHA256 `32f9c46fcdbb51691d43be53c9a77fbb7269853b38df6051817cfe2d92eb52c7`.
- BACKUP-VERIFIED.json SHA256 `b6a200521c0c8a7c8c5b95813206d63656321c2ff984c5c399a9378c288cdfb2`.
- Verification completed at 2026-09-29 15:35:37 UTC / 18:35:37 Cyprus on THESIS_SSD volume `0a2f1ba9-0000-0000-0000-100000000000`, with more than 40 GB free at transfer start.
- Archive wall time 191.952798 seconds; first transfer plus verification 924.344 seconds.
- Whole file and every member verified by the frozen preservation path; partial and failure markers absent. Nine roots cover the full run plus original/R1/R2/R3 sources and controls, including historical failures and their resolutions. No historical-study archive was rebuilt or transferred.

## Reporting and boundaries

Scientific aggregates were first opened at Unix 1790697410.2740335, after the SSD verification gate. The selected archive members were additionally authenticated against the preserved request during publication reading. REPORT.json is byte-identical to the sealed analysis: SHA256 `13749ea4a9c32250abbf7fa99cf209cf266349e933bec9fa7cf755e915c9ceeb`.

The publication helpers only format saved evidence, verify identities and source/pair arithmetic, and summarize already-recorded costs. They do not refit, simulate, infer new outcomes, rerun the bootstrap or change the estimator. All 512 source results, 8,192 episode identities and recorded branch decisions are published without favorable selection. The verified archive retains full action/state/feature/endpoint arrays. Complete accounting and model/fit records accompany the report.

Measured sizes: 10,196,275,956 bytes of evaluation workers and 87,618,606 other archived member bytes. Inclusive accounting upper bound is 32,186,877,402 bytes, including both archive copies, full live roots, new-study SSD packages and a further 1 GB metadata/publication allowance; this is below 80 GB. Individual worker, control, group, live and archive caps passed.

Access was restored through the administrator-documented CYENS bastion using the existing configured account/key. No VPN, credential extraction, dependency change, research repair or rerun was involved. The original SSH configuration backup is retained locally; connection configuration and credentials are not part of the public report.

The user-paused monitor stays paused. No automatic next experiment, AV1, model promotion, resource expansion or reserved-data access is authorized. All historical decisions, completed studies and E12 drafts remain unchanged.
