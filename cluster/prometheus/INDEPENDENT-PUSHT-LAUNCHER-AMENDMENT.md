# Launcher-only amendment, 6 September 2026

Collection job300326 produced and validated all6000 independent references.
The first stage array300327 failed before entering the worker main function:
Apptainer --cleanenv removed SLURM_ARRAY_TASK_ID. The code did not pass the
index as an explicit argument. No final planner was invoked, no scientific
outcome was created or inspected. Array300327 and dependents300328/300329
were stopped; their logs and submission record are preserved.

Correction: expand the scheduler index in the host shell and pass --index
explicitly across the clean container boundary. Add a mock clean-environment
regression and an actual two-element CPU array handoff test. No collector,
model, initialization, outcome rule, sample size, alpha boundary, stopping rule,
reference seed, horizon, checkpoint, or task allocation changes.

The already validated reference data are reused byte-for-byte in a new
execution directory, with a new source/registry binding and explicit provenance.
The original collection and failed execution directory remain unchanged.
