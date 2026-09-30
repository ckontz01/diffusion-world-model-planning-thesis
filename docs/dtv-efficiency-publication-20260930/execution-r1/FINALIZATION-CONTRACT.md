# DTV-EFF0 acceptance and preservation operations

These small operational adapters implement the already authorized final
acceptance, archive and one-shot SSD transfer. They remain outside the executed
source manifest and do not change any worker, measurement, scientific setting,
allocation or approval. No new research execution or recovery is authorized.

The frozen `dtv_efficiency_r1.accept` is the independent grid validator. The
adapter waits for all nine sealed successful tasks, a single all-complete event,
no STOP and the exact controller's exit. It reconciles one final scheduler
snapshot, reauthenticates bound files in place and invokes that validator once.
Supplemental checks cover complete files, exact contexts/first/reset evidence,
logs and full storage accounting. Any refusal preserves evidence and stops;
there is no worker resubmission or acceptance retry path.

The archive includes source once, all remote controls, the small client
operational package, the full run and the authenticated complete report. Its
own archive/request are not recursively included in themselves; the inventory
and their independent hashes authenticate that relationship. Existing bound
checkpoint/input files are never copied. All member hashes and exact archive
bytes are carried by the backup request. There is one exclusive archive path.

Native Windows streams once directly to a new directory on THESIS_SSD, with
the specified volume identity and at least 40 GB free. A partial is retained on
failure; no fallback, overwrite, resume, automatic retry or historical transfer
exists. A full SHA256, exact member set, member sizes and every member hash must
pass before the partial acquires the final name and a verified receipt. Timing
publication can only read that authenticated, verified archive afterwards.

Seven artificial preservation tests passed, including complete coverage,
duplicate/missing members, unsafe paths, truncation, whole-file tampering and
member-digest mismatch. They used no data, models, GPU or scheduler allocations.

Local scripted tests, final acceptance/archive, transfer/verification and
publication share the 600-second cumulative wall budget through the append-only
CPU-FINALIZATION ledger. The wrapper allows each action only once and refuses
after a recorded fault. Subprocess timeouts bound acceptance/archive at 180
seconds, the transfer at 120, tests at 30 and publication at 30. Allow 120
additional seconds conservatively for ancillary inspection, serialization,
Git publication and byte accounting, without exceeding 600 in total.
Maximum four CPU threads and 8 GiB remain unchanged. No GPU allocation is made
for finalization. Inclusive accounting reserves both archive copies, source
preparation and client/publication copies; all retained evidence counts.
