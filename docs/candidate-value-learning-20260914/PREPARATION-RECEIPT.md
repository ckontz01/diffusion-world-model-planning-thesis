# CVL-1 completion and publication receipt — 14 September 2026

**Prepared, implemented, tested, source-authenticated and published. Not launched.**
This receipt records preparation facts, not scientific outcomes or launch approval.

## Published source

Original requested commit `4ed1b801b4f1f08f4517f05e2d7ec900541c43bc` was pushed to
`candidate-value-learning-preparation-20260914`, and `git ls-remote` matched it.
Subsequent implementation was preserved in
`b44fc4c096fd2a84967ea3c11dbb239653a27b63`, also pushed and remotely verified.
This receipt is a later documentation-only commit; the deployed scientific source
and protocol remain the exact `b44fc4c` package.

Immutable review links:

- [Executable protocol](https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/b44fc4c096fd2a84967ea3c11dbb239653a27b63/docs/candidate-value-learning-20260914/PROTOCOL.md)
- [Resource plan](https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/b44fc4c096fd2a84967ea3c11dbb239653a27b63/docs/candidate-value-learning-20260914/RESOURCE-PLAN.md)
- [Implementation map](https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/b44fc4c096fd2a84967ea3c11dbb239653a27b63/docs/candidate-value-learning-20260914/IMPLEMENTATION.md)
- [Registered worker](https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/b44fc4c096fd2a84967ea3c11dbb239653a27b63/cluster/prometheus/candidate_value_worker.py)
- [Pipeline tests](https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/b44fc4c096fd2a84967ea3c11dbb239653a27b63/cluster/prometheus/test_candidate_value_pipeline.py)
- [Exact grid](https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/b44fc4c096fd2a84967ea3c11dbb239653a27b63/docs/candidate-value-learning-20260914/COST-PLAN.json)
- [Launch/packaging commands](https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/b44fc4c096fd2a84967ea3c11dbb239653a27b63/docs/candidate-value-learning-20260914/EXECUTION.md)

## Verification actually performed

- 25 CVL tests + 22 retained single-anchor unit/host regressions: **47/47 pass**
  in the working repository (18.484s final run).
- The exported committed closure also passed **47/47** (18.607s); every source
  manifest member verified before and after testing, every Python file parsed,
  and the exported Bash script passed `bash -n`.
- Synthetic end-to-end collection, five artificial fits, ranking validation,
  512 closed-loop coordinates and a mocked complete 293-job dispatch passed.
  Fake physics is not a claim of real simulator/CUDA equivalence.
- Prometheus metadata/runtime capsule generated successfully using host Python
  3.6.8, without loading any research model or opening a reference NPZ. Its 160
  selected records have 160 distinct source keys. Ten runtime dependency files,
  one environment tree and one code/config tree were pinned. Nonselected registry
  outcome/descriptive fields were lexically skipped, not deserialized or exported.
- Source tar matched byte-for-byte between Prometheus and the external SSD;
  capsule backup hash matched and its selected-identity/source/protocol gates
  were independently rechecked locally.
- Existing proposer/LeWM/adapter, initializer/driver/decoder, historical results
  and the original preparation allocation were not edited. Original WSL checkout
  still shows the same three E12 draft files as untracked; none was modified.

Local CPU environment: `/home/chris/miniforge3/envs/thesis/bin/python` in WSL
Thesis-Ubuntu. Synthetic tests are not research training or experiment reruns.

## Immutable identities and storage

|Artifact|SHA-256|
|---|---|
|Source manifest|`15030f427bed815e1fc4041cce2283e22ddc9713f649703b7983e4bfa171c556`|
|Protocol|`6451cbd44e3fdfd430b3f6d1c69eb49a14bb493beaa1acdedee971a73978ff2c`|
|Source tar|`66120802c78ed20b8eb3fed9020795d79ac7f01d5b4acd0a3ded9c9272c07d31`|
|Launch capsule|`e41d49657a93fab4e1bee6530e4fdcb32b08f91eaeee1973d99736abcbc292d6`|

Source snapshot (56 archive members; tar 593,920 bytes):

`/lustreFS/data/superworld/ckontzias/thesis/snapshots/candidate-value-learning-20260914-15030f427bed815e`

Capsule (57,026 bytes) and source archive:

`/lustreFS/data/superworld/ckontzias/thesis/staging/candidate-value-learning-20260914-15030f427bed815e/`

External backup, on verified volume `D:/THESIS_SSD` with approximately 379GB free
at preparation time:

`D:/THESIS-BACKUPS/candidate-value-learning-20260914/source-b44fc4c/`

This contains `source.tar`, the verified exported closure, and `LAUNCH-CAPSULE.json`.
No raw research artifacts were downloaded. The new remote source directories and
source/capsule files are non-writable. Existing historical paths were not changed.

## Exact bounded launch candidate

96 train / 32 ranking-validation / 32 closed-loop development references. Four
fixed anchor slots at each H75/H150. At most 1,024 banks, 8,192 sampled candidate-
index rows and **16,384 binary outcomes = 128 × 2 × 4 × 8 × 2**. Physical-action
uniqueness is measured separately; unavailable anchors are not replaced.

Both tail outcomes are retained. Three MLP seeds are one fixed ensemble. Logistic
is the minimal learned closed-loop control; the context-only diagnostic is not
a fifth arm. Closed loop is **32 × 2 horizons × 2 evaluation draws × 4 arms =
512 episodes**, with zero extra exact repeats and no best-seed selection.

First training tranche: references **1444, 1314, 767, 1481**, both horizons:
eight jobs / at most 512 tail outcomes, already inside the full allocation.
It checks technical correctness, time, memory and storage only, not success.

Registered maximum: **290 GPU jobs + 3 CPU jobs = 293**. Fixed reservations total
48h10m GPU plus two CPU allocation wall-hours. Hard ceiling **50 GPU-hours**
includes preflights, collection, closed loop and failed/technical allocations;
**two CPU hours** includes five evaluator fits and both analyses. **20GB remote**
includes new outputs, failures, logs/temp files, terminal evidence and a 50MB
source/control reservation; **40GB external free space** is separately required.
Control-node packaging/checksum/transfer time is not misrepresented as CPU
training time. No automatic retry, extra case, new seed or cap increase.

Within-bank advancement: technical integrity and training support, at least ten
informative validation references, positive selected-success difference versus
continuation, and mean informative concordance above 0.5. Calibration is
supplementary. This pre-outcome completion clarification replaces the preparation's
Brier gate; it is explicit for review, not a result-dependent revision.

## Readiness and remaining decision

Source/input/runtime **metadata authentication is complete**. The source package's
earlier pending-deployment text describes the state when it was frozen; this
receipt supplies the completed external capsule without modifying that snapshot.

**No new real labels, research training, simulator episodes or Slurm/GPU jobs were
launched.** Capsule `researcher_approved` is false. No APPROVAL.json or experiment
run directory exists. The backup watcher and dispatcher were not started.
Actual pinned-runtime A6000 preflights and real throughput remain untested and
are mandatory inside any subsequently approved envelope. Source authentication
does not substitute for those checks or establish efficacy.

The next review is the bounded launch decision for this exact package, not another
proposal or a reopening of the completed 32-reference diagnostics.
