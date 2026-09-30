# DTV-EFF0 — recovered efficiency lead, execution disabled

**Conclusion: existing comparable measurements do not support the lead.**
The artifacts are recoverable, so a narrow timing-only test remains possible.
This package neither establishes a new method nor authorizes that test.

| Evidence class | Finding | Interpretation |
| --- | --- | --- |
| Historical measured fact | D1 three-noise checker: 4.206/4.180/4.183 ms versus ACID 4.014/4.006/4.028 ms; complete solves slightly slower | No demonstrated D1 planning speedup; these are not single-noise timings |
| Historical measured fact | v3 offline DTV 0.04260 s versus ACID 0.09652 s for 15,000 sequences, excluding Le-WM/loading | About 2.266× throughput, 53.92 ms per large batch; not online latency |
| Source-level finding | Candidates share nine original epsilon-checker checkpoints, but differ in noise-bank construction and deployed weight; D1/v3 ACID RNG paths also differ | Report labels and shared weights do not establish configuration equivalence |
| Unmeasured | Exact v3 planning path and D1 single-noise production-call/solver latency | No compatibility claim pairing single-noise success with three-noise timing |
| Prediction to test | Savings persist at 300 candidates and through complete CEM despite shared world-model work | Five controls, all tasks/seeds, three distinct timing boundaries |

## Delivered records

- [CONFIGURATION-LINEAGE.md](CONFIGURATION-LINEAGE.md): exact candidates,
  architecture, normalization, reductions, noise, CEM and checkpoint lineage.
- [HISTORICAL-TIMING-RECONCILIATION.md](HISTORICAL-TIMING-RECONCILIATION.md):
  raw-priority D1/v3/E3/E6D evidence, scopes, ratios and absolute savings.
- [BINDINGS.json](BINDINGS.json): all 27 scorer checkpoints, three Le-WM
  checkpoints, saved-input locations/hashes and exact nine-worker grid.
- [PROFILING-PROTOCOL.md](PROFILING-PROTOCOL.md) and
  [RESOURCE-PLAN.md](RESOURCE-PLAN.md): fixed workload, budgets and utility screen.
- [MISSING-ARTIFACTS.md](MISSING-ARTIFACTS.md): remaining live-runtime uncertainties.
- [PREPARATION-AUTHORITY.json](PREPARATION-AUTHORITY.json),
  [PREPARATION-ACCOUNTING.json](PREPARATION-ACCOUNTING.json), artificial test
  receipts, source/byte authentication and the retained failed test records.
- `PACKAGE-MANIFEST.json`, `SSD-BACKUP.json` and `PUBLICATION.json` bind the
  new package, verified designated-SSD copy and immutable Git publication.

The initial compact ledger's task-path curation defect is preserved in
`HISTORICAL-TIMINGS.json`; use `HISTORICAL-TIMINGS-VERIFIED.json`. Historical
reports were not edited. New displayed numbers were checked against raw JSON,
not copied back into older claims.

## Production entry points

`python -m dtv_efficiency.campaign --run <exclusive remote run>` prints the
Slurm plan; it does not submit. Adding `--submit` is rejected by the disabled
approval. `python -m dtv_efficiency.profile --job pusht-6101 --output <path>`
also rejects execution before importing torch or deserializing saved inputs.
An explicit future instruction must be recorded and authenticated, bind the
package manifest and input contract, and enable a separate approval record.
The false template remains unchanged.

The worker delegates to the authentic original D1/v3 scorer callables and
released stable-worldmodel CEM; wrappers bind identity, streams and timing,
not new scoring math. Operational diagnostics remain in the hot path. Extra
hashes/traces are outside it. No compiler, quantization, cached-score shortcut,
distillation, architecture change or semantics-preserving speed optimization
was introduced. ACID remains a historical reconstruction, not official code.

`python -m dtv_efficiency.accept --run <completed run> --output <new report>`
independently checks every allocation, worker seal, exact timing cell, offline
workload, hardware and finite charge before returning all-cell comparisons.
It retains unfavorable results and grants no next stage. Its fixed utility
screen is complete-CEM wall-time saving of at least 10% in every task/seed/
context median and at least four of five blocks for every cell. Plain and
forward controls remain mandatory.

## Preparation testing and preservation

Artificial CPU tests use tiny randomly initialized models, fake rollouts and
the recovered original scorer/CEM source in the existing WSL `thesis`
environment. They never load research tensors, infer a real checkpoint, call
Le-WM, run physics or allocate a GPU. The final receipt distinguishes that
CPU environment from the pinned future CUDA runtime.
All 27 final artificial tests passed in 11.253 seconds of test time
(22.625 seconds including process/startup transport), with four CPU threads
and approximately 255 MB process RSS high water. The final receipt is
`INTEGRATION-CONFIRMED-RECEIPT.json`; earlier 20- and 26-test passes are kept.

`python -m dtv_efficiency.check_preparation --label <new-exclusive-label>`
retains each test run under a fresh receipt name. Failed fixtures and the
module-runner startup failure remain preserved, with exact corrections.
No tolerance was loosened to make a real score pass.

`python -m dtv_efficiency.package freeze` freezes only this small package.
`python -m dtv_efficiency.package backup` creates one exclusive native-Windows
archive on designated THESIS_SSD and verifies all member hashes and the whole
archive. No historical archive is copied, no fallback disk is used and no
retry/overwrite is automatic. This preparation backup is not a future result
backup. Later timing results, if authorized, require their own one-shot
new-study preservation and source-authenticated report.

No research checkpoint was deserialized in this preparation. No research
inference, fitting, success outcomes, physics, source allocation, protected
C1/I1 access, ACV/ACVM rerun or automation was performed. All old outputs,
approvals, checkpoints and E12 drafts remain unchanged.
