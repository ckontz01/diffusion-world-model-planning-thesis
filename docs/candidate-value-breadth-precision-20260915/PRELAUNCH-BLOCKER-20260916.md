# CVL-BP1: pre-launch controller dependency blocker

16 September 2026 (Asia/Nicosia); remote diagnostic clock
15 September 2026, 21:25 UTC. **No study allocation was submitted.**

## Approval preserved

The researcher approved the exact preparation at
`9ea4c58abaa6c907ae539020126b3f427666eedd`, including its fixed scientific grid,
resources, stage barriers and no-retry rule. The supplied approval text has
SHA-256 `5fd32eaa897f8a468ac7516f091f5eaaed16e41df9e88afac826c25ff53927bc`.
That approval is preserved; this record does not amend the scientific protocol
or claim the experiment has run.

The prepared external source manifest remains
`ddcb207aa016b8c3306ba8b0fd53cd9008e972f53b38e4801f8e45979914e0b6`.
The reviewed code, protocol, allocation and historical decisions are unchanged.
The external D: volume is mounted as `THESIS_SSD`, with 378,184,638,464 bytes free
at the readiness check, exceeding the approved 40 GB reserve.

## Concrete incompatibility

The published dispatcher is intended to run on the Prometheus login host,
where the Slurm clients are available. At
`breadth_precision_execute.py:87`, before the first evaluation allocation, it
imports `check_frozen` from `breadth_precision_learning`.

That module imports NumPy at module scope and imports `candidate_value_data`,
which imports `candidate_value_learning`, which imports PyTorch. The freeze
check itself only needs standard-library hashing/JSON and the existing contract.

Read-only checks on `controller1` established:

- `/usr/bin/python3` is Python 3.6.8; neither NumPy nor PyTorch is installed for it.
- `/usr/bin/python3.9` is Python 3.9.6; neither package is installed for it either.
- The accepted environment's `bin/python` points to `/opt/conda/bin/python`,
  which is available inside the accepted container, not as a usable host path.
- A read-only `/bin/sh` invocation in the accepted container found Python, but
  no `sbatch`, `sacct` or `scancel` on its configured PATH. No GPU or model was used.

Consequently, starting the host controller as prepared would knowingly risk
completing all training collection/fits and then failing at the evaluation
freeze barrier. Moving the controller into the container is not a verified
drop-in solution. No package installation, permission change, Slurm-client
mount workaround or source modification was attempted.

This is a preparation implementation defect, **not scientific underperformance**.
The synthetic and exported tests used a workstation environment containing both
packages; they did not exercise the controller's dependency-free host boundary.

## Accounting and preservation

- Slurm jobs submitted: **0**. No ambiguous submission or live study allocation.
- GPU/CPU Slurm allocation charges: **0 / 0**; the approved envelope is untouched.
- No remote research worker, dispatcher, new run directory, collection,
  evaluator fitting, new outcome access, simulator or world-model call started.
- Only source/approval metadata, interpreter/package availability, container
  executable availability and external-volume readiness were inspected.
- No new reference payload was opened; reserved closed-loop and 1600–5999
  payloads remain unopened. The three E12 drafts remain untracked and untouched.
- The preparation source copy remains on the external SSD. This blocker record
  and the original approval text are backed up there separately; there are no
  partial research outputs to reconcile or discard.

## Narrow recovery decision requested

Authorize a **pre-launch standard-library-only freeze-check repair**: separate
the unchanged model-seal validation from NumPy/PyTorch imports, add an isolated
host-dependency regression test, refreeze the resulting technical source, bind
the unchanged approved scientific scope/resources to its actual new source hash,
then launch the original fixed grid. No dataset, model, normalization, loss,
stream, candidate, update count, gate, limit or scientific endpoint would change.

No retry is proposed: there has been no allocation or research execution.
No repair or revised-source launch is silently authorized by this record.
