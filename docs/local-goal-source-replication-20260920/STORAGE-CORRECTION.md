# LGP-RB2 narrow prelaunch storage correction

The selected GPT-6 Pro chat's complete review (UI: Worked for 16m) explicitly
forbids launching v4 and directs one lossless representation correction followed
by a narrow review. This is delegated preparation authority, not execution
approval. No new proposal, source selection or outcome-driven adjustment.

## Reproduced defect, no research failure

Reviewed commit: 33433c3fc1ceb8b1623f143a1fdaed3ccb4ab68d. The downloaded review ZIP
has SHA-256 `8410e08d5405dd80502532e8fb8071cc40944ce6db6644ce6b39829d29db0e75`.
Its inspected stdlib storage_reproducer.py was run with no research imports,
payload access, cluster allocation or simulator. The original full-stage fixture
reproduced 2,335,492 bytes of EPISODE JSON plus 2,811,087 report bytes = 5,146,579
bytes, excluding endpoints/metadata/seals. The stripped fixture reproduced
5,025,251 bytes. Compact encoding of exactly the same full-stage values reproduced
1,462,787 bytes. The unchanged 5,000,000-byte worker cap therefore could not
accommodate a legitimate full-budget job in v4. Early successes cannot be a
storage assumption. The original review and v4 are preserved on THESIS_SSD.

## Production correction

lgprb2_payload.write_payload is exclusive UTF-8 text with LF, sorted keys,
allow_nan=False, compact separators and final newline. Only new RB2 EPISODE.json
and REPORT.json use it. No inherited module is edited; all fields/float values,
both copies, action/state NPZs, endpoint tests and scientific execution remain.

The existing worker guard is extracted unchanged into make_guard, adding a
pending-byte argument solely to reserve the exact final seal. write_completed
uses that actual guard before/after the report, after technical metadata with
the pending seal, and after sealing. Technical wall/CPU measurements retain
their original boundary after the report write. A post-seal failure preserves
the original seal and failure evidence, exits nonzero and is not resealed or
accepted as a successful worker. There is no retry/resume path.

## Complete regression and conservative bound

The real artificial eight-cell driver runs all 150/300 action budgets with the
actual sampler/CEM/policy and a fake vector pool, no research weights or physics.
There are 1,800 delivered artificial actions, 120 stages and 2,100 round records.
Its output is finalized through the production writer/guard. The directory must
contain exactly 19 files: eight EPISODE.json, eight endpoint NPZs, REPORT.json,
TECHNICAL.json and sha256.txt. The final seal is verified and complete size <5 MB.

A second complete directory uses the same endpoint bytes and long finite JSON
metrics: ordinary long decimals and a 24-character finite binary64 spelling.
This is serialization stress, not a simulated physical or timing measurement.
Decoded compact/indented objects compare exactly, including float.hex() bit
identity/signed zero; endpoint SHA, dtype, shape and array bytes compare exactly.
The endpoint verifier still validates the artificial states/flags/counts/schedule.
No production scientific value is transformed or rounded by this test.

The bound uses the full actual schema at maximum stages/rounds, including both
payload copies, and substitutes SIZE allowances, not stored data:

- 24 bytes per finite binary64 number (overbounds the binary32 logged values).
- 12 bytes per bounded integer, including all thirty elite indices/round;
  valid source/seed/action/candidate counters and 24/48-GiB memory counters fit.
- At least 66 encoded bytes per string, 258 per reference path, or the actual
  escaped length if longer. Frozen fixed strings/digests and all 512 metadata
  paths are checked against this scope; keys and JSON punctuation are exact.
- The same numerical/string bound plus unchanged indentation for TECHNICAL.json.
- The full eight 50,000-byte endpoint allowances, not favorable compression.
- 4,096 bytes for the final seal, checked against its exact fixed file inventory.

The test must show this complete bound <5,000,000 and records its components,
measured actual/long footprints and remaining margin. A separate real on-disk
directory at the 5 MB cap must be rejected by make_guard; the guard is not mocked.
Exclusive collision, nonfinite rejection and LF behavior are also tested.
Full exported synthetic results are publication evidence outside the manifest.

INPUTS.json, DATA-ROLES.json, GRID.json, REUSE.json and all resource caps retain
their v4 byte identities. Six models/settings, 512 sources, 1,536 GPU jobs,
12,288 episodes, 128 GPU-hour cap, 7,200-second CPU analysis, 8 GB workers and
24 GB inclusive storage are unchanged. Research execution remains disabled;
return the corrected immutable package to the exact selected reasoning chat.
