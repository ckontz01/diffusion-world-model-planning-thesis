# Corrected profiling protocol — no launch authorized

The scientific/timing clauses of the reviewed
`docs/dtv-efficiency-20260930/PROFILING-PROTOCOL.md` remain fixed. This file
supersedes only its execution-control values and names the new entry points.
The false approval is immutable; enabling execution requires a separately
recorded explicit instruction bound to the corrected manifest and bindings.

Nine serial workers: PushT/Reacher/Cube × scorer seeds 6101/6102/6103,
planner seed 7101, original two saved contexts per worker and all five arms:
plain, reconstructed ACID, forward, legacy DTV and D1 single-noise .25.
No source-role/checkpoint/configuration change. All numerical equivalence
checks, 5 balanced blocks × 2 repeats, original warmups and full offline lane
are retained. The grid includes exactly 1,260 complete CEM solves.

The three boundaries remain separately labelled:

- A: checker alone on identical saved predicted trajectories/actions.
- B: complete original shared-rollout cost callable.
- C: **saved preprocessed observation/history/goal to returned planner actions**.

Level C excludes raw-image preprocessing, physical action decoding and
physics. It is not full end-to-end episode latency. Original image encoding
inside the saved-input interface remains charged; no cached-latent shortcut
is introduced. Wall/CUDA-event boundaries, first operational call scopes,
warmups, CPU diagnostics, precision/defaults and order remain unchanged.
The supervisor and incremental evidence writes stay outside headline calls.

Each worker has a 720-second absolute work deadline, 60-second preservation
allowance and nominal 780-second Slurm reservation (`00:13:00`). Initial
empty accounting visibility is bounded at 60 seconds for the returned ID.
Full-future reservations, exact terminal charges, no requeue/retry/restart,
strict identity/hardware checks and fail-stop behavior are defined in
`CORRECTION.md` and `RESOURCE-PLAN.md`. Failure/partial evidence is retained.

Independent `dtv_efficiency_r1.accept` requires all nine unique successful
allocations, the original full-grid cells/offline/equivalence checks, complete
supervision seals and identical journals/profile lists. Unfavorable and small
effects remain in the all-cell report; no fastest-seed/cell selection.

The frozen utility screen is unchanged: at least 10% complete-CEM wall-time
saving vs ACID in each task/seed/context median, with at least four of five
blocks meeting 10% for each cell. Plain and forward remain reported controls.
Failure of this screen does **not** prove exactly zero speed advantage.
A favorable offline-throughput result alone cannot advance the study.
No finding automatically authorizes a next stage or promotes a model.

The one-shot result preservation plan remains: one new-study-only archive
containing source/approval, all raw control/accounting/charge records,
profiles/seals/failures and full report, without copied research checkpoints
or inputs; native designated-SSD transfer; whole and every-member verification.
Retain failed partials and seek a scoped transfer decision, with no automatic
retry, fallback disk, historical archive transfer or research rerun.
