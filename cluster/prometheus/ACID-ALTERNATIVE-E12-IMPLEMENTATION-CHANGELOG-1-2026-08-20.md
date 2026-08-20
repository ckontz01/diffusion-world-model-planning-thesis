# ACID-alternative E12 implementation changelog 1

Date: 2026-08-20  
Applies to: `ACID-ALTERNATIVE-E12-PRISM-MATCHED-UNTOUCHED-D4-PROTOCOL-2026-08-20.md`  
Protocol SHA-256: `08cbe26c3186f06d6731defc8fc66f63c2a55c1102f6d089f1e286176f9ed927`

This changelog records execution and implementation corrections permitted by
Section 9 of the frozen E12 protocol. It does not change a task, arm, dataset
partition, checkpoint-selection rule, training recipe, candidate budget,
seed, margin, statistical gate, or inference rule. The E12 D4 manifest and D4
result directory did not exist when any correction below was made.

## 1. Stage-B preflight could not invoke Git

- Failed job: `298477`.
- Immutable snapshot:
  `gdp-cem-e12-stage-b-d75003b0a4e7e0a6`.
- Failure: the pinned Apptainer runtime did not contain a `git` executable, so
  the preflight could not read the already-downloaded PRISM checkout's HEAD.
- Correction: resolve HEAD from `.git/HEAD`, loose refs, or `packed-refs`, and
  still require the exact frozen 40-character commit.
- Commit: `433921a` (`Make E12 preflight independent of Git executable`).
- Failed output preserved at
  `results/acid-alternative/gdp-cem-e12/failed-stage-b-preflight-298477`.

No model, data, metric, or result content had been produced.

## 2. Stage-B preflight encountered a line-ending representation mismatch

- Failed job: `298481`.
- Immutable snapshot:
  `gdp-cem-e12-stage-b-6b7860cad812ec74`.
- Failure: the protocol recorded hashes of the public PRISM files as checked
  out with CRLF line endings, whereas the pinned Prometheus checkout stores
  the same commit with LF line endings.
- Correction: require the exact pinned Git commit, reproduce and check the
  protocol's canonical CRLF hashes, and separately record the raw LF hashes.
  No source-content check was removed or weakened.
- Commit: `0844d3e` (`Record PRISM line-ending hashes explicitly`).
- Failed output preserved at
  `results/acid-alternative/gdp-cem-e12/failed-stage-b-preflight-298481`.

No learned component or evaluation outcome existed.

## 3. Stage-B launchers pre-created trainer-owned output directories

- Failed/cancelled arrays: PriorHead `298487`; PRISM-DP `298488` (running
  element `298492` was cancelled after the launch defect was identified).
- Immutable snapshot:
  `gdp-cem-e12-stage-b-61ffbbef1a3ef445`.
- Failure: each launcher created the final method output directory before
  invoking a trainer that intentionally creates that directory with
  `exist_ok=False`. The trainers therefore stopped before training.
- Correction: launchers create only the parent and job-local scratch
  directories. A freeze-time regression check rejects any future launcher
  that again pre-creates `${OUT}`.
- Commit: `8025753` (`Keep E12 trainer outputs trainer-owned`).
- Failed output preserved at
  `results/acid-alternative/gdp-cem-e12/failed-stage-b-training-launch-298487-298488`.
- Replacement immutable training snapshot:
  `gdp-cem-e12-stage-b-e2faf062f3eec188`, source-manifest SHA-256
  `e2faf062f3eec188b8b78d167f6e75de29b5ff64446843c04696ed53d4bd856b`.
- Replacement arrays: PriorHead `298504`; PRISM-DP `298505`. The complete
  preflight and GPU smoke were rerun before those arrays.

No failed-launch checkpoint or training statistic was used.

## 4. Native Stage-A wrapper had two runtime-only defects

- Failed array: `298510`.
- Immutable snapshot:
  `gdp-cem-e12-stage-a-a941a96221ae06c2`, source-manifest SHA-256
  `a941a96221ae06c24fa9c68ab02dceb0e7710cd46f8b4ded8bf8eb7c9e8d011b`.
- PushT failure: Stable-WorldModel 0.0.6 unconditionally constructs
  `Path(video_path)`, so `video_path=None` failed after native evaluation.
- Cube failure: the launcher omitted the NVIDIA EGL vendor-file bind and
  `PYOPENGL_PLATFORM=egl` used by the already-validated E11 headless stack.
- Correction: render non-result videos only into job-local scratch removed by
  the launcher trap; bind the NVIDIA EGL vendor file; and set the established
  EGL/headless environment. Freeze-time assertions reject both regressions.
- Commit: `aab5259` (`Repair E12 native artifact runtime`).
- Failed output preserved at
  `results/acid-alternative/gdp-cem-e12/failed-stage-a-298510`.

These are native public-artifact sanity runs, not matched claim data.

## 5. First repaired Stage-A rerun lacked this required changelog

- Superseded array: `298542`.
- Immutable snapshot:
  `gdp-cem-e12-stage-a-a5e9ffde6469b287`, source-manifest SHA-256
  `a5e9ffde6469b2871234b036185f3cd5b73de55eb5bd2c14280dc008ec369257`.
- The corrected runtime passed its first five cells, but the snapshot did not
  contain the Section-9 correction record. The array was cancelled before
  completion and cannot be used as the E12 Stage-A result.
- Superseded output preserved at
  `results/acid-alternative/gdp-cem-e12/superseded-stage-a-298542-missing-changelog`.
- Required resolution: freeze a replacement Stage-A snapshot containing this
  changelog and rerun all 12 native cells from the beginning.

## 6. Stage-B validity failure is not an implementation correction

All six Reacher PriorHeads from replacement array `298504` wrote complete,
finite checkpoints and summaries but failed the frozen 15% validation-MSE
improvement rule. PushT and Cube passed for both goal variants and all three
seeds. No gate was changed. Commit `8b5844f` added a fail-closed, P1-only audit
that can preserve `invalid` results without turning them into an artifact
registry or authorizing D4. The audit runs only after all Stage-B training
elements terminate.

The current official PRISM HEAD was rechecked as
`baa0eb95efb812196b68796c258b1f0cf10b7625`, identical to the protocol-pinned
commit. The public `dp_baseline` directory still omits `model.py`,
`scheduler.py`, and `policy.py`; therefore the matched PRISM-DP arm remains a
disclosed reconstruction, never an official reproduction.
