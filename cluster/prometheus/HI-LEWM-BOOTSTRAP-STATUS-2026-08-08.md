# Hi-LeWM Prometheus bootstrap status

Completed 8 August 2026.

## Outcome

The released epoch-15 Hi-LeWM PushT checkpoint completed an end-to-end GPU
smoke evaluation on Prometheus job `294570`:

- partition/node/GPU: `defq`, `gpu02`, one NVIDIA RTX A5000 24 GB;
- state/exit code: `COMPLETED`, `0:0`;
- wall time: 61 seconds;
- peak host RAM reported for the batch step: 2,068,488 KiB (about 1.97 GiB);
- evaluation call time: 17.81 seconds;
- outputs: one result file, one eight-row episode TSV, and eight valid MP4s;
- video validation: every MP4 decodes a 448 x 448 RGB frame, runs at 15 fps,
  and reports a duration of 1.67 seconds.

This was an infrastructure smoke, not a benchmark run. It deliberately used
only eight evaluation cases and sharply reduced CEM populations/iterations.
Its 0% success rate must not be cited as model performance.

## Runtime pin

The working artifact runtime is isolated at:

`/lustreFS/data/superworld/ckontzias/thesis/envs/hi-lewm-artifact-py311-cu121-swm006`

Key versions:

- Python 3.11.10;
- PyTorch 2.5.1+cu121 and torchvision 0.20.1+cu121;
- CUDA runtime 12.1 and cuDNN 9.1;
- `stable-worldmodel==0.0.6`;
- `stable-pretraining==0.1.8`;
- `transformers==4.57.6`;
- `imageio-ffmpeg==0.6.0`.

The full resolved dependency set and the independent installed freeze match
exactly. The `stable-worldmodel` 0.0.6 wheel used for the API audit has SHA-256
`90601307b3430436d617a5134579089414a1f98eab1dfb6aeabf36ea7f46ff4d`.
The immutable CUDA container has SHA-256
`589af9b428527ae2d315fbd5eaf7ef991efb1aa7249e30a6d28e6731df40afb2`.
The independently serialized SSD backup SIF has SHA-256
`cccc563637d52857e8fc32721d3f36a3e26e3b0d1f9fc9a3ae9fffb9219251a0`;
its runtime was separately checked as Python 3.11.10, PyTorch 2.5.1+cu121,
and torchvision 0.20.1+cu121. SIF files include build metadata, so independent
serializations of the same pinned OCI image need not be byte-identical.

## Reproducibility findings

The release is runnable for checkpoint evaluation, but not as a clean fresh
install:

1. Its environment leaves `stable-worldmodel` unbounded. The released
   evaluator matches the 0.0.6 API; 0.1.x breaks it.
2. Its output resolver stringifies `output.subdir: null` as a literal `None`
   directory. The wrapper uses the path-neutral value `.`.
3. The minimized runtime needs the explicitly pinned FFmpeg plugin to write
   rollout videos.
4. More seriously, the released `h_le_wm/train/hierarchical.py` is evaluator
   code rather than the trainer invoked by the official smoke specification.
   Therefore the published training workflow was not reproduced and must not
   be claimed as reproduced.

The evidence and failed diagnostic job IDs are recorded in
`ARTIFACT-ISSUES.md`. No released source file or checkpoint was modified.

## Evidence on Prometheus

- outputs:
  `/lustreFS/data/superworld/ckontzias/thesis/data/stablewm/repro/pusht_checkpoint_smoke`
- stdout/stderr:
  `/lustreFS/data/superworld/ckontzias/thesis/logs/pusht-ckpt-smoke-294570.{out,err}`
- output/log hashes:
  `/lustreFS/data/superworld/ckontzias/thesis/manifests/hi-lewm-pusht-checkpoint-smoke-294570.sha256`
- Slurm accounting:
  `/lustreFS/data/superworld/ckontzias/thesis/manifests/hi-lewm-pusht-checkpoint-smoke-294570.sacct.txt`
- decoded-video validation:
  `/lustreFS/data/superworld/ckontzias/thesis/manifests/hi-lewm-pusht-checkpoint-smoke-294570-validation.json`

## Next thesis step

Freeze this smoke as infrastructure evidence. Next, run the protocol's baseline
pilot with the released checkpoint and protocol-defined planner budget/seeds;
do not tune from these eight smoke cases. In parallel, use the documented
contingency for training: request the missing Hi-LeWM trainer from the authors,
or port empirical-macro CEM into the trusted Stable-WorldModel harness as a
separately reviewed implementation.
