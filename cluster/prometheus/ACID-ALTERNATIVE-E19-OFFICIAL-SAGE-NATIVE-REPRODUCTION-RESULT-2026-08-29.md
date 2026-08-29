# E19 official SAGE native-reproduction result

Date analyzed: 29 August 2026

Evidence role: public-release reproducibility and identifier-only overlap audit

Claim status: **native reproduction failed; no matched performance comparison is authorized**

## Frozen decision

E19 executed the complete pinned public SAGE benchmark, but the unchanged
official summarizer rejected the reproduction. All 180 cells completed
successfully and all 9,000 episode outcomes passed the frozen identity and
integrity checks. The official two-percentage-point rule passed for only 29 of
the 60 task/method/horizon means. The maximum absolute difference was 25.967
points.

The terminal decision is `stop_native_reproduction_failed`. This is a
scientific release-reproducibility failure, not an incomplete run or a cluster
failure. No cell was tuned or rerun in response, no E18-versus-SAGE performance
comparison was launched, and no protected holdout was opened.

## Immutable evidence and information barrier

- Official SAGE source: commit
  `8219029fd52e89157e05aebb998ab26f0ef46966`, tree
  `0c64066eeac97c27fee382c1879bb26968b3fd56`, with a clean worktree.
- Official checkpoint snapshot: `CLTRAY/SAGE` revision
  `1b5afbc8eeb1c8e99d9529099e1aa15f392a6346`; all six released checkpoint
  byte counts and SHA-256 digests matched the pinned release manifest.
- Immutable E19 snapshot:
  `/lustreFS/data/superworld/ckontzias/thesis/snapshots/gdp-cem-e19-9f5499887c0d2e1f`.
- Source-manifest SHA-256:
  `9f5499887c0d2e1f9808cc5f493e7f172e717bcb8db202088e89e5c29f2a1d6c`.
- Protocol SHA-256:
  `759f64b67a5c8e9d33e03c4d7027ede7edf99f1a4186236fb8f0879fc7ed0e20`.
- Run root:
  `/lustreFS/data/superworld/ckontzias/thesis/experiments/gdp-cem-e19/native-reproduction-run-20260828-9f549988`.
- Jobs 299867--299870 completed the preparation, release, data/overlap,
  Le-WM identity, and non-performance A6000 runtime gates. Array 299871 then
  completed all 180 cells, with 50 episodes per cell. Analyzer 299872 opened
  performance only after that 9,000-episode barrier closed.
- The independent cell audit found 180 unique array identities, the exact
  registered task/method/seed/horizon grid, 9,000 episodes, and matching
  source, protocol, input, checkpoint, planner, per-cell status, and output
  hashes.
- A final read-only test run against the immutable snapshot passed all 23
  tests: 16 E19 wrapper tests and seven unchanged upstream SAGE tests.
- `analysis/sha256.txt` verified every sealed analysis artifact. In
  particular, `NATIVE-REPRODUCTION-AUDIT.json` has SHA-256
  `095f11d775e0b2fb77f16bcaee8ba3aaa8eca9b799050b0f97e0b90fed0ded97`,
  `cell-results.tsv` has
  `97e7b5125480d39dc9df394cca560c60becffe01b540c2b20a62f1119d407b8c`,
  and `summary.tsv` has
  `2d493d83661b551fb9a6f7bf11c048e48655dec492bfcd282c8f3f5bf221ed7`.

The pristine upstream release audit retained the previously documented 36
manifest byte-hash failures: the Git checkout contains LF JSON while the
released hash file describes the same bytes after CRLF conversion. All 36
semantic identities, all seven unchanged upstream tests, and the complete
independent release audit passed. This was handled exactly as preregistered;
the official checkout was not edited.

The exact versioned Le-WM object checkpoints were mapped to the pinned official
SAGE runtime classes without changing any checkpoint tensor. Both tasks had
all 303 tensors bit-identical, and synthetic reference costs were bit-exact.
For Cube `lewm_generator`, the compatibility wrapper performed the same
unexpanded local-goal cache warmup already present in pinned PushT before
delegating to unchanged official Cube CEM. The mandatory preflight reproduced
the upstream uncached-rank defect and proved the cached goal bit-identical.
This made the public method executable; it did not change its model, goal,
candidates, costs, seeds, schedules, budgets, or analysis.

## Identifier-only overlap result

The public paper manifests were not episode-disjoint from E18 training:

| Task | Official-manifest episodes overlapping E18 training | Common untouched candidates |
|---|---:|---:|
| PushT | 270 | 579 |
| Cube | 84 | 280 |

The candidate split contains identifiers only and is preserved for possible
future protocol design. The nonzero overlap independently forbids a matched
E18-versus-SAGE evaluation on the official paper manifests.

## Native reproduction

Each entry below is `reproduced / released` mean success in percentage points,
aggregated over the three official seeds. The horizons are exactly the six
released paper horizons.

### PushT

| Method | H25 | H50 | H75 | H100 | H125 | H150 |
|---|---:|---:|---:|---:|---:|---:|
| Base CEM | 88.000 / 89.300 | 42.667 / 56.000 | 16.667 / 28.000 | 7.333 / 18.700 | 10.667 / 7.300 | 6.000 / 12.700 |
| Far-goal Prior CEM | 96.000 / 91.300 | 54.667 / 57.300 | 24.000 / 18.700 | 12.667 / 14.700 | 7.333 / 16.000 | 9.333 / 10.700 |
| LeWM + Generator | 88.000 / 90.700 | 74.667 / 75.300 | 72.667 / 70.700 | 62.000 / 72.700 | 62.667 / 66.700 | 55.333 / 58.700 |
| Generator Prior Top | 54.667 / 55.300 | 40.667 / 42.000 | 34.667 / 35.300 | 27.333 / 28.700 | 24.000 / 24.000 | 18.000 / 16.000 |
| SAGE | 94.000 / 94.000 | 84.667 / 81.300 | 76.000 / 81.300 | 74.667 / 72.700 | 64.667 / 68.700 | 60.667 / 64.700 |

### Cube

| Method | H25 | H50 | H75 | H100 | H125 | H150 |
|---|---:|---:|---:|---:|---:|---:|
| Base CEM | 71.333 / 66.700 | 54.667 / 56.000 | 68.667 / 62.700 | 59.333 / 57.300 | 46.667 / 40.000 | 23.333 / 26.700 |
| Far-goal Prior CEM | 97.333 / 98.000 | 76.667 / 74.000 | 82.667 / 83.300 | 78.000 / 80.000 | 58.667 / 58.700 | 40.667 / 41.300 |
| LeWM + Generator | 71.333 / 91.300 | 45.333 / 63.300 | 63.333 / 76.000 | 56.000 / 70.700 | 38.000 / 59.300 | 25.333 / 51.300 |
| Generator Prior Top | 88.000 / 88.700 | 68.667 / 69.300 | 60.667 / 60.700 | 75.333 / 75.300 | 61.333 / 60.700 | 1.333 / 1.300 |
| SAGE | 98.000 / 98.700 | 78.000 / 76.000 | 86.000 / 86.000 | 84.667 / 85.300 | 74.667 / 77.300 | 65.333 / 67.300 |

The unchanged official summarizer exited with code 1 at its first rejected
row: `pusht/base_cem/H50`, where 42.667 differed from the released 56.000.
The analyzer deliberately propagated that failure status after sealing the
complete 60-row result. Its own Slurm state is therefore `FAILED|1:0`, while
the evaluation array is complete and successful.

## Fidelity summary

| Group | Rows within ±2 points | Mean absolute difference | Maximum absolute difference |
|---|---:|---:|---:|
| PushT | 12 / 30 | 4.006 | 13.333 |
| Cube | 17 / 30 | 5.107 | 25.967 |
| Base CEM | 2 / 12 | 5.950 | 13.333 |
| Far-goal Prior CEM | 6 / 12 | 2.611 | 8.667 |
| LeWM + Generator | 2 / 12 | 11.331 | 25.967 |
| Generator Prior Top | 12 / 12 | 0.669 | 2.000 |
| SAGE | 7 / 12 | 2.219 | 5.300 |
| **All released means** | **29 / 60** | **4.556** | **25.967** |

The pass-count pattern was heterogeneous. Generator Prior Top reproduced all
12 means. Cube SAGE reproduced five of six, and Cube Far-goal Prior CEM
reproduced five of six. In contrast, LeWM + Generator reproduced two of six
PushT means and none of the six Cube means. All six Cube LeWM + Generator
means were below the release, with the largest gaps at H150 (-25.967), H125
(-21.300), and H25 (-19.967) points. Base CEM reproduced only one horizon per
task.

## Scientific interpretation and stop

E19 does not support treating the released paper table as a validated native
baseline in this thesis environment. The failure is not a blanket claim that
official SAGE never works: several released components reproduced closely,
and the full SAGE arm was within tolerance for five of six Cube horizons. The
large, systematic shortfalls are concentrated in the released
LeWM + Generator path, especially on Cube, with additional instability in
Base CEM. That heterogeneity is precisely why the frozen rule required every
one of the 60 means rather than accepting a favorable subset.

The narrow Cube cache compatibility correction resolved an upstream execution
defect and was proved not to alter tensors or planner semantics. It cannot make
the published means reproducible, and the scientific gate may not be rescued
by tuning. Consequently:

- the public paper values are not used as a validated matched comparator;
- the favorable E18 result remains development-only evidence about the frozen
  continuation planner;
- no matched H75/H150 protocol was drafted or launched;
- any future comparison would require a separately frozen common untouched
  episode split and a new decision after this reproduction failure; and
- the thesis's established positive claims remain the untouched E11 result and
  E13's compute-efficient-alternative result against the disclosed PRISM-DP
  reconstruction.

No D5, D3/D4 metric artifact, P3, P4, C1, or I1 was generated, opened, hashed,
or consumed. The E19 source, checkpoints, datasets, manifests, methods, cells,
seeds, horizons, CEM settings, tolerance, and failed outcome remain frozen.

See the [frozen protocol](ACID-ALTERNATIVE-E19-OFFICIAL-SAGE-REPRODUCTION-AND-OVERLAP-PROTOCOL-2026-08-28.md),
the [implementation changelog](E19-IMPLEMENTATION-CHANGELOG-2026-08-28.md),
and the [upstream release-defect record](E19-OFFICIAL-SAGE-RELEASE-DEFECTS-2026-08-28.md).
