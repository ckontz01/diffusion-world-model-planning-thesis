# Focused artificial preparation results

Final suite: `INTEGRATION-03-RECEIPT.json` and `INTEGRATION-03.log`.
46 tests passed: all 27 reviewed artificial regressions plus 19 new correction
checks. No efficacy screen or favorable toy outcome was required.
35.875 seconds outer local scripted wall time, 22.036 seconds test time,
11.414 seconds process CPU; CPU affinity four, torch intra-op four/inter-op one.
Process RSS high water was 259,784,704 bytes. RUSAGE_CHILDREN also reported
259,784,704 bytes (a scoped child high-water value, not additional measured
coincident/node memory). The process virtual-address-space limit was 8 GiB.
The earlier aborted attempt and both native/WSL passes remain accounted.

## Deadline and preserved output

A standard-library mock child blocks for 30 seconds after writing a completed
artificial record and ignoring TERM. The production supervisor's POSIX path
with shortened test-only waits enforces a one-second absolute work deadline,
escalates to KILL, returns within three seconds, retains the completed journal
and writes supervision, deadline-fault and failure evidence. No GPU/model is
used. Prior-startup time consumes the same deadline, and an already exhausted
deadline prevents child startup. Normal completion and startup failure paths
also pass. Test-only durations never replace the 720-second production value.
Honest cleanup/uninterruptible-I/O limitations are in `CORRECTION.md`.

The nine artificial complete worker fixtures contain every required warm
timing identity, all offline lane identities, equivalence evidence, profiles,
original seals, journals, supervisor evidence and new control seals. Every
complete worker remains below 4 MB; independent acceptance succeeds, then
rejects modified supervisory evidence. Blocking/failure fixtures remain below
the same cap. Full live/archive/source reservations include logs and metadata;
the manifest itself is included in the final source byte audit.

## Accounting reconciliation

Mocked `empty, empty, RUNNING, COMPLETED` resolves the same exact ID in four
responses at times 0/5/10/15 seconds, one submission and one actual charge.
Persistent absence faults at 60 seconds after 13 polls with no guessed charge.
Wrong allocation/task IDs, duplicate rows, command errors and unknown states
are rejected; SUSPENDED remains live. A FAILED allocation with 23 elapsed
seconds carries 37 prior seconds to 60 exactly once, including when terminal
record writing itself faults. Each tested sequence has one submission only;
no failure/unresolved condition creates a replacement or advances a task.

Generated commands all use `--time=00:13:00`; nine reservations total 7,020
with a separate 7,200-second aggregate ceiling. Strict source/role/checkpoint
bindings are inherited; no task or solve is removed. AST equality confirms
the original scientific helpers, headline timer, entire inference workload
body and utility comparison function. All 1,260 CEM solves and the offline
reconciliation lane remain present. Hardware/live-runtime checks remain future
included technical work, not claims of a real CUDA execution in preparation.
