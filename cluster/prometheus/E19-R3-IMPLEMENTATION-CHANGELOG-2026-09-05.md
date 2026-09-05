# R3 implementation and execution record

The user approved one new instantaneous-initialization contract after R2.
Canonical working branch: `e19-r3-fresh-state-initializer`, based on R2 commit
`8acff056e5701671ab723a7926a84f5c0d9eae83`. All work is in external-SSD-backed
WSL `/home/chris/thesis`; bulk runs stay on Prometheus Lustre. Three unrelated
untracked E12 drafts are preserved. No historical source/result/decision edit.

## Inventory / candidate / local validation

Read sealed R1 endpoint fields for three exposed PushT starts in both stacks;
read HDF5 root schema/attribute names only, not new dataset records. The schema
adds episode-length/offset identifiers, not block/controller state. No recorded
block momentum or contact state is present. Defaults are explicitly assumptions.

Added opt-in subclass/factory and new Gym ID. Native `_setup` creates fresh
physics, public fields and spatial reindex implement instantaneous assignment;
native legacy reset/setter/step remain available unchanged. Goal rendering is
separate; start observation comes from actual initialized state. Velocity-space
metadata correction is an independent flag/helper.

The first local implementation passed NumPy arrays to Pymunk vector setters.
Five tests failed before completing fresh initialization because the public CFFI
binding requires tuple/list inputs. Changed those API arguments to tuples;
all11 local tests then passed. This was before freezing or cluster validation;
no alternate scientific initialization candidate was selected.

## Core validation

- Snapshot `gdp-cem-e19-r3-30215e7fcfd0e614`.
- Source-manifest SHA256
  `30215e7fcfd0e614f2233277f3c9854abc87172a8d688ec5c3e193b0757f8ee3`.
- Run `/lustreFS/data/superworld/ckontzias/thesis/experiments/gdp-cem-e19-r3/run-20260905-30215e7f`.
- Job **300301**, COMPLETED0:0, elapsed48seconds.
- Both stacks'11 native regression tests passed in the runner. All adjacent
  inventory/validation seals passed before aggregate interpretation. Both
 24-scenario gates passed:96 fresh resets total, zero fresh-reset physics
 steps,144 fixed primitive actions,1560 total Space.step calls including
120 old-history preparation steps. No benchmark metric retained.

## First arm-check harness (preserved failure)

- Snapshot `gdp-cem-e19-r3-arms-bde5784c50fef64c`.
- Source SHA256 `bde5784c50fef64c60fc37f48187254bfcfb415e2b980fe77176d162eb247d46`.
- Run `.../experiments/gdp-cem-e19-r3/arms-20260905-bde5784c`.
- Job **300302**, FAILED1:0, elapsed30seconds.
- Failed SAGE/base_cem raw-input equality at the first full-batch slot after
  physical equality passed. Source audit showed the harness reused a policy:
  native set_env resets buffers, not `_plan_call`. The singleton references
  advanced call metadata; the batch was not at call0. No ARM-CHECK output was
  written. Three singleton plus50 batch initializations and9 actions preceded
  the failure. No solver or performance evaluation ran.
- Exact stderr746bytes, SHA256
  `88bf198ca2e5f786da653a7ca7b6af7c80b59a24be145e608db6843af112aad5`.
  Traceback was in the2976-byte stdout. Both logs and run remain on Lustre.

## Replacement arm-check harness

Construct a new native policy per initialization, with unchanged loaded model
and never-invoked solver. Explicitly require SAGE call0/slot mapping and test
the actual action-scaler roundtrip. Never patch a private policy counter. The
validated initializer bytes remain identical to the core snapshot.

- Snapshot `gdp-cem-e19-r3-arms-88a476ab878979f9`.
- Source SHA256 `88a476ab878979f90e6dd80de7365feac8ab39008f32fbe4047eff668f92cdd5`.
- Run `.../experiments/gdp-cem-e19-r3/arms-20260905-88a476ab`.
- Job **300304**, COMPLETED 0:0 in 3m18s. All ten adjacent result seals passed;
  the independent verifier confirmed 560 initializations, 885 fixed actions,
  all arm/slot identities, within-stack input equality and singleton/core
  fixed-trajectory agreement. Zero solver invocations.

E18's non-action scalers were not refitted or replaced using new dataset data.
The arm gate explicitly checks raw lowdim equality plus native image/action
preprocessing, not those missing historical scaler values. This limitation was
specified before the gate and is preserved in every E18 arm audit.

## Final verification

57 local tests passed in 16.22 seconds: 21 new initializer/interface/evidence
tests plus 36 existing R1/R2/E18 regressions. Independent R1 and R2 evidence
verifiers passed unchanged. The core, both arm harnesses and R1/diagnostic/E18
parent source manifests passed post-execution verification; initializer bytes
match between snapshots. All R3 result seals, shell syntax and whitespace checks
passed. No scientific/holdout run, model change, historical-result amendment or
automation was introduced. The only remaining untracked non-R3 files are the
three preserved E12 drafts.
