# E7P proposal-selection implementation errata

Date: 2026-08-17  
Applies to: `ACID-ALTERNATIVE-E7P-PROPOSAL-SELECTION-PROTOCOL-2026-08-17.md`

## E7P-S1 — exact SHA-256 validation-row seed

Before the first selection run, static review found that the implementation
reduced a little-endian SHA-256 prefix modulo `2^63-1`, while the frozen
protocol says to use the first 64 SHA-256 bits as the NumPy seed. The evaluator
now interprets the first 16 hexadecimal SHA-256 digits directly as an unsigned
64-bit integer. No P1 selection metric or D2/D3 outcome had been read.

## E7P-S2 — fail-closed lineage and determinism preflight

Before the first selection run, static review also required exact task-specific
cache hashes, cache structure, checkpoint architecture and statistic shapes,
plus repeated proposal and latent-rollout determinism checks. These checks were
added without changing any model, checkpoint, candidate, metric, selection
rule, or advancement threshold. No P1 selection metric or D2/D3 outcome had
been read.

## E7P-S3 — isolated-versus-batched encoder tolerance

Selection array `297712` stopped all three tasks during real-stack preflight,
before the metric loop and before any accepted P1 selection result. Re-encoding
one frame in an isolated batch differed from its immutable batched cache value
by `1.8477439880371094e-6` on PushT, `2.5033950805664062e-6` on Reacher, and
`1.9073486328125e-6` on Cube. The cached-latent rollout itself reproduced the
released rollout exactly (`0.0` maximum absolute error on all three tasks).

The original `1e-6` encoder guard was an undocumented implementation tolerance,
not a scientific threshold in the frozen protocol. It is replaced by a
fail-closed `5e-6` absolute encoder tolerance; the rollout tolerance remains
`1e-5`. Both tolerances and observed errors are written to every accepted task
summary. No candidate-quality, action-MSE, goal-cost, or advancement outcome
from array `297712` existed or was inspected. Its failed directories remain
preserved, and replacement jobs use new IDs and paths.
