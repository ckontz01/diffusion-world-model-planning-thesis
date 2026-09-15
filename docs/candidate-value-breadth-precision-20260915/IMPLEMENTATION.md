# Implementation and future operator entry points

## Prepared implementation

All new files are separate from accepted CVL-1 and objective/capacity sources.

- `breadth_precision_contract.py`: ID-only roles, exact streams/sampling, task
  grid/count model, fixed budgets and explicit future-approval authentication.
- `breadth_precision_data.py`: unchanged runtime interface, saved C-bank/prefix
  comparison, two/four-draw label handling, accepted decoder/trajectory checks,
  strict old/new saved-data readers.
- `breadth_precision_learning.py`:18 fixed-update original-capacity fits,
  common authenticated normalizer, pre-evaluation model freeze, all-model common
  evaluation and source-paired allocation contrasts. Only pure score/metric/
  summary helpers are imported from the accepted objective/capacity study;
  its data readers, fits, recommendation and execution entry point are not called.
- `breadth_precision_execute.py` / `run_breadth_precision.sh`: fail-closed
  worker and serial Slurm controller, existing A6000/defq configurations,
  read-only inherited runtime/data mount, bounded writable **new-run** mount.
- `prepare_breadth_precision.py`: metadata-only count output and authenticated
  source closure builder. Copies original62 source entries byte-for-byte;
  new source uses LF; no original source replacement. Approval template remains
  false. Exact source, protocol, role and grid hashes precede later submission.
- `breadth_precision_backup.py`: new-namespace external-SSD companion around
  the accepted incremental archive writer/verifier; no execution authority.
- `breadth_precision_infra.py`: three exact pure helper function bodies from
  the accepted storage-race-repaired dispatcher. Kept separate because the old
  immutable source predates that repair; no historical dispatcher is replaced.
- `test_breadth_precision.py`: focused synthetic cases. Tests never call an
  optimizer, frozen neural checkpoint, planner, world model or physics simulator.

Use the existing Python3.11+/Torch/NumPy environment. The cluster worker uses
the accepted pinned PyTorch2.5.1/CUDA12.1 container and Python environment;
CPU allocations have no GPU resource and hide CUDA devices. No dependency or
permission changes are required. Hardware execution has **not** been tested by
this preparation; synthetic passing is not a claim of real rollout completion.

## Preparation-only commands

From this repository (set `PYTHONDONTWRITEBYTECODE=1` to keep source closures clean):

```bash
PYTHONPATH=cluster/prometheus python cluster/prometheus/prepare_breadth_precision.py plan
PYTHONPATH=cluster/prometheus python -m unittest cluster/prometheus/test_breadth_precision.py -v
bash -n cluster/prometheus/run_breadth_precision.sh
```

The plan prints all450 future execution coordinates but submits nothing.
The test uses temporary synthetic arrays/archives and the identifier manifest.

## Source-only freeze for a later approved run

The accepted upstream source path is
`/lustreFS/data/superworld/ckontzias/thesis/snapshots/candidate-value-learning-20260914-521a0e6627c570ff`.
Its manifest SHA-256 is
`521a0e6627c570ffa30d12adc63f92cf9ba76dee2c9bc4c59d24f4982f4f45f2`.
The accepted original runtime capsule SHA-256 is
`a1f152f66a1a6f1b766691b4a12c18fc6489d921f82ca7fbca29d86714b21469`.
The new protocol/roles are pinned by a complete new source manifest; inherited
bytes are checked against a copied `UPSTREAM-MANIFEST.sha256`. Do not rebuild
the old capsule or fit new normalization statistics.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=cluster/prometheus python \
  cluster/prometheus/prepare_breadth_precision.py freeze \
  --repo "$REPO" --upstream "$ACCEPTED_SOURCE" --out "$NEW_SNAPSHOT"
```

Here `$REPO` is this reviewed commit, `$ACCEPTED_SOURCE` is the exact path above,
and `$NEW_SNAPSHOT` must be a new unused source directory. This command only
copies/hashes code and metadata; it does not touch reference payloads or models.
It prints exact source/protocol/role hashes and the derived new run path.
Do not alter the snapshot after creating its manifest. No false claim of OS
immutability: hashes enforce source identity; permissions are not changed.

## Guarded execution commands — NOT authorized by preparation

After an explicit launch approval, create an external approval JSON from the
false template, containing `researcher_approved: true`, the exact three hashes,
the exact `caps` object, and the path of the existing capsule with the pinned
SHA above. The source template itself remains false and untouched. Keep the
approval/control files under the reviewed study namespace, within the50MB
source/control reserve. Backups must be ready before dispatch.

```bash
# WSL Thesis-Ubuntu, mounted external THESIS_SSD:
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$REPO/cluster/prometheus" python \
  "$REPO/cluster/prometheus/breadth_precision_backup.py" \
  --run "$RUN" --approval "$APPROVAL" --source-sha "$SOURCE_SHA"

# Prometheus, pinned runtime Python; do not start before exact launch approval:
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$SNAPSHOT/cluster/prometheus" python \
  "$SNAPSHOT/cluster/prometheus/breadth_precision_execute.py" dispatch \
  --source "$SNAPSHOT" --run "$RUN" --approval "$APPROVAL"
```

These are operator templates, not commands executed for this preparation.
Do not replace placeholders with a broad output root. `$RUN` must exactly equal
the contract's study parent plus `run-<approved-source-hash16>` and must not exist
when dispatch starts. The dispatcher has no resume/retry entry point.

## Verification record

The committed preparation receipt records actual synthetic test results and
publication status. No real input NPZ, old validation payload, reserved closed-loop
payload or1600–5999 payload was opened by this preparation. The only newly
inspected research metadata was the authorized identifier-only role projection;
cost planning reused accepted aggregate accounting. Historical result/source
files remain unchanged; only a new README history entry links this preparation.
