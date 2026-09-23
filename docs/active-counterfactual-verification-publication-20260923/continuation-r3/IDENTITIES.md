# Frozen ACV0 R3 control recovery

- Control manifest: `4cd769916c5e6f38c64e8ded9e058ab281f826cf0ef7dee0ec79840195b93588`.
- Enabled R3 approval: `157d796cbe023d2f826b604671f58bb688722963039f6697ec31f89e1059c7a0`.
- Transport archive:276480bytes,14members, SHA256 `5d778fdfbb805f177504015c640f95e57e82563f277064dab2a97a7bc8009e86`.
- Reconciled baseline: `804cc7d8a7b00a4fdd962b7e85aa7fc3d025f3ecc84b9402cd63a43edbc88576`.
- Original scientific manifest unchanged: `c2c6fcbe8c41fed22d0fde17bcb5f8cd456a74c1cb0d77039f4df94d86e0d468`.
- Original worker approval unchanged: `e1e4b6f6d0e0d1fbb83e89d165be793128f02130647e21a1c12c5892d7d90460`.

All15 final synthetic regressions passed, including a315-task artificial full continuation and whole/member-verified final archive. Three R3 scripted test attempts are retained: one test-fixture error, then two complete15-test passes. Cumulative R2+R3 testing916.470seconds of7200 maximum; R3 peak memory at most62455808bytes, four-core affinity15, no GPU/Slurm allocations. Original scientific and R2 source closures hash-verified unchanged. New source/authority footprint is under2MB including the source export, far below250MB.

Authority is the user's direct request `FIX IT AND RESUME IT`, narrowly applied to the R2 scheduler-status fault. Original scientific authority remains separately pinned. New control paths will be:

```
/lustreFS/data/superworld/ckontzias/thesis/snapshots/active-counterfactual-verification-control-r3-4cd769916c5e6f38
/lustreFS/data/superworld/ckontzias/thesis/staging/active-counterfactual-verification-control-r3-4cd769916c5e6f38
```

The existing original R1 research run is extended only with never-created tasks. Resume24 completed suppliers/3015GPU-seconds;315 new tasks starting505. Final expected counts339 successful tasks/340 allocations, one historical failure/replacement, no new replacement or automatic retry. Original technical gate retained; original scientific settings and caps unchanged. This freeze record does not claim a launch or completed research/preservation.
