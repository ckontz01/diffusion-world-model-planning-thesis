# Hi-LeWM artifact issues found during Prometheus bootstrap

## 2026-08-08: released training entry point is evaluation code

- Source artifact: Zenodo `10.5281/zenodo.21353240`, `package.zip` SHA-256
  `b89046841d679fe70f435540d62ae87b662ec34eb457919b098d152263f63967`.
- The archived and staged copies of
  `h_le_wm/train/hierarchical.py` both have SHA-256
  `da0cfb47e4ee9bd43e53371ac44a96503b9fde199436a70a8ccbb4b95bcc631e`.
- That file contains the evaluator implementation and is decorated with
  `config_path="../config/eval", config_name="hi_pusht"`. It does not contain
  the high-level training assembly or trainer loop.
- The official `smoke/pusht/train` spec invokes this module with
  `data=hi_pusht`; Hydra therefore fails before computation because the
  evaluator config has no `data` key.
- Prometheus job `294559` proved that the container and A5000 CUDA path work,
  then failed at this artifact boundary with exit code 1. Logs are retained as
  `logs/pusht-smoke-294559.{out,err}`.

### Operational workaround

Use the released epoch-15 Hi-LeWM checkpoints for baseline evaluation and run
the reduced released-checkpoint evaluator smoke job. Do not claim that the
released training workflow was reproduced. If retraining Hi-LeWM becomes
necessary, request the missing entry point from the authors or reconstruct it
as a separately reviewed implementation from the provided model/training-step
modules.

## 2026-08-08: PushT evaluator forwards obsolete environment kwargs

- The released `h_le_wm/config/eval/hi_pusht.yaml` adds
  `world.history_size: 1` and `world.frame_skip: 1`, unlike the pinned upstream
  LeWM PushT evaluation config.
- `stable-worldmodel==0.1.1` forwards these keys to the registered PushT
  constructor, which accepts neither key. Prometheus job `294560` therefore
  passed CUDA and config composition, then failed during environment creation.
- The compatibility wrapper deletes these two no-op/default-valued keys with
  Hydra overrides (`~world.history_size`, `~world.frame_skip`) without changing
  the artifact source or evaluation algorithm.

### Resolution after version audit

- The deletion workaround was diagnostic only. PyPI wheel inspection showed
  that `stable-worldmodel==0.0.6` exposes both the artifact's public
  `World.evaluate_from_dataset(...)` call and the World-level
  `history_size`/`frame_skip` arguments. Releases 0.1.0 and 0.1.1 expose only
  dataset-driven `World.evaluate(...)` and changed that wrapper interface.
- The artifact's environment files specify unbounded
  `stable-worldmodel[train,env]`, so a fresh install on 2026-08-08 selected
  0.1.1 and cannot run the released evaluator. The reproducible compatibility
  environment therefore pins 0.0.6 and retains the original evaluator config
  unchanged. This is an inferred compatibility pin, not a version declared by
  the authors.
- Jobs `294560` through `294563` trace the API diagnosis. They are retained as
  failed compatibility probes and must not be reported as benchmark runs.

## 2026-08-08: video dependency and null output subdirectory

- The 0.0.6 runtime reached `World.evaluate_from_dataset` in job `294568`, but
  video creation failed because the artifact's unbounded `[env]` dependency
  had implicitly supplied an FFmpeg backend. The minimized benchmark runtime
  now pins `imageio-ffmpeg==0.6.0` explicitly.
- The released config sets `output.subdir: null`, while
  `resolve_output_dir(...)` stringifies that value and creates a literal
  `None/` directory. Hydra also refuses to delete a null-valued node as if it
  were absent. The smoke wrapper therefore sets the output-only value to `.`;
  results and videos resolve directly under the explicitly configured output
  root. This does not change planning or metrics.

## 2026-08-08: released matrix cannot recreate the reported three-seed B0/B1 table

- Hi-LeWM arXiv v2 states in Section 3 and Appendix C.2 that reported planning
  values are averaged over three random seeds.
- The released PushT hierarchical matrix specification contains only
  `seeds: [42]`; the runner's fallback is also `[42]`. No second or third paper
  seed is identified elsewhere in the released YAML, matrix CSV, source, or
  packaged result files inspected on 8 August 2026.
- The released hierarchical matrix specification also has no
  `empirical_macro` override. The base evaluator configuration sets
  `planning.high.empirical_macro.enabled: false`, so that official matrix runs
  B0 only. Although the runner supports an optional empirical-macro block, the
  artifact supplies no B1 matrix specification.
- The package contains neither the paper's raw per-seed matrix results nor a
  completed `raw_rows.csv`/`summary.csv` from which the seed identities could
  be recovered.

### Operational workaround

Use seed `42` only for explicitly labelled development pilots. Do not infer the
other seeds from the reported mean and standard deviation. Before claiming a
three-seed paper reproduction, obtain the original seed list/B1 invocation
from the authors or predeclare a new independent reproduction seed set and
label it as such. The local B1 runner makes every released empirical-macro
default explicit and changes only the solver switch relative to B0.

## 2026-08-08: B1 GPU outcomes are not bitwise repeatable

- B0 repeated exactly across two full seed-42 A5000 runs: all 50 episode labels
  and the `84%` aggregate matched.
- Four B1 executions with the same checkpoint, seed, GPU UUID, resolved config,
  and evaluation episodes produced `84%`, `86%`, `86%`, and `88%`. Only two
  boundary episodes varied across the four runs.
- Job `294578` rules out empirical-bank sampling/encoding as the source: two
  fresh processes produced byte-identical NPZ files, including an exact match
  for all 131,072 macro-action floats.
- The variation therefore occurs after bank construction. The empirical solver
  calls `torch.topk` for elites and retained candidates; PyTorch documents that
  tied-element indices are not stable across invocations. This is a credible
  explanation, not yet a proven root cause.

### Operational treatment

Do not describe the released B1 GPU path as bitwise deterministic. Preserve it
unchanged as the published baseline, analyze it over declared evaluation
seeds, and report repeat sensitivity. Any stable-sort or index-jitter variant
must be labelled as a thesis-owned deterministic sensitivity, not as the
unaltered published B1 implementation.
