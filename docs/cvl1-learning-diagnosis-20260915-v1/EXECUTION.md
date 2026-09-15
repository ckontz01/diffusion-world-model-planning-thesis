# Learning diagnosis v1: execution record

Analysis definitions and implementation were frozen before new diagnostic
evaluation at `f7ca86db1cd5aceeb1b07b237aa68c980e93760a`, and the remote Git hash
matched. Seven focused synthetic tests passed, including original-index tie
handling, binary-draw Brier error, conditional concordance, hierarchical weighting,
cross-draw reversal, final-budget agreement and gain-minus-loss decomposition.

Accepted CVL-1 result remains `36d953e5cf366965564cc09b2e8c9a33d407550a`, decision
`stop_no_ranking_promise`. Scientific model artifacts remain in its original
`run-521a0e6627c570ff/fit-0`, authored by the original frozen implementation.

## One CPU allocation

Job **301440**, account superworld, partition defq, qos normal, 4 CPUs, 8GiB,
02:00:00 hard wall limit. No GPU requested; Slurm allocation TRES is
`cpu=4,mem=8G,node=1`. Apptainer has no `--nv` and CUDA devices are hidden.
This job is a separately authorized post-stop diagnosis, not a CVL-1 retry.

Source: `/lustreFS/data/superworld/ckontzias/thesis/staging/cvl1-learning-diagnosis-20260915-v1/source-f7ca86db-lf`.

Output: `/lustreFS/data/superworld/ckontzias/thesis/experiments/cvl1-learning-diagnosis-20260915-v1/run-f7ca86db`.

Source tar SHA-256:
`66e4ed36950a2ce7e0b4335bbb6462421109f7fcdf773c7ce377720eb31d369b`.

LF source manifest SHA-256:
`5ec8599cd7632571b35ba170244cfb32262ff1d58a1b49585c364f05b01e6522`.

The export guard rejected Git archive's CRLF text before submission. Only reversible
CRLF→LF transport normalization was applied to the four exported files; analysis
semantics were not edited. The first host submission helper then encountered
Python 3.6's unsupported `text` argument before any subprocess was spawned. Its
supported `universal_newlines` spelling was used for the one actual `sbatch` call.
Neither preparation issue allocated a job or ran a model. The original archive,
empty rejected export directory and exclusive launch intent are preserved.

## Allowed reads and output

The worker authenticates consumed code and saved features/labels against accepted
source and stage seals, uses existing JSON/NPZ and frozen evaluator readers, and
does not call the collector's trace/physical reconstruction paths. Its consumed
scientific-file inventory is saved as `results/CONSUMED-FILES.json`; evaluator
files are included. No original source record or branch trajectory is loaded.

`results/REPORT.json` contains separate train/validation aggregates, all fixed
scorers, horizon/anchor and tail-scope strata, calibration, decomposition and every
reference. `BANK-ROWS.json` and `CANDIDATE-ROWS.json` preserve all descriptive
evidence, not just selected favorable cases. Adjacent hashes seal the new outputs.
These are new descriptive analyses only; no retroactive CVL-1 decision gate exists.

External destination:
`D:/THESIS-BACKUPS/cvl1-learning-diagnosis-20260915-v1/` on THESIS_SSD.
The source tar was copied there before submission. Job 301440 completed 0:0 in
20 allocated wall seconds; the worker reported 16.5654 seconds elapsed, 32.7476
process CPU seconds and 423,424,000 bytes process maximum RSS. No GPU was allocated.
The archive `result-f7ca86db.tar` is 15,923,200 bytes with SHA-256
`7fcd6f3c1fc7a8f76ad87e85f335fc911fee00060452e3dcf4b17de525f730b2`;
local and remote hashes match, and all four result members match the adjacent
seal `19ccd6003085e8c2b8aca70555153314fe203b8b05151fee077b9763c01546a7`.
See [the completed diagnosis](REPORT.md). No historical output was changed.
