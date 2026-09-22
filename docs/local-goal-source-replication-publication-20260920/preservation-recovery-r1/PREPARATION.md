# Preservation recovery R1 — frozen operational tool

The user supplied the selected reasoning conversation's explicit R1 direction
as an attachment on 22 September 2026. `AUTHORIZATION.txt` preserves the exact
bytes (SHA256 `638e57066943747d61b43dd0c8eda55b7c2157a9e37bc1d410ee7d514ca7c810`).
This is a preservation-only reasoning direction under the user's standing
delegation, not a new direct user signature or a new scientific protocol.
Accepted fault commit: `1da99c6b9d2aae5fbed8484beebd81f64c2bb864`.

## Implementation and independent checks

The standard-library-only tool lives outside the executed source closure.
There is no Slurm, model, analyzer, simulator, training or archive-creation path.
It cannot restart an existing recovery directory. Exact original request,
source, approval, completion and archive identities are pinned. The original
failed directory is only read; an exclusive read handle on its partial rejects
an outstanding writer and holds the original stable while authenticating and
copying its prefix. The original files' hashes/mtime are checked again at final
acceptance. No failed or successful range attempt is removed.

The remote helper is supplied through configured SSH stdin, runs as one Python
3.9 process, creates no remote file or bulk chunk, and has independent wall and
RLIMIT_CPU limits. It scans the archive once to authenticate the whole file,
prefix and all 25 exact ranges. It checks source identity before/after every
scan/range. It obtains inclusive remote bytes using the already accepted frozen
metadata-only storage function. New remote recovery disk occupancy is zero;
no recovery additions are hidden from the existing 24 GB ceiling.

Ranges are received as binary stdout, with stderr separately drained to bounded
files. A range must exit successfully, have exact length and a matching on-disk
hash before it can be appended to the new assembled partial at its exact offset.
Complete-length corruption is nonretryable even if SSH also reports disconnect.
Durable progress is appended only after the assembled file is flushed/fsynced.

There are at most two attempts for a transient interruption, separated by 30
seconds; no third attempt or session resumption. The tool may stop earlier if
it cannot reconcile an uncertain remote sender within the metadata allowance.
The final whole/member verifier preserves all checks from the accepted
`lgp1_preserve.verify_archive` logic and adds phase deadline checks; no extraction.
It verifies the complete historical LGP1/RB1 archives from their original
inventories/receipts before the new final rename and recovery-only receipt.

## Finite envelope

`FROZEN.json` binds all exact files, identities and machine-readable limits.
The script enforces 50 suffix transmissions, 8 setup/metadata SSH invocations,
3,346,767,872 archive-payload bytes (conservative requested-length charging for
failed attempts), 8 GB new SSD footprint and the existing 24 GB remote ceiling.
This payload counter is not a network-wire measurement.

SSH uses BatchMode, ConnectTimeout=15, ConnectionAttempts=1,
ServerAliveInterval=15 and ServerAliveCountMax=3; existing credentials and host
verification are unchanged. No permanent configuration change.

Range watchdogs: 90 seconds idle, 300 seconds absolute. Remote range helper:
280-second alarm and at most 8 process CPU seconds. Setup: 600 seconds locally,
580-second remote alarm, up to 120 CPU seconds for full hashing or 8 for other
metadata. Sum of known CPU plus hard-quota upper bounds for unknown exits must
remain below 600 seconds; unknown charges include a one-second granularity
margin. Uncertain remote senders are reconciled only by exact tool/session/
operation argv identity and UID, never by guessed PID or unrelated processes.

Outer watchdog: 5,400-second authentication/transfer phase, up to 1,800 further
seconds for final verification, at most 7,200 seconds from first production SSD
check. It can terminate only its own local worker/child tree. Unknown remote
helpers remain separately bounded and explicitly reported, never silently retried.
Clock/session values are bound in the exclusive session record; no clock reset.

The new location is exclusively:
`D:/THESIS-BACKUPS/local-goal-source-replication-20260920/run-a8fa92772272e11a-recovery-r1`.
Original request bytes are copied unchanged, including their old destination
field. The recovery receipt explicitly maps the new location without pretending
that the first transfer succeeded. The required label/volume and 40 GB free
are checked before recovery and final acceptance.

## Synthetic verification

21 distinct artificial-only tests pass in native Windows Python. They cover
non-aligned prefix/suffix offsets and final short range, exact reconstruction,
whole/prefix corruption, source change before/during read, source EOF,
binary stdout/newline fidelity, excess stdout, transport failure retention,
authentication/host-key fail-stop, idle and absolute watchdogs, unrelated-process
survival, exclusive file creation, bad length/hash/offset rejection, the
two-attempt ceiling, exact production range arithmetic, archive duplicate/
missing/unexpected-member rejection, phase deadlines, invocation/CPU/payload
limits and complete-length corruption coincident with disconnect.

Final test wall/process CPU: 4.953 / 0.90625 seconds. Initial 20-test receipt is
also preserved; the 21st regression was added before production to prove that
complete-length corruption cannot enter the transport retry path.
No SSH invocation or research archive byte was used in preparation/tests.

Commit/push this complete frozen package and read back the remote commit before
calling `recover.py execute --commit <that exact commit>` once. On success,
require both RECOVERY-BACKUP-VERIFIED and RECOVERY-SESSION-COMPLETE, with no
failure record; the latter accounts for final sealing CPU/wall/footprint.
The scientific information barrier remains closed until acceptance.
