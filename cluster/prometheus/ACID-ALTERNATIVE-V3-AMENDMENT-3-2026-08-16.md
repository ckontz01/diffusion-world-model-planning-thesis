# ACID-alternative v3 amendment 3: bounded ACID inference batching

Date logged: 2026-08-16 16:09 EEST  
Applies to: `ACID-ALTERNATIVE-V3-MULTISEED-D2-PROTOCOL-2026-08-16.md`  
Protocol SHA-256: `c38e086ee09cbabaa9ab53246add92835d59f95173b5f35290f474abb94a4dfb`

## Timing and outcome status

This amendment was made after the fresh D2 manifest, candidate pools, shared
world-model rollouts, and physical candidate executions had been generated,
but before any D2 endpoint-score artifact or Stage-A statistic existed. All
three endpoint-scoring array elements in job `297539` failed after 22 seconds,
and dependent Stage-A job `297540` never ran. Diagnosis used only scheduler
states and the CUDA stack traces; no physical success, distance, RMSE, rank,
selection, or gate value was opened or inspected.

The failed snapshot's source-manifest SHA-256 was
`875a9cbc19dba78db1706169b7f2d8bc97a70913d82b55f793735dfe8c2df388`.
A new immutable source snapshot and source-manifest hash are required for the
endpoint-score rerun and all downstream analysis.

## Outcome-independent implementation repair

The Stage-A scorer attempted to evaluate ACID over all 50 by 300 by 5
candidate-transition tuples in one transformer call. PyTorch's CUDA scaled
dot-product-attention kernel rejected that launch with `invalid configuration
argument` on every task. This was a batch-shape limitation, not an endpoint
value, model, checkpoint, random-stream, or data failure.

ACID inference now:

1. generates the complete Gaussian tensor once, using the same frozen
   SHA-256-derived seed and tensor shape as before;
2. flattens tuples in the existing C-order;
3. evaluates consecutive chunks of at most 8,192 tuples;
4. concatenates and reshapes outputs before applying the unchanged
   de-standardization and action-residual reduction.

The preflight self-test compares chunked and unchunked ACID costs from
identically seeded generators. The Stage-A timing record reports the same
8,192 transition batch size used by the repaired path. Closed-loop Stage B is
mathematically unchanged; its 300 by 5 tuples already fit in one call, though
the same function remains capable of safe chunking.

## Artifact lineage and rerun scope

The P1 gate, fresh-D2 manifest, captured candidate pools, physical executions,
and shared-rollout/core-score artifacts are unaffected and remain immutable.
They are reused only after their hashes and the predecessor source-manifest
hash above are verified. Failed job `297539` produced no valid endpoint-score
artifact. All three task endpoint scores are rerun together under the new
source snapshot, followed by a complete new Stage-A analysis. The failed jobs
and logs remain in the audit trail.

No endpoint definition, score sign or reduction, candidate, physical outcome,
model, checkpoint, seed, noise draw, lambda, metric, bootstrap stream,
threshold, or scientific gate changes in this amendment. C1 and I1 remain
untouched.
