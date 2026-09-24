# Narrow pre-launch correction: focused results

24 September 2026. Reviewed publication `bb181cc6b6c60770898afacdcca3fb9e604c90c1` is preserved. Corrected preparation is `runtime-v2`; **execution remains disabled**.

## Scope and evidence

Direct user instruction is preserved byte-for-byte in `CORRECTION-INSTRUCTION.md`, SHA256 `fcdf744e20d4e4a1cf02cb4cd08c092cfdf563fd01b28665ab59d2b55cf59fbe`. Supplied review ZIP SHA256: `f1de1d1906befeead5452f8dd82ef52c8cdfd6938d2f242c79f66160bc0691a3`. Every extracted member matches the supplied manifest; original review results and probes are retained unchanged under `review-input/`.

The supplied excerpt probes reproduced the erroneous CPU/GPU `/bin/bash` operand and all six `KeyError('initial_sha256')` failures. Their source excerpts were AST-compared to the exact reviewed command/evaluation/reader functions. On Windows, only the probe's Linux-only ELF-header read was replaced by an explicit artificial `/bin/bash` binary fixture; no shell binary, scheduler or cluster was invoked. Receipt: `PROBE-REPRODUCTION.json`, SHA256 `cfbabff5c7136de7321180c94a89adf922b759279f12a6cd55bf4e4e01e0263b`. These probes are not substituted for the production-path tests below.

`SOURCE-DIFF.patch` is the complete unified Python/shell correction diff against runtime-v1, SHA256 `b9c3302a3c97f0a325e4f018e77189435fb336c9ed807ee08e12bd3100dd5e2d`. `SCOPE-AUDIT.json` SHA256 `80b0eda2b314bee13aac30ebed82030863c4bb493f1f40256dbb9b6624e702c0` records every prior/current source hash, all67 old manifest members unchanged,13 copied code files byte-identical, and nine carried metadata/resource files byte-identical. Only dispatch, worker, acceptance and analysis change in the production path, plus the new coupling helper. The runner/sealer changes enforce correction-specific preparation limits and the new export namespace. Remaining added code is focused testing/provenance tooling.

## Focused integration:22 tests passed

Receipt `TEST-CORRECTION.json`, SHA256 `7a6c4327713c9bf3ecea8f5aac278d311d849cc5b70e8ee61545bc5fd92d7c22`.

### Actual CPU/GPU command vectors

Both actual generated vectors select the exact `runtime-v2/run_worker.sh` file, beginning with the accepted `#!/bin/bash` shebang. Five following arguments remain `[package, approval, run, task key, gpu flag]`. Every CPU/GPU resource, time, account, partition, QOS, node, log and no-requeue option was compared to the old generated vector and matched. `/bin/bash` is no longer a batch-script operand. The wrapper's bytes are unchanged; no live submission was made.

### Actual worker → saved authorization → seal → acceptance

All six tests run the production `worker.main()`/evaluation path, actual `episodes.save`, unchanged inherited `load_verify(..., authorization=...)`, actual worker sealing and actual `acceptance.worker`. Authorization is a real `common.Authorization` instance with an artificial fixture initialization; its reference capability and the reader's exact binding/NPZ/hash branch run, not a mocked replacement. Hardware, runtime loading, checkpoint objects, reference NPZ files and physical world are artificial. The original endpoint verifier remains unchanged. Small artificial search settings are documented in the test receipt, not applied to the production protocol.

| Configuration | Complete worker bytes including metadata/hardware/technical/seal | Accepted |
|---|---:|---|
| static |1276497|yes|
| committed_feedback |1276593|yes|
| no_update |1276523|yes|
| active |1276497|yes|
| ordinary |1276451|yes|
| early-replan |1241183|yes|

All42 rejection checks passed: for each control, absent initial hash, absent goal hash, wrong initial hash, wrong goal hash, wrong reference binding, changed initial array and changed goal array were rejected by the actual authenticated saved reader. No normalization, relaxed hash comparison, verifier modification or removal of production authorization was used.

Maximum4×4/150-step evidence serialization plus100000 bytes of complete-output metadata/technical/seal reservation is1373681 bytes, below the unchanged2000000-byte cap. Largest actual complete worker was1276593 bytes. The original full-campaign footprint remains17.384GB live,17.752650240GB archive and71.641950720GB inclusive, below18/18.5/80GB. Per-worker logs remain counted separately under the unchanged complete log reservation.

### Cross-episode coupling

- Matching selected-action prefixes passed the actual first16-cell gate and gate readback.
- Three separately saved, authenticated, sealed and individually accepted artificial episodes had altered `b0/latent`, `b0/dynamics` or `b0/initial_proprio` prefix fields. Each was rejected by both the included gate's bounded digest comparison and the independent actual-array comparison.
- Different selected prefix action sequences were accepted without trajectory equality. An altered post-prefix latent was allowed. Changing only a prefix-index label did not change the action-based association (individual evidence still separately requires a valid tree/index binding).
- Actual terminal prefixes of lengths2,3 and5 passed when matched. Inconsistent flags, lengths or same-action histories with different terminal lengths were rejected. No missing steps or suffix were fabricated.
- The actual final analysis loop visited8192 artificial records across all512 ordered sources. Its coupling function compared actual arrays and rejected a same-prefix mismatch in the final source. For this full-grid wiring regression, the saved reader/seals were fixtures and the estimator was replaced by a fixed non-efficacy fixture; the six production-path tests above separately exercised the real reader. This is not8192 physical episodes or another scientific/bootstrap analysis.

Relevant existing regressions also passed: unchanged original decisions and committed-feedback terminal/fallback semantics;8197 unique task identities; exact scheduler/hardware checks; model-access barrier; complete future resource reservations; all8197 serial state-machine tasks with mocked scheduler; included16-before-source2 ordering; finite pending grace; ambiguous/failed claims retained and charged; no successful restart; explicit control-fault finalization; disabled production CLIs; and archive path/deadline/hidden-member checks. No new fitting was performed and the previous artificial optimizer/efficacy suites were not rerun.

## Preservation regression and bounded accounting

`TEST-PRESERVATION.json`, SHA256 `271df6bef9a64cd33bde8a39f46aa86ba4ecbbc8159282f0f54326e6c517160c`, passed the actual artificial archive/whole-member-verification functions, mocked native-Windows transfer, retained failed128-byte partial, no fake ACK and repeat-archive refusal. This test made no network or real SSD transfer; the corrected package's actual SSD copy is separately documented by `PACKAGE-VERIFIED.json` after freezing.

All local attempts are retained in `ATTEMPTS.jsonl`. The first focused run passed21 checks but its full-grid fixture lacked a mocked seal hash, causing `FileNotFoundError`; that fixture was corrected without relaxing production authentication. The second run passed all22 checks. Recorded local scripted wall time through the scope audit is514.828 seconds, including the failed attempt; peak Windows job memory1753686016 bytes, four-core affinity15 and8GiB limit. Preparation caps remain7200 cumulative seconds and250MB new artifacts; serialization and the small verified export fit far below that artifact ceiling. Freeze/copy timing is recorded separately in the final delivery receipt.

No real research checkpoint inference, research-data fit, new reference payload, physics/simulator, Slurm or GPU allocation occurred. All scientific choices, roles, seeds,192-update recipes, candidate tree, precision, estimator/contrasts, resource caps, information barriers and no-automatic-retry rules remain unchanged. Old monitors, historical results and E12 are untouched. Live hardware/throughput/payload/large-transfer behavior remains untested until a separate execution instruction. The next review is the narrow launch decision only.
