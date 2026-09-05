# E18 shared-infrastructure review before confirmation

Date: 5 September 2026. Static source review plus existing synthetic unit
tests, prompted by [E19-L1](E19-L1-EXPOSED-ARTIFACT-LOCALIZATION-RESULT-2026-09-05.md).
This is not a new E18 performance result or certification of the complete
simulator stack. No E18 episode, model training, or protected holdout was run.

## Correct the earlier numerical interpretation

The existing [E18 result](ACID-ALTERNATIVE-E18-EXPLORATORY-CONTINUATION-PLANNER-RESULT-2026-08-28.md)
has the following task-first numbers; they are quoted from the committed
report, not newly aggregated from protected or partial data:

| PushT horizon | VAD continuation | Greedy VAD-300 | Gaussian continuation |
|---|---:|---:|---:|
| 75 | 50.00% | 47.22% | 47.22% |
| 150 | 44.44% | 25.00% | 25.00% |

The strongest reported gain is +19.44 percentage points at H150, not a loss.
The equal-task/equal-horizon clustered intervals remain [-0.69, +13.89] points
against greedy VAD-300 and [-2.78, +16.67] against Gaussian continuation.
Both include zero. E18 remains exploratory; E17's adapter failure remains
failed and unchanged.

The published timing values are VAD continuation 0.1134 seconds, greedy
VAD-300 0.0568, and Gaussian continuation 0.0614: approximately 2.00x and 1.85x,
not 14–20x. Source inspection adds an important scope clarification:

- `E18Planner.solve` synchronizes CUDA before and after its timed region. The
  region includes encoding, proposal/selection, continuation adapter/model
  work, transfer of selected actions to CPU, and in-region diagnostics.
- The evaluator and analyzer divide each timed three-context solver stage by
  `SHARD_SIZE=3`. The analyzer excludes the first call of each shard, pools
  stage values within each task/horizon/arm, takes their median, and averages
  the four task/horizon medians equally.
- Thus the values are **batch-amortized seconds per context-stage**, not an
  isolated one-context request latency or a three-context batch-call latency.
  The existing analyzer's shorter field name does not change this arithmetic.
- Policy preprocessing before `solve`, environment stepping/rendering,
  checkpoint loading, and the full episode are not included. Do not compare
  these figures directly with SAGE wall-clock episode time or trace-instrumented
  diagnostic elapsed time. No cross-SAGE speed claim is established.

The historical result file and its values have not been rewritten. This
separate note corrects the earlier explanation and clarifies its measurement
definition.

## What is shared and what is not

| Area | Source evidence | Assessment |
|---|---|---|
| Image transport | E18 calls `swm.data.HDF5Dataset` and verifies the exact HDF5 path/hash; SAGE's PushT release path uses the reconstructed JPEG-backed Lance input | The specific L1 JPEG-conversion sensitivity is not on E18's input transport path. This is not an encoder-equivalence claim. |
| World-model weights/runtime | Both lineages use the fixed LeWM artifacts, but E18 uses the historical LeWM environment and explicit cached-latent rollout, whereas SAGE uses the official runtime class mapping and its own history/goal path | Passing SAGE runtime parity on fixed banks does not validate E18's distinct rollout contract. Do not change E18's runtime to SAGE's by analogy. |
| Local goals/cache | E18 encodes its final goal and scores action-conditioned continuations; it has no SAGE generated-local-goal stage-key cache | SAGE's Cube cache-warmup shim is not an E18 dependency. |
| Elite selection | E18 averages the two smallest continuation **values** and selects the first branch by `argmin`; it does not perform SAGE CEM elite refits or use the old diagnostic tracer | The duplicated top-k logging problem is not an E18 production path. Index permutations among equal best-two values do not alter that mean, but this does not prove complete numerical determinism. |
| Input hashing | E18 records explicit proposal-generator state bytes, not the entire input dictionary through the old `repr` fallback | No shared opaque-input-hash criterion was found. |
| RNG control | E18 seeds NumPy, Torch/CUDA and dedicated proposal/GMM generators and enables deterministic algorithms; its top-level evaluator does not explicitly seed Python `random` | This alone neither proves a defect nor guarantees environment determinism. Dataset-derived reset seeds and independent RNGs still require checking. |
| Dataset state initialization | Both world implementations reset, apply state-setting hooks, then overlay dataset observations into the initial input dictionary | Shared conceptual risk: matching first solver inputs can conceal differing hidden simulator/reset state. A future confirmation must not assume this issue is SAGE-only. |
| Timing | Synchronized three-context stages, then divided by three; preprocessing/environment time outside the region | Recorded ratios stand, but must be labelled amortized planner-stage timing, not universal end-to-end latency. |

Relevant source: [E18 evaluator](evaluate_gdp_cem_e18.py),
[scheduled policy and timers](gdp_cem_e18_runtime.py),
[planner](gdp_cem_e18_closed_loop.py), and
[single-latent rollout](gdp_cem_latent_rollout.py).
The planner consumes raw `state` on PushT and raw `observation` on Cube; both
of those fields match in L1's initial SAGE banks but differ later. L1 did not
run those banks through E18, so this is a mapping of risk, not an empirical
E18 repeatability finding.

## Reset/state restoration: concrete remaining gate

Pinned official SAGE
`stable_worldmodel/world/world.py::_evaluate_from_dataset` calls
`reset(seed=init_state.get('seed'))`, applies the task callables, then overlays
dataset values into `self.infos`. E18's installed Stable World Model 0.0.6
`world.py::evaluate_from_dataset` follows the analogous sequence using
`init_step.get('seed')`. If a dataset has no reset-seed column, that call does
not itself provide an explicit seed. L1 did not inspect new dataset episodes
to establish the seed content or reset-state sufficiency.

The PushT hook also advances physics once after assigning state. Cube sets
qpos/qvel and target, then invokes its pre/post-step hooks. State setters and
dataset-input overlays must be checked together: the visible first observation
can be the recorded image rather than a fresh render of the restored physical
state. This source fact is consistent with L1's divergence boundary, but does
not prove the hidden-state cause or identify the correct author configuration.

Before any confirmation holdout, a separately logged engineering check on
already exposed/development records should compare state immediately after
reset, after each setter, and after each action in the first action block;
include velocities, contacts/warm starts and task targets where available,
fresh render versus the supplied image, actual environment RNG states, and
primitive actions entering the simulator. Repeat across processes. Do not
discard differences as metadata until their consumers are identified. Any
objective correction must be source-justified, tested, and separately
versioned; do not silently alter the historical E18 or SAGE evaluation stack.

This additional environment-execution check was not run by L1's expressly
zero-new-episode fixed-bank plan. No shared production defect was established
or patched today. The infrastructure review is useful progress, not permission
to consume a confirmation set.

## Identity and tests

Frozen E18 source-manifest SHA-256:
`182ed1e7d1e9994638ab1fbc773c79cac8d68858b716e67ff8969e5b2e74e29c`.
Protocol SHA-256:
`aff490f3f000c7d9b261632dcd3ccfc76a630b2f44e41f78832c3719607b8459`.
Both matched the immutable snapshot. The following five local modules were
also byte-identical to their frozen counterparts:

| Module | SHA-256 |
|---|---|
| `evaluate_gdp_cem_e18.py` | `f9f84b4712d5fc46e557dd070d2c45caaaf672dc277340cf833c71eb9b37e7a3` |
| `gdp_cem_e18_runtime.py` | `48eaafe8658b9bd63f820fe6f977fdd362fcc08daed3404fc1d982cba1fc7bb2` |
| `gdp_cem_e18_closed_loop.py` | `5c3f831315fc7f8908208d5d66ebac856d20b0bdc02012dcfe98cf6fb5b5e4e9` |
| `gdp_cem_e18_specs.py` | `589f22bc3ff513539b1379b9b43eb2a9bf2fa96cbd633502827a97af3b5bc495` |
| `gdp_cem_latent_rollout.py` | `ef00809db456536ab57d1401848d1601423c664c916c2edcd01919982465ed44` |

The inspected installed E18 world source hashes to
`15fc9e4a69d2ad81d29ca8fedd689b53e96887f7614fa98223ef5ddee37bbda6`;
the pinned official SAGE world source hashes to
`39318b81ed151d8556d8540f460a63eedaed0ce4b2211ce0af9f8200e7d83bde`.
They are different implementations, not byte-identical shared files.

Twelve existing local tests passed across E18 specifications, closed-loop
planner, runtime, evaluator, analyzer, and P2-manifest construction. These
tests use synthetic fixtures and create no protected manifest. They support
the code-level checks, not real-input full-stack validation.
