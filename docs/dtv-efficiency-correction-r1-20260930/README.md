# DTV-EFF0 control correction R1 — execution disabled

This is the narrow control correction to reviewed commit
`712c39041a8242c3f45d43f95b3199bd77ca64ba`. The original source, scientific
bindings, manifest, export and receipts remain unchanged and reconstructible.
No new historical analysis or efficacy experiment is performed.

The corrected path uses `dtv_efficiency_r1`, not the historical dispatcher.
Its small `BINDINGS.json` overlay authenticates and inherits the reviewed
scientific/input bindings, changing only the finite execution-control values.
The complete corrected export will include those immutable dependencies.

- [CORRECTION.md](CORRECTION.md): exact correction and control semantics.
- [PROFILING-PROTOCOL.md](PROFILING-PROTOCOL.md): corrected execution/timing contract.
- [RESOURCE-PLAN.md](RESOURCE-PLAN.md): complete workload and finite reservations.
- `GENERATED-PLAN-FINAL.json`: nine unsubmitted commands, totaling 7,020 seconds.
- `SOURCE-DIFF-FINAL.patch`: exact reviewed-to-corrected final source diff.
  Earlier plan/diff files remain as dated preparation evidence, not current
  entry points. The final manifest authenticates all current source bytes.
- `INTEGRATION-01-RECEIPT.json`: retained aborted full-suite attempt.
- `NATIVE-CONTROL-01-RECEIPT.json`: 18 standard-library checks passed locally.
- `NATIVE-CONTROL-02-RECEIPT.json`: 19 checks passed, adding charge preservation
  when the terminal record itself triggers a control-record fault.
- `INTEGRATION-03-RECEIPT.json`: all 46 existing/new checks passed in WSL,
  including POSIX TERM/KILL escalation and full-future reservation checks.
- [PREPARATION-BLOCKER.md](PREPARATION-BLOCKER.md): preserved historical interruption.
- [RECONNECTION-RESOLUTION.md](RECONNECTION-RESOLUTION.md): authenticated
  reconnection and completed tests; no filesystem/environment repair.
- [TEST-RESULTS.md](TEST-RESULTS.md): deadline, accounting and footprint results.
- `PACKAGE-MANIFEST.json`, `SSD-BACKUP.json`, `PUBLICATION.json`: final frozen
  source, exclusive verified designated-SSD export and Git publication identities.

## Entry points

`python -m dtv_efficiency_r1.campaign --run <exclusive remote run>` generates
the plan only. `--submit` refuses the false approval before any scheduler call.
`python -m dtv_efficiency_r1.profile --job pusht-6101 --output <exclusive path>`
also refuses it before importing torch or opening research tensors.

`python -m dtv_efficiency_r1.accept --run <completed run> --output <new report>`
is the corrected independent full-grid acceptance/report path. It requires
supervision evidence, its seal and matching completed journals, in addition
to the unchanged numerical, hardware, timing-cell and allocation checks.

`python -m dtv_efficiency_r1.check_preparation --label <exclusive label>` runs
the existing 27 artificial regressions plus the new correction checks in
the existing WSL CPU environment. `--native-control-only` runs only the new
standard-library suite using existing Windows Python. It is not a substitute
for the requested full regression run or the production POSIX termination test.

After all requested checks pass and the SSD is available,
`python -m dtv_efficiency_r1.package freeze` and then `backup` create the new
exclusive manifest/export and verify whole-file and every-member hashes.
Neither command is a research launch. No fallback disk, old archive rewrite
or extra backup cycle is permitted.

Software preparation checks are complete. Final immutable identities and
whole/member backup verification are recorded in the corresponding receipts.
Research inference, GPU profiling, fitting, physics, success evaluation,
source allocation, historical reruns, monitoring and promotion remain disabled.
