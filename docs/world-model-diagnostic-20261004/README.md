# WM-DIAG0: review package, preparation-v1

Outcome: runnable **artificial components**, not a complete launchable research campaign. All research access and execution remain disabled. No checkpoint forward, research fitting, physics, new payload read, label collection, Slurm allocation or monitor was performed.

Read [CLAIM-AND-PRIOR-ART.md](CLAIM-AND-PRIOR-ART.md), [COMPATIBILITY.md](COMPATIBILITY.md), [PROTOCOL.md](PROTOCOL.md), [ANALYSIS.md](ANALYSIS.md) and [RESOURCE-PLAN.md](RESOURCE-PLAN.md). Exact IDs and rows are in ROLE-PROPOSAL.json and SOURCE-ROWS-PROPOSED.json, both **PROPOSED_NOT_ALLOCATED**.

Implementation is ../../wm_diag0/. Run from the repository root using the existing native Python, with no installation:

```powershell
& 'C:/Users/Chris/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B wm_diag0/bounded_run.py UNIQUE-ARTIFICIAL-LABEL 'C:/Users/Chris/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B -m unittest wm_diag0.test_components wm_diag0.test_package -v
& 'C:/Users/Chris/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B -m wm_diag0.analysis docs/world-model-diagnostic-20261004/ARTIFICIAL-ANALYSIS-INPUT.json --artificial
& 'C:/Users/Chris/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B -m wm_diag0.resource_plan
```

Scripted tests must use the bounded runner; the estimator command above illustrates its entry point and should also be wrapped when used as a test. No scientific conclusion follows from the artificial fixture.

## Blocking launch gates

1. Explicit review/allocation of the 60 unused PushT and 60 proposed Reacher parents. The PushT proposal consumes all remaining eligible old references; no allocation has occurred.
2. Exact released DINO-WM no-proprioception weights, SHA256, configuration, training-role overlap and native temporal/action/S0 contracts. A public release listing is not an authenticated runnable artifact.
3. Production bridges for each frozen backbone, native fresh origin plus complete replay, native endpoint verification, branch-owned native CEM tail and immutable selection/outcome separation. These are explicitly absent, not disguised by the array validator.
4. Resolve the Reacher circular-coordinate proxy versus raw-qpos native endpoint convention before freezing a launch contract. No endpoint substitution is allowed.
5. Final exact model-call/storage accounting against authenticated DINO metadata; freeze source closure, test interfaces artificially, Git/SSD preserve and receive a separate explicit execution instruction.

Existing completed studies and paused monitors remain unchanged. No practical repair/router is implemented. A finite future workload is proposed, not authorized.
