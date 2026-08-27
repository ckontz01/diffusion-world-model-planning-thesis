# E18 exploratory continuation-planner launch record

Launch date: 27 August 2026

## Frozen identity

- Git branch: `e18-exploratory-continuation-planner`
- Source commit at freeze: `9e27e19`
- Protocol SHA-256:
  `aff490f3f000c7d9b261632dcd3ccfc76a630b2f44e41f78832c3719607b8459`
- Immutable snapshot:
  `/lustreFS/data/superworld/ckontzias/thesis/snapshots/gdp-cem-e18-182ed1e7d1e99946`
- Source-manifest SHA-256:
  `182ed1e7d1e9994638ab1fbc773c79cac8d68858b716e67ff8969e5b2e74e29c`
- Run root:
  `/lustreFS/data/superworld/ckontzias/thesis/experiments/gdp-cem-e18/development-run-20260827-182ed1e7`

The immutable snapshot inherited and revalidated the exact E17 source
manifest, passed Python compilation, shell syntax, protocol-hash and read-only
checks, generated an exact 240-cell registry, and passed 12 container tests.
No P2 outcome or protected metric was generated or read before freezing.

The first freeze attempt stopped before snapshot creation because the login
node's default Python could not parse `from __future__ import annotations`.
The failed staging tree is preserved at
`/lustreFS/data/superworld/ckontzias/thesis/staging/gdp-cem-e18-freeze-failure-20260827-login-python`.
Commit `9e27e19` made the registry generator use the same pinned Python 3.11
container as the rest of the preflight. This was a wrapper-only execution fix;
the protocol, arms, starts, seeds, budgets, models, and gates did not change.

## Slurm dependency chain

| Job | Role | Dependency |
|---:|---|---|
| 299327 | CPU audit of all 18 E15 proposers and both unchanged E17 adapters | none |
| 299328 | Two-task fresh P2-development start-manifest array | `afterok:299327` |
| 299329 | Complete 240-cell A6000 evaluation array, at most three concurrent cells | `afterok:299328` |
| 299330 | Single task-first aggregate analyzer | `afterok:299329` |

The information barrier forbids opening any metric-bearing partial evaluation
file or evaluator log before every evaluation cell is terminal and successful
and the analyzer completes. Scheduler state, exit codes, file existence, byte
counts, and checksums remain observable for monitoring.

## Scientific scope

E17 remains a failed two-task interface preflight; E18 does not alter its gate
or reinterpret it as a pass. E18 is a separately named, outcome-informed,
development-only planner experiment motivated by E16's large exact-bank oracle
reranking headroom. It directly tests the mechanism E17 never evaluated:

- 64 first chunks, each with eight action-conditioned continuations;
- selection by the mean cost of the best two continuations;
- greedy VAD controls at 300 and compute-matched 576 candidates; and
- matched one-pass diagonal-Gaussian and direct-GMM continuation controls.

The run uses 12 fresh P2 development starts per task, two horizons, three
pre-existing learned seeds, and identical Le-WM checkpoints. It cannot provide
untouched-holdout confirmation, cannot repair E17's failed Cube coordinate
gate, and cannot establish a diffusion-specific claim unless it beats both
multimodal and unimodal continuation controls under the frozen task-robust
rules. E18 never creates or consumes D5 and never launches full-horizon
trajectory diffusion or a learned value critic.
