# LGP-RB2 compact-evidence correction receipt — 20 September 2026

Status: **corrected, exported and synthetically verified; research execution
remains disabled**. Return this package to the selected GPT-6 Pro conversation
for its narrow execution decision. This is not an execution approval.

## Review and exact correction

The complete response to preparation `33433c3fc1ceb8b1623f143a1fdaed3ccb4ab68d`
was read in the user's existing `Analyse E11 Research Question` chat, model
`6 Pro`, URL https://chatgpt.com/c/6a8714c3-0da0-83eb-b9e5-9171a1dadcd5.
The UI reported **Worked for 16m**. It accepted allocation/grid/design but
explicitly prohibited launching v4 and directed only this storage correction.
The user's advance delegation supplies authority; no new direct user signature
or research-execution instruction is claimed.

The downloaded, inspected stdlib reproducer independently reproduced the
review's 5,146,579-byte duplicated JSON fixture, excluding all endpoint and
metadata files. The same objects compactly encoded use 1,462,787 bytes. Thus v4
could not safely fit legitimate full-budget jobs under its 5,000,000-byte cap.
This was found before research execution, not a failed research allocation.
The extracted review files are retained on THESIS_SSD in
`reasoning-storage-review-33433c3`; the original downloaded ZIP has SHA-256
`8410e08d5405dd80502532e8fb8071cc40944ce6db6644ce6b39829d29db0e75`.

Changes are limited to the new RB2 payload writer, two payload call sites,
extraction/testing of the same worker guard, final metadata/seal byte checks,
focused test discovery, and documentation. `EPISODE.json` and `REPORT.json`
retain both full copies, all fields/rounds, exact numeric values, sorted keys,
exclusive creation, finite-only JSON, UTF-8/LF and final newline. Only whitespace
is removed. Inherited writers and scientific modules are unchanged.

The actual production finalizer is exercised by the test. It checks before and
after REPORT, after TECHNICAL with the exact pending seal size, and after seal
creation. Wall/CPU sampling remains after REPORT serialization. A post-seal
failure preserves that seal and the failure record and exits nonzero; it is
never resealed as success or retried. Caps and preservation margins are unchanged.
See [source diff](STORAGE-SOURCE.diff) and
[bound/test specification](../local-goal-source-replication-20260920/STORAGE-CORRECTION.md).

## Complete-directory measurements, not partial JSON estimates

The actual artificial driver delivered all **1,800 actions**, **120 stages** and
**2,100 round summaries** across all eight full-budget cells. The production
writer, storage guard and seal verifier handled the complete **19-file** job:
eight episode JSON, eight endpoint NPZ, REPORT, TECHNICAL and sha256.txt.

| Complete footprint | Bytes |
|---|---:|
| Actual artificial full-budget directory | 1,961,847 |
| Same schema, long finite numerical serialization stress | 1,970,237 |
| Conservative complete bound | 4,083,625 |
| Margin below the unchanged 5,000,000-byte cap | 916,375 |

The bound comprises 3,677,186 bytes for both compact evidence copies, 2,343 for
indented TECHNICAL, the full 400,000 bytes allowed for eight endpoints, and 4,096
for the seal. It uses 24 bytes per finite binary64 number, 12 per bounded integer,
conservative fixed-string/path allowances and the full schema at maximum stages.
It does not rely on early success, unusually short numbers or NPZ compression.
The corresponding old indented JSON alone for the actual driver output was
5,609,928 bytes. This differs from the review's smaller fixture because the real
artificial driver includes complete episode metadata and populated statistics.

Parsed compact/indented fields and float bits (including signed zero) were exact.
Endpoint SHA-256, dtype, shape and array bytes were identical; the unchanged
endpoint verifier passed. A real on-disk directory at the cap was rejected by
the **unmocked** production guard. Nonfinite and exclusive-collision rejection
also passed. The deliberately long metrics are serialization fixtures, not
scientific outcomes or measured runtime performance.

## Tested immutable package

SSD export: `D:/THESIS-BACKUPS/local-goal-source-replication-20260920/preparation-v6`.
Archive `preparation-v6.tar`: **3,788,800 bytes / 111 file members**, whole bytes
and all members verified. v1–v5 exports and receipts remain untouched.

| Binding | SHA-256 |
|---|---|
| Source manifest | `a8fa92772272e11a279aac6c13699fc5b6da9f8160bd3264bab15e3f6bf68cec` |
| Archive | `f9e097120c3e332ca42823d30b6f6788cb398a1bba47a128dfe161db6c8421dd` |
| Protocol | `0fc90d2d34388c017bf15bdf066e2a66745bcd05e617d168a2395ee6cdfe02d5` |
| Input, unchanged | `dad31b016748698595d980cd962d632725f140a1aa1091dc7add58ef562dcca8` |
| Roles, unchanged | `daa652174a7bf2f459190d0ddcea8524218a392fc1644b345a4ce94f8fc38536` |
| Grid, unchanged | `6f911efe1c39848a91cd7d30c7436321315c1a16ce8307bd5402dd0e539618bc` |
| Reuse lock, unchanged | `7ba0fba6fd4e2ecb75cc5853628d32cc26cfb1d958f0728d733c05cc8b70aea5` |

Publication evidence outside the frozen source closure:
[manifest](storage-v6/SOURCE-MANIFEST.sha256),
[false approval template](storage-v6/APPROVAL-TEMPLATE.json),
[archive/member receipt](storage-v6/PACKAGE-RECEIPT.json),
[complete test results and per-file footprint](storage-v6/TEST-RESULTS.json).

**38 distinct tests passed**, pinned Python 3.11.10 / Torch 2.5.1+cu121 /
NumPy 2.2.6, CPU-only, one thread, no CUDA initialization: **41.022477 seconds
wall, 40.175857 process CPU seconds, 490,307,584-byte peak RSS**. Zero research
forwards, physics, optimizer steps or scheduler/GPU allocations. Host Python
3.9.6 `-B -S` imports and exported Bash syntax also passed. An initial manual
host-check command had a quoting error before imports; correcting that command
required no source, environment or permission change.

Source-only synthetic staging:
`/lustreFS/data/superworld/ckontzias/thesis/staging/lgprb2-synthetic-a8fa92772272e11a`.
It is not an execution snapshot, scientific run or controller. v5 also passed,
but its loader counted three imported fixture tests twice (41 executions).
v6 removes that duplicate discovery and asserts unique test IDs; its 38 tests
are the published final count. This did not change production scientific code.

THESIS_SSD volume `0a2f1ba9-0000-0000-0000-100000000000` was verified with
329,384,349,696 bytes free. No fallback storage or WSL filesystem repair was used.

## Unchanged scope and remaining uncertainty

The exact 512 sources, six models, four arms, horizons/seeds, endpoint, RNGs,
decoder, initialization, weighting and analysis are unchanged. So are 1,536
GPU jobs / 12,288 episodes, 460,800 GPU allocation seconds, one 7,200-second CPU
analysis, 5 MB/job, 8 GB workers, 200 MB source/control and 24 GB inclusive cap.
No retry, new case, arm, resource increase, reference-payload access or historical
rewrite occurred. Old LGP1/RB1 artifacts and E12 drafts remain unchanged.

The bound resolves the identified representation defect. It does not establish
real two-model GPU throughput, new-source physical behavior or peak worker/GPU
memory. Those remain the role of the included first-four-job tranche, only after
an explicit execution instruction. Research approval remains **false**.
