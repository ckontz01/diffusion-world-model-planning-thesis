# Preparation implementation and handoff

## Included now

- `cluster/prometheus/candidate_value_learning.py`: deterministic source-ID
  allocation, source-alias check, fixed eight-of-64 sampling, strict feature
  allowlist/time inputs, full-remaining-budget native-success reducer, compact
  MLP/logistic models, train-reference restriction, sparse-support stop,
  hierarchical weighted BCE training function, frozen ensemble probabilities,
  sampled-bank metrics and source-bootstrap interval.
- `cluster/prometheus/candidate_value_hook.py`: opt-in observer around the
  existing solve. Checks original macro identity; supports both full continuation
  and final first-only stages; substitutes only the returned selected macro;
  verifies scoring consumes no explicit/global torch RNG; restores observed
  methods even on failure. No model or environment creation.
- `cluster/prometheus/prepare_candidate_value_package.py`: generates proposed
  ID allocation and arithmetic cost artifacts; no data, model or network reads.
- `cluster/prometheus/test_candidate_value_learning.py`: synthetic fixtures only.
  No simulator, model checkpoint, source reference or historical outcome loaded.

The MLP has 87,681 parameters and the linear control 620. Synthetic optimizer
testing uses artificial feature/label arrays for two epochs, not the proposed
research training. Production training is specified at 40 epochs in the protocol.

## Tested and not tested

13 new synthetic unit tests pass (latest run 4.158s); the 22 existing single-anchor
unit/host regression tests also pass (0.245s). This is not an experiment rerun.
`git diff --check` passes. The new tests cover allocation/disjointness/aliases,
candidate winners and nonwinner inclusion, deterministic sampling, feature
allowlist/nonfinite rejection, absolute/cyclic time including restart/final chunk,
first-chunk and final-step success, censored-run rejection, hierarchical weights,
model shapes and isolated synthetic optimizer RNG, sparse-support and validation-
reference rejection, sampled-bank metrics/ties, resource arithmetic, every
decision stage across both horizons and a second synthetic episode, restoration
of hooks on error and fail-without-fallback behavior.

These tests do **not** establish actual simulator restoration, real bank identity,
decoder delivery, real policy-buffer lifecycle or collection throughput. The
accepted frozen driver/initializer is not redesigned. Before launch, a thin
adapter must bind this hook to that driver and authenticate its real dependencies.
The fake solver deliberately makes no claim of numerical equivalence to LeWM.

The preparation has no real-execution CLI, Slurm script or dispatcher. Remaining
bounded implementation before an approved launch: selected-record-only reader,
fresh-driver collection glue, owned downstream RNG handoff, persistent audit and
training-data schemas, model serialization/receipts, complete stage analyzer,
approval/source-hash gate and fail-stop resource/dispatch ledger. Their required
behavior is specified in [PROTOCOL.md](PROTOCOL.md); no outcomes may be read before
the implemented closure and contract are frozen. A scientific deviation needs
review, not silent interpretation of the current library as launch authorization.

## Checks

Run from WSL using the existing local CPU environment, without installing packages:

```text
/home/chris/miniforge3/envs/thesis/bin/python -m unittest discover \
  -s /mnt/c/Users/Chris/thesis-recovery/git-recovery-20260906/cluster/prometheus \
  -p test_candidate_value_learning.py -v
```

Inspect `git diff 9e90b5c -- cluster/prometheus/` to confirm the only experiment
implementation additions are the new CVL files. Historical single-anchor,
independent fresh-driver, proposer, adapter, initialization and decoder source
files remain unchanged. The original WSL thesis checkout and unrelated E12 drafts
are not targets of this preparation.

## Approval requested, not assumed

Review the data/sampling/time-policy target, 96/32/32 allocation, fixed models and
progression gates, 50 GPU-hour/20GB cap, CPU training limit and external-backup
requirement. Approval would cover the exact staged diffusion-only experiment and
its remaining bounded glue. It would not authorize confirmation, a GMM extension,
architecture search, a new downstream tail policy, an enlarged diagnostic or
reopening accepted historical investigations.
