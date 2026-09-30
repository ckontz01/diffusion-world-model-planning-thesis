# Preparation blocked by designated SSD disconnection

The first combined artificial suite attempt returned exit 135 after
27.359 seconds with no stdout. That attempt and its empty output are retained
as `INTEGRATION-01-RECEIPT.json` / `INTEGRATION-01.log`; no success is claimed.

A subsequent narrow startup diagnostic reported:

`Failed to attach disk 'D:\WSL\Thesis-Ubuntu\ext4.vhdx' to WSL2: The system cannot find the path specified.`

Error: `Wsl/Service/CreateInstance/MountDisk/HCS/ERROR_PATH_NOT_FOUND`.
Native `Get-Volume -DriveLetter D` returned no volume, and `Test-Path` for
that VHDX returned false. This establishes current SSD/WSL unavailability;
it does not by itself prove the cause of the earlier exit 135.

No WSL repair, disk remount workaround, dependency/permission change or
fallback disk was attempted. The required THESIS_SSD identity must return:
volume `0a2f1ba9-0000-0000-0000-100000000000`, at least 40 GB free.

19 standard-library correction tests passed using existing native Windows
Python (`NATIVE-CONTROL-02-RECEIPT.json`; earlier 18-test receipt retained).
They include real blocking-child
termination, retained partial evidence, accounting mocks, complete artificial
nine-worker outputs and unchanged workload/utility AST checks. Windows uses
its native termination path; POSIX TERM/KILL escalation and the existing
27 torch CPU regressions still need the recovered WSL environment.

Next: reconnect the SSD, rerun the combined suite under a new exclusive
receipt label within the remaining correction budget, complete final audits,
freeze the correction manifest, make exactly one new small SSD export,
verify whole/member hashes, then commit/push and verify the remote hash.
The old package/export remains unchanged. The correction is not launch-ready;
approval remains false and no research allocation has been made.
