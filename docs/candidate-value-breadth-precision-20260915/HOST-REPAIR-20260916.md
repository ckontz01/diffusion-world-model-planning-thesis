# CVL-BP1 authorized host-boundary repair

The user explicitly approved the narrow repair and launch of the unchanged
approved experiment with “yes, fix it” on 16 September 2026. This resolves the
preserved [pre-launch blocker](PRELAUNCH-BLOCKER-20260916.md), not a scientific
failure or a retry. There were no prior CVL-BP1 allocations.

## Exact source change

Move `check_frozen`, `CONFIGS` and the accepted metrics-helper hash into the new
standard-library-only `breadth_precision_freeze.py`. The learner imports those
same definitions; the dispatcher and source packager import the dependency-free
module. No NumPy/PyTorch import is needed on the controller host. No package,
environment, permission or Slurm-client change was made.

AST comparison against approved commit
`9ea4c58abaa6c907ae539020126b3f427666eedd` confirms every learning function and
the relocated freeze-check function are unchanged. The protocol, resource plan,
role manifest, scientific contract, collection implementation and runtime wrapper
remain byte-identical. All 18 fits, seeds, updates, gates, limits and the grid
remain fixed. The old source package is preserved.

## Verification

- Existing synthetic suite: 26/26 passed in the repository, 4.420s, and 26/26
  in the exported package, 2.593s. No training or real physics/model execution.
- New isolated host-boundary suite: 4/4 passed locally with `-B -I -S`; imports
  of NumPy, PyTorch and the numerical/runtime modules are explicitly rejected.
- **Actual Prometheus Python 3.6.8:** 4/4 host-boundary tests passed in 0.022s
  with `-B -I -S`. Valid freezes pass; wrong source, mutated member, incomplete
  models, changed configurations and already-opened evaluation flags still fail.
- `bash -n` passed. All 81 source-manifest entries verified on Prometheus.

## Refrozen source

Snapshot:
`/lustreFS/data/superworld/ckontzias/thesis/snapshots/candidate-value-breadth-precision-20260915-70e3838c83561b8b`

| Identity | SHA-256 |
|---|---|
| New source manifest | `70e3838c83561b8b24ea2f2c2f6875c2674d7c9b391e682c1023ba3641238975` |
| Unchanged protocol | `284b420a0b0bb183689ac217346cc9a1444ba814fc0d3c8cf064952e80ec0f9c` |
| Unchanged resource plan | `577ac440e26fb4b18d456af3581b2b0d9ddf254d0166295944dcfc0743eb938d` |
| Unchanged role manifest | `ae77734061becc33ac37d9f094c918c1c77a844da7d3d12af15471a3d2eb107f` |
| Preserved original preparation source | `ddcb207aa016b8c3306ba8b0fd53cd9008e972f53b38e4801f8e45979914e0b6` |

Source-only external copy:
`D:\THESIS-BACKUPS\cvl-bp1-preparation-oByPHd\host-repair-source-20260916`.
The new source's approval template stays false; a separate bound execution
approval records the original researcher approval and scoped repair permission.

Launch, runtime authentication, backup readiness and actual job IDs are recorded
separately after they occur. This repair record does not assert completion of
collection, model fitting or evaluation. No scientific decision is amended.
