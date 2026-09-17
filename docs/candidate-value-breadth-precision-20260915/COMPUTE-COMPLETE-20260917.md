# CVL-BP1 computation complete; final preservation pending

Historical intermediate status, superseded by [FINAL-REPORT.md](FINAL-REPORT.md).
The user approved content-only packaging; a separate versioned package and all
four external archives were verified without modifying permissions or deleting
the partial package. Final aggregate disclosure followed backup verification.

On 17 September 2026, direct Prometheus accounting confirmed all 300
cluster-continuation allocations completed with exit 0:0, ending at analyzer
job 301952. Including the authenticated historical prefix, the study has
450 successful coordinates and 451 attempts. The only unsuccessful attempt
remains the preserved 63-second cancellation 301578. No successful fit or
other successful coordinate was restarted.

Completion validation rechecked the unchanged scientific source, protocol,
roles, runtime authentication, original and continuation approvals, all 450
technical worker identities/seals, 18-model freeze, and train/model/evaluation
stage ordering. All passed. Charged GPU allocation time is 106,698 seconds;
CPU-stage allocation-wall time is 489 seconds (four CPUs per allocation).
Run bytes before auxiliary preservation were 1,526,098,316; maximum reported
worker RSS was 2,001,854,464 bytes. These are technical accounting, not results.

## Verified external archives

The designated D: THESIS_SSD volume was checked by label, NTFS filesystem,
volume ID `0a2f1ba9-0000-0000-0000-100000000000`, and 377,715,449,856 free bytes.
The two historical archives were rehashed and verified with the accepted
archive-member verifier, without overwriting either.

The accepted `candidate_value_backup.once` transferred and verified
`cluster-final.tar` under the existing external backup directory:

- Bytes: 1,089,720,320.
- SHA256: `90e7489d681b8cd72a175711286f3b5a2d3319a0f05910c1bfe89d7f5d9de72c`.
- Request SHA256: `a1166ab7eab3d563388bb4065ed941f71621d9b6a03c57550896d9708bca74de`.
- Transfer plus verification: 74.22869745699973 seconds.
- Completed Unix UTC: 1789678527.9079823.
- Request covers 305 newly sealed roots; the real receipt and cluster ACK exist.

This follows the explicit cluster-first, backup-after-compute amendment. It
does not retroactively claim intermediate backups were performed.

## Remaining auxiliary preservation blocker

Creating `final-preservation-20260917` in the run root with `shutil.copytree`
stopped on permission errors during metadata-preserving copies of the frozen
operational overlay into `control-source-1`. Read-only checks found all seven
destination files present and byte-identical to their source. This supports
a metadata-copy failure after data copying, not a failed scientific job.

The partial package is preserved, unsealed, and has no backup request or ACK.
No permissions were changed and no packaging retry was attempted. The main
final-artifact transfer completed independently. Final union-coverage reporting,
remaining root logs/control preservation, aggregate disclosure and scientific
handoff remain pending; no DISPATCH-FINAL marker was fabricated.

Proposed narrow continuation for user direction: use content-only copies in a
new versioned auxiliary package, retaining source metadata as a descriptive
record rather than trying to reproduce restricted filesystem attributes.
Do not alter source permissions or delete the partial package. No computation
needs to be restarted. Aggregate scientific results remain unopened.
