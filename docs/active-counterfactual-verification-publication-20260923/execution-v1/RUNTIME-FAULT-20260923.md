# ACV0 R1 transport fixed; separate controller-runtime integration fault

The user authorized the scoped transport correction with **“fix it”**. The corrected helper now sends the large configuration and source payload over configured SSH stdin; only a419-character bootstrap (subsequently431 characters after preserving the operation's `json` global) occupies the remote code argument. Local binary round-trip and envelope-bound tests passed. No scientific source was changed.

## New concrete fault

The authorized R1 preflight reached the cluster, passed exact namespace/previous-allocation absence checks and runtime-source/container hashes, then failed at invoking the pinned environment's Python directly on the login host:

`FileNotFoundError: /lustreFS/data/superworld/ckontzias/thesis/envs/hi-lewm-artifact-py311-cu121-swm006/bin/python`

The failed R1 receipt covers Unix1790162394.5285225–1790162418.9390523. This is not a research worker failure. Its read-only checks occurred before any source/control directory creation, enabled approval, controller or allocation.

Narrow read-only diagnostics explain the failure:

- The environment's Python is a symlink to `/opt/conda/bin/python`, absent on the host but present in the already pinned container. Its `pyvenv.cfg` explicitly identifies this container-created Python3.11.10 environment.
- Invoking that environment inside the existing container, with no GPU passthrough and a read-only research mount, successfully imports pinned NumPy2.2.6. However, `sbatch`, `sacct` and `apptainer` are absent from its command environment.
- The host has Slurm commands and Python3.9, but importing NumPy there fails. It is not the required compatible NumPy/fitting environment.

The unchanged dispatcher needs host Slurm throughout and imports `fitting.model_freeze` (and therefore NumPy) at the post-fitting seal gate. Launching bare host Python would postpone the fault until after research allocations; launching the pinned container directly would lose its scheduler commands. Neither unverified route was used. This exposes a preparation/runtime-integration gap, not grounds to install dependencies, modify permissions, or silently patch the approved source.

## Preserved status

No snapshot, control or run has been created by these operations. No enabled approval exists. Zero submitted/live/terminal/ambiguous ACV0 jobs; zero GPU or CPU-job allocation seconds; sources490/545 not started. No research checkpoint, reference payload or simulator was used. The false template and all frozen source members remain unchanged. The original error206 receipt, zero-allocation reconciliation, R1 test/failure records and runtime diagnostics are retained.

## Scope needed to continue

A controller-runtime integration correction must be authorized and independently checked before any allocation. A narrow candidate is to keep the scheduler controller on host Python3.9 while executing only the authenticated model-sealing operation through the existing pinned container/Python/NumPy environment. That would require revising and re-freezing the dispatcher integration (not scientific settings) and approving its new immutable identity. No such source revision, bridge, dependency installation or renewed preflight/launch has been implemented here. This report is not another general approval request or a proposed new experiment.
