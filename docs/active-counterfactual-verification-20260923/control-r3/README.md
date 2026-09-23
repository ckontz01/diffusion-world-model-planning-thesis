# ACV0 R3: status-only control recovery

Direct user instruction: `FIX IT AND RESUME IT`, following the R2 status-fault report. This is a narrow continuation of the already authorized scientific campaign, not another experiment or resource expansion. R1 scientific source, workers, original approval, roles, grid, models, training updates, analysis and hardware association remain unchanged. No new scientific method or outcome claim.

## Reconciled boundary

R2 stopped at 2026-09-23 17:51:06 UTC with `ValueError('Unambiguous scheduler columns')`. Its final submitted allocation304220 subsequently completed successfully in160seconds. Read-only reconciliation authenticated all24 successful task outputs,25 allocations including the original23-second failed304189, and3015 GPU-seconds. No live, unknown or ambiguous submission remains. Both old controllers are inactive by PID plus Linux start_ticks. The completed technical tranche is retained.

The exact failing scheduler response was not saved by R2. Consequently we cannot identify which transient column was absent. The reproduced parser defect is that `rstrip('|')` removes empty final fields, and numeric fields were decoded before deciding whether a scheduler row was nonterminal. Slurm documents `-P` as separating fields without an extra trailing delimiter: an empty final field must not be discarded. [Official sacct documentation](https://slurm.schedmd.com/sacct.html).

## Correction and limits

The new parser preserves all12 field positions, accepting only a single optional13th empty delimiter for parsable compatibility. Polling authenticates job/task identity and known state first. Active states may have unfinished accounting. Missing/partial identity or terminal accounting gets at most8 consecutive15-second waiting intervals (the ninth incomplete observation stops). No missing field becomes a zero charge. Wrong IDs/names, duplicate records, unknown/requeued states, malformed numeric data, unavailable scheduler or log-bound violation fail-stop. Raw transitions, incomplete observations and errors are retained in a10MB technical log. This is status polling, never a retry of sbatch or scientific work.

Reuse all24 completed tasks in original order, with currently dated R3 receipts. In particular,304220 is accepted now without falsely claiming R2 accepted it. Existing R1/R2 ledgers and both STOP files remain byte-identical. The new resolution binds those exact STOP hashes and the direct user instruction; it does not waive future faults. Every submission path blocks all24 reused keys. The315 new tasks begin with collect-fit-505, and only the original remaining grid is used. Initial charges3015 plus full remaining reservations177600 =180615GPU-seconds, below unchanged220800cap. CPU stage cap21600seconds, serial GPU, original storage and per-worker caps remain enforced. Counts if complete:339 successes,340 total allocations, one historical failure/replacement, zero new replacements or automatic retries.

R3 synthetic tests share R2's two-hour cumulative local scripted-test ceiling, four CPU threads,8GiB RAM and250MB preparation artifacts. No Slurm/GPU testing, dependencies, model calls, research payload decoding, simulator replay or new source allocation. Tests cover status parsing, bounded polling, all24 immutable reused suppliers,315-only dispatch, complete logical accounting, gates, exact stops, archive members and whole-file/member verification. Old preparation test receipts remain intact.

## Finalization

The R3 adapter independently checks the full339 successful logical grid and340 allocation records, and resolves the single preserved R2 observation_unresolved event using authenticated304220 completion. It checks the original pre-analysis order, preserved tranche, both192-update model seals before final-source work, all charges and storage. The one final new-study archive includes original R1 science/run/failed-v2 provenance, old R1/R2 source/control/authority/stops/resolutions, and new R3 source/control/authority/ledger/completion. No historical study rearchive or transfer. The unchanged R1 whole/member verifier and native designated-SSD transfer are reused, never its incompatible archive entry point.

Scientific aggregates remain unread until complete acceptance and verified external preservation. AV1, historical monitors, E12 drafts, protected payloads and unrelated studies are untouched. No follow-up run or new replacement is authorized.
