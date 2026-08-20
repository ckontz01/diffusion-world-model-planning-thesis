# Hi-LeWM B0/B1 PushT baseline pilot status

Completed 8 August 2026.

## Clean pilot outcome

Prometheus job `294575` completed the full published PushT `d=25` selected
configuration for the released epoch-15 Hi-LeWM checkpoint:

- state/exit: `COMPLETED`, `0:0`;
- hardware: `gpu02`, NVIDIA RTX A5000 24 GB, UUID
  `GPU-c9252516-39a8-eb72-0b36-d198e1d2ab73`;
- wall time: 12 minutes 18 seconds for B0 followed by B1;
- peak host RAM: 3,072,260 KiB (about 2.93 GiB);
- B0 evaluation: 42/50, `84%`, 329.76 seconds;
- B1 evaluation: 43/50, `86%`, 327.58 seconds;
- within-run matching: identical 50 `(episode_id, start_step)` cases;
- validation: every frozen setting resolved correctly, all 100 videos were
  present and non-empty, and B0/B1 differed only by the empirical-macro switch.

This is a development pilot, not a paper reproduction. The released matrix
identifies only seed `42`, while the paper reports three-seed aggregates. The
local run used CUDA on an A5000; the released matrix specification says
`eval_device: cpu`.

## Consistency with the paper

With 50 episodes, individual seed results move in two-point increments. If the
paper's displayed standard deviation is the population standard deviation and
both mean and standard deviation are rounded to one decimal, the paper's B0
`89.3 +/- 4.1` uniquely corresponds to seed rates `{84, 90, 94}`, and B1
`88.7 +/- 4.1` uniquely corresponds to `{84, 88, 94}`. The first complete
seed-42 pilot (`294573`) produced `84/84`, exactly compatible with those two
sets. This is supporting arithmetic, not recovery of the unpublished seed
identities.

## Repeated-evaluation finding

B0 was exact across jobs `294573` and `294575`: all 50 outcome labels matched
and both success rates were `84%`.

B1 was not bitwise outcome-deterministic on the GPU. Four otherwise identical
seed-42 executions produced `84%`, `86%`, `86%`, and `88%`. Forty-eight of 50
episode outcomes were invariant. Episode 18054 at start step 22 changed between
the 84% and 86% runs; episode 8235 at start step 10 changed between the 86% and
88% repetitions.

The empirical-macro bank is not the source: job `294578` built the 4,096-entry
bank in two fresh processes, and every saved array was byte-identical. The
`actions` array hash was
`8707ec2e1c6a2c8cb81646b1f9245f35866f51b1bd1474f18a193fc84003abde`,
with zero unequal elements and maximum absolute difference zero.

The remaining variation occurs downstream of bank construction. The released
empirical solver uses `torch.topk` twice per iteration. PyTorch explicitly says
that tied-element indices from `topk` are not guaranteed stable across
invocations, making elite/candidate tie handling a credible mechanism, but the
current evidence does not prove that it is the sole cause.

## Decision

The published baseline path is operational, and the checkpoint/configuration
are plausible enough to unlock P1/P2 development. Keep the released B1 solver
unchanged when labelling it as the published baseline; do not silently replace
its selection rule. Analyze B1 statistically over declared seeds and report the
observed repeat sensitivity. For thesis-owned M1-M3 code, use deterministic
tie-breaking and test repeated runs explicitly.

## Evidence on Prometheus

- clean pilot outputs:
  `/lustreFS/data/superworld/ckontzias/thesis/data/stablewm/repro/pusht_b0_b1_d25_seed42_job_294575`;
- clean pilot logs: `logs/pusht-b0-b1-d25-294575.{out,err}`;
- bank diagnostic:
  `/lustreFS/data/superworld/ckontzias/thesis/data/stablewm/repro/empirical_bank_determinism_job_294578`;
- repeated B1 diagnostic:
  `/lustreFS/data/superworld/ckontzias/thesis/data/stablewm/repro/b1_determinism_d25_seed42_job_294580`;
- frozen PushT partitions:
  `/lustreFS/data/superworld/ckontzias/thesis/manifests/partitions/pusht-v1`.

The next evidence-bearing step is a P0-only frozen-encoder latent-cache smoke,
followed by P1/P2 latent extraction and candidate-audit scaffolding.

