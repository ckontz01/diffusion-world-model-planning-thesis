# LGP1 deterministic sampler / saved-final validation recovery — 2026-09-19

Authority: the user's explicit "fix and resume", following the report of job
301980's CUDA cumulative-sum exception. This authorizes this one technical
recovery, not an automatic retry loop or a scientific change.

## Established failure and completed work

Fresh Slurm accounting:301977 FAILED1:0/46s,301979 COMPLETED0:0/3388s,
301980 FAILED1:0/252s. Total charged GPU allocation time3686s,CPU-stage0s.
The old detached controller is absent. No later fits or evaluations started.

The sealed cache from301979 is complete and reused in place, without copying
or rerunning it. Cache seal SHA-256:
`7923e9590e3c520c44ac3a36c2bf9000f6d91a4b06a6333f528f3930a4580734`.
Its source manifest is `b96b797315320184c3289e09d7a5c43f898ef2432ba57deb86b1a8094fb7653a`;
its actual run approval hash is `aba207913b929334adaf76c36b0b974b4338de6d800dad5b9f27b2209df8d672`.

The GMM8301 final checkpoint was written after **12000updates** and before
validation. Its fixed-final metadata and actual file hash agree:
`2283b7aef1b38d50d546beeb6f73ad36e9fbc6f1fb1bc5001b830d182f062286`,53364030bytes.
The preserved failed-fit seal is
`e28e6e56366d8ea3c90de6fed9fd91a5532dfd13da8a504e87027fd2e8fe454d`;
the prior dispatch ledger hash is
`90c18122dbdb134732f503c6d7cb8fbb12f85b1f571817a2c68bf795b963cd4a`.
No training-loss/validation-effect-based decision was made. Partial metrics and
the interrupted optimizer state were not inspected to select a continuation.

Job301980 failed in the first validation candidate-sampling call:
`logits.softmax(-1).cumsum(-1)` invokes a CUDA kernel unavailable under the
required strict deterministic mode. The optimizer loop had completed. Therefore
the correct recovery is validation of the fixed final model, not model retraining
or invented optimizer-state resumption.

## Narrow sampler correction

Keep GPU softmax, FP32 probabilities, the inverse-CDF categorical rule, exact
last-CDF entry1, one shared mode per trajectory, tie inequality and GPU RNG
order unchanged. Move only the eight-probability cumulative sum to CPU and move
that tiny result back to the original device. Strict deterministic algorithms
remain enabled; no warn-only mode or temporary disabling is used. No RNG calls
are added. CPU prefix arithmetic is now explicit; no claim of bitwise equality
to an unavailable nondeterministic CUDA prefix implementation is made.

Synthetic checks use the actual sampler, fixed logits, repeated local generators,
and an explicit reference implementation. A synthetic GPU check executes inside
the already authorized validation allocation, before research model evaluation;
it consumes no extra scheduler allocation and no research model or simulator.

## Validation-only continuation

The new validation-only function authenticates the old failed-fit seal and exact
final checkpoint; verifies family,seed,12000updates,1536000row presentations,
cache seal and normalization arrays; loads it without an optimizer; and copies
the original checkpoint/metadata bytes exclusively into the new fit completion
root. Post-validation file and tensor checks require unchanged weights.

The unchanged validation loop is shared with normal fits. It restarts its fixed
seed+200000 validation stream from the beginning because the failure occurred
in the first sampling call, with no completed validation report. This repeats
unfinished validation only, with no checkpoint or seed selection.

The new allocation records zero optimizer updates and zero training row
presentations. GMM8301 retains its historical12000updates/1536000presentations.
The other five previously unsubmitted fits each perform their original12000
updates. Final aggregation requires72000unique model-training updates and
9216000presentations;60000updates/7680000presentations occur in the new chain.
No completed cache or trained model is regenerated.

## Reservations, identity, preservation

The saved model's original allocation used252seconds. Limit its validation-only
allocation to14100seconds (235minutes), so the combined original+validation
maximum14352seconds remains below that fit's original14400seconds. The other
five fitting allocations and all technical/evaluation/analysis limits are unchanged.

New remaining reservations:14100+5*14400+196*1200=**321300GPU-seconds**.
Including all3686prior seconds gives **324986**, below336000. The final CPU
allocation remains4CPU/8GiB/7200s. New allocations:202GPU+1CPU. With the three
prior GPU attempts, the study will have205GPU+1CPU attempts, of which two GPU
attempts failed. Successful scientific coordinates remain203GPU+oneCPU.
The completed cache is part of prior charges and is not double-counted.

A fresh exclusive source/output/control namespace is used. Preflight verifies
all three exact terminal jobs, absence of old controllers, sealed cache/model
identity, unchanged input lock and no unexpected prior LGP1 job or run namespace.
Mixed provenance is explicit: only the exact saved cache is read from its old
root; the validation-only completion carries the original GMM checkpoint hash.
All other workers bind the new source/approval. All six models still freeze
before any technical/main episode; no evaluation has been advanced early.

Both earlier run/source/control histories remain intact and count toward the
unchanged12GBtotal,5.9GBworker,200MBsource/control caps. Archive inventory and
SSD verification include both histories and the new controls. No historical
artifact is deleted. SSD backup remains after cluster compute; cluster progress
does not depend on local connectivity. No additional automatic recovery is granted.

No data roles, targets, normalizers, model dimensions, training seeds/updates,
candidate/refinement budgets, action support, decoder, initializer, success
predicate, reference set, comparison or interpretation changes are made.
