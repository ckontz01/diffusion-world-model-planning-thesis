# CVL-1 executable implementation

Completion of the existing preparation, not a new method proposal. Original
preparation commit `4ed1b801b4f1f08f4517f05e2d7ec900541c43bc` was pushed and its
remote branch hash verified before subsequent implementation was committed.
Research launch is **not authorized** by this implementation or its tests.

## Implemented paths

All files below are under `cluster/prometheus/`.

|Component|Files|Responsibility|
|---|---|---|
|Original core/hook|`candidate_value_learning.py`, `candidate_value_hook.py`|Allocation, features, sampling, native target, models, weighted loss, original-solve selection|
|Fresh driver binding|`candidate_value_runtime.py`|Unchanged runtime/driver, actual-state observations, decoder checks, full-budget/cycle lifecycle, paired tail handoff|
|Sealed collection|`candidate_value_data.py`|Selected-record reader, prefixes, eight-index/two-draw replay, binary labels, persistent traces/banks and independent seal/label checks|
|Evaluator fits|`candidate_value_models.py`|Train-only standardization, three MLPs, logistic/context controls, NPZ serialization, fixed ensemble|
|Analysis|`candidate_value_analyze.py`|Within-bank variation/concordance/selection, context diagnostic, conditional four-arm episodes, source reductions|
|Authentication/worker|`candidate_value_contract.py`, `candidate_value_worker.py`, `run_candidate_value.sh`|Exact coordinates/caps/hash approval, runtime/source checks, resource receipts, fail-closed workers|
|Dispatch/backup|`candidate_value_dispatch.py`, `candidate_value_backup.py`|Serial stages, actual allocation charges, no retry, technical pilot, incremental SSD backups|
|Packaging|`package_candidate_value.py`, `candidate_value_freeze.py`|Committed import closure, LF shell rejection, deterministic archive, source/runtime/input capsule without authorization|
|Design artifacts|`prepare_candidate_value_package.py`|ID-only allocation and arithmetic execution/cost grid; no research-data/model/network access|
|Tests|`test_candidate_value_learning.py`, `test_candidate_value_pipeline.py`|Synthetic core and full pipeline regressions|

No collection/training/evaluation glue is intentionally deferred. Real deployment
verification is distinct from implemented functionality: the runtime/input capsule
and registered A6000 preflights must still pass on Prometheus before approved
collection. Synthetic success does not establish real physics, CUDA, scheduler,
storage or throughput correctness.

## Synthetic tests

The completion suite contains 25 CVL tests and retains the 22 existing single-anchor
unit/host regressions (47 total). No test opens real model/reference payloads.

- Exact 96/32/32 roles, 1,024-bank/16,384-tail ceiling, 293-job grid and caps.
- Distinct paired generator states and coupled streams across candidates.
- Collision retention, nonwinners, strict features, first-chunk/final-step success
  and incomplete-run rejection.
- Actual unchanged `FreshEpisode` and scheduled-policy class with fake physics,
  H75/H150, cycle-final, restart, budget termination and a second fresh episode.
- Collection, all five 40-epoch artificial fits, model round-trip, train-only
  normalization, context invariance, ranking and all 512 synthetic closed-loop
  coordinates. Smaller artificial train/validation populations keep regression
  fast; separate grid tests enforce the real allocation.
- Source/output corruption rejection, missing approval rejection, resource caps,
  CPU/GPU dispatch shape and member-verified backup.
- A completely mocked 293-job serial dispatch and identity-only registry projection
  that does not deserialize nonselected scientific/descriptive fields.

MLP: 87,681 parameters; three seeds form one fixed mean-probability arm. Logistic:
620 parameters. Context diagnostic: 620 stored / 398 effective parameters, not an
extra closed arm. Artificial optimizer tests are not research training.

Run with the existing local CPU environment, without installing packages:

```bash
PYTHONDONTWRITEBYTECODE=1 /home/chris/miniforge3/envs/thesis/bin/python -c '
import sys, torch, unittest
torch.set_num_threads(1)
sys.path.insert(0,"/mnt/c/Users/Chris/thesis-recovery/git-recovery-20260906/cluster/prometheus")
suite=unittest.defaultTestLoader.discover(sys.path[0],pattern="test_candidate_value*.py")
result=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())'
```

The exported closure is tested separately so success cannot depend on unrelated
files left in the working repository. Historical single-anchor unit tests remain
regression checks, not a rerun of the accepted experiment.

## Completion clarifications versus 4ed1b80

- Protocol §3 declares even/odd paired streams and preserves both binary outcomes.
- §4 adds training-only evaluator standardization and the requested context-only
  diagnostic; frozen proposer/action normalization is unchanged.
- §5 replaces the old Brier progression condition with within-bank concordance
  above chance; calibration is supplementary. No new outcomes informed this
  explicit pre-launch clarification.
- §6 and RESOURCE-PLAN specify the pilot, all 293 jobs, five CPU fits, conditional
  512 episodes, failures and total accounting.

No runtime, initializer, decoder, checkpoint or historical decision was edited.
The original WSL thesis checkout and E12 drafts are not targets. No confirmation,
GMM extension, SAGE grid, architecture search, new tail policy or expansion is
authorized. See [EXECUTION.md](EXECUTION.md) for exact deployment/approval gates.
