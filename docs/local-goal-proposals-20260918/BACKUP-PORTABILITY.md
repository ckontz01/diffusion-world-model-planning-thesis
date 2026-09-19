# Final-preservation-only portability correction — 19 September 2026

All LGP1 computation completed before this correction: 204 successful
coordinates, 207 attempts (three preserved historical failures), 15,615 GPU
allocation-seconds and one 16-second CPU analysis. No computation is repeated.

The accepted archive verifier produced `final.tar`, 1,734,420,480 bytes,
1,733 members, SHA256
`24609c83f6c21d99edc579229ab990db184c6e0fa1133ebad4336882c35189fd`.
The original source/run/control chains and all their artifacts are included.
Its original immutable source remains unchanged.

## Exact failure and correction

The first Windows backup invocation stopped at `Request namespace`, before
reading the remote request, creating its destination, or transferring bytes.
`str(Path('/lustreFS/...'))` uses backslashes on Windows, while the authenticated
remote request uses Linux forward slashes. No partial archive or backup claim
was created. The exact run destination was verified absent.

Only remote-path validation in `lgp1_preserve.py` changes. Use `.as_posix()`
for the remote root and require the exact canonical Linux namespace, a
16-character lowercase hexadecimal run ID, and the fixed request basename.
Reject traversal, duplicate separators, backslashes and unexpected suffixes.
Volume UUID/label/free-space checks, exclusive creation, request/archive binding,
byte/member verification, preservation of partial failures and no-fallback
behavior are unchanged. This patch is used only for final Windows copying;
the original cluster archive creator and all scientific workers stay frozen.

Four focused synthetic tests passed on bundled Windows Python 3.12.14,
including emulated Windows path behavior, invalid namespaces and tampered/missing
archive members. The separate operational package and authorization bind the
actual source/manifest, archived request and archive hash before transfer.
This uses the user's standing 19 September technical-repair authorization;
it is not a claim of a new user approval or authority for another allocation.

## Other finalization observations

The initial final-authentication helper imported four Python bytecode caches
without `-B`, then correctly stopped because those extra files violated exact
source coverage. The four generated files (33,377 bytes) were moved unchanged
to `final-helper-bytecode-preserved-20260919` in the current control directory,
with hashes and an incident record. No sealed source bytes changed. The helper
now disables bytecode writes itself and is invoked with `-B`. All source and
worker seals then passed. The preserved incident is included in the archive.

The attempted local synthetic-suite rerun did not start because the existing
WSL Python executable returned `Input/output error`. No dependency installation,
environment mutation or permission change was attempted. This is separate from
healthy SSH transport and completed cluster work. The original 47-test results
in checkout/export/pinned runtime remain intact; this correction has its own
four stdlib-only regression tests.

Research results remain unread until actual final SSD verification. No new
scientific gate, seed selection, interpretation change, or follow-up is enabled.
