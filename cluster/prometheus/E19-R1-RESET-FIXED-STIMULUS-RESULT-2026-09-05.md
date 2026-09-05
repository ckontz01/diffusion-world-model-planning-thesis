# E19-R1: reset and fixed diagnostic action stimulus result

Date: 5 September 2026. Outcome-informed engineering check on already-exposed
records, **not a benchmark or historical CEM-plan reconstruction**.

## Outcome first

**Do not clear the evaluation interface for confirmation yet.** Identical
requested PushT states and identical delivered actions did not always produce
identical restored physical states. The first meaningful difference was
already present after the state-setting hook, before any diagnostic action.
This supplies concrete restoration/execution counterexamples in both stacks,
not evidence that the diffusion model needs changing.

Decision: `hold_confirmation_pending_restoration_contract_resolution`.
No production correction, model change, new planning, training, SAGE grid,
E20, E18 confirmation, protected-data access or author contact occurred.
E19 remains `stop_native_reproduction_failed`; D2 and L1 remain unchanged.

The validated evidence comprises five cases, two fresh processes per case in
each stack: **20 valid initializations and 300 post-restoration actions**.
Eight earlier Cube attempts are preserved separately because a harness counter
initially mixed reset-internal steps with stimulus steps; they are not included
as valid paired evidence. No outcome-based selection occurred.

For complete execution accounting, those eight incomplete attempts each ran
two native reset-internal calls and thirteen post-restoration actions.
Across both jobs there were 28 process initializations, 404 post-restoration
actions and 32 Cube reset-internal calls. Only the prespecified twenty complete
traces (300 post-restoration actions) enter the reported paired analysis.

## Fixed cases and stimulus provenance

| Case | Source sentinel / row | Task | Episode / start | Source horizon | Action source |
|---|---|---|---|---|---|
| 0 | s0 / 19 | PushT | 8908 / 53 | 50 | CEM candidate 1, diagnostic stimulus |
| 1 | s0 / 0 | PushT | 201 / 6 | 50 | CEM candidate 1, diagnostic stimulus |
| 2 | s2 / 0 | PushT | 627 / 21 | 125 | Saved prior-top returned actions |
| 3 | s3 / 0 | Cube | 85 / 36 | 150 | CEM candidate 1, diagnostic stimulus |
| 4 | s3 / 1 | Cube | 386 / 32 | 150 | CEM candidate 1, diagnostic stimulus |

All indices are zero-based. The predeclared rule scans candidate indices,
never costs or elites. Candidate 0 was all zeros in all four CEM cases and
failed the nontrivial rule; candidate 1 was the first eligible sequence.
The first 15 primitive actions were fixed before simulation. This selection
was independently recomputed from the sealed banks after the run without
model inference and matched every selected tensor/hash.

CEM stored coordinates are bfloat16; the prior-top values are float32.
Selected shapes are 15x2 for PushT and 15x5 for Cube. Exact selected values,
macro shapes/dtypes, action hashes, source bank/content hashes, released
checkpoint hashes, and manifest/episode/start identities are in
[STIMULI.json](e19-r1-evidence/STIMULI.json). Its SHA-256 is
`45ac71f23c4ff96df15a7eb2c019456c7847bec4cae3582c57dbefb8f085848a`.

The CEM sequences are **not** final selected plans. The prior-top values are
authentic saved outputs, but their use in the E18 interface is an engineering
stimulus, not an E18 historical planner output.

## Action delivery was consistent

The exact SAGE checkpoint statistics decoded stored actions into environment
commands. SAGE's unchanged scheduled policy buffered and decoded a fixed-return
stub. The E18 interface re-encoded those commands through its original
StandardScaler mechanism and used unchanged E18ScheduledPolicy buffering and
decoding. Normalization statistics were fitted from the same existing public
training HDF5 columns used by E18, not a fresh holdout. No new rescaling or
clipping was introduced into either environment.

Across all ten pairs, every primitive `env.step()` action was bit-identical
between repeats. In all twenty traces, policy output and base-environment
step input were bit-identical. SAGE's delivered actions also exactly matched
the decoded stimulus; the E18 re-encode/decode round trip differed from those
commands by at most **5.960464477539063e-8**. This is recorded float32 rounding,
not a cross-stack byte-equality claim.

The stub was invoked once per valid trace and returned a fixed tensor; it
performed no search, model forward pass or sampling. The diagnostic stopped
after 15 post-restoration primitive steps and before any second stub call.
Native rewards/termination machinery still ran internally, but no benchmark
success table was produced or analyzed. Logs include an E18 observation-space
warning on PushT; that warning is preserved, not silently suppressed.

## Within-stack physical findings

| Stack / case | After restoration, before first action | Under the same 15 delivered actions |
|---|---|---|
| SAGE PushT 0 | Captured public physical state agrees | State and observations agree |
| SAGE PushT 1 | Block position differs by up to **0.642411**, angle by **0.000625289 rad** | Difference persists; first next observation differs |
| SAGE PushT 2 | Captured public physical state agrees | State and observations agree |
| E18 PushT 0 | Block position differs by up to **1.031932**, angle by **0.005439396 rad**; contacts/velocities also differ | First next observation differs; block-position difference is **0.842222** after step 15 |
| E18 PushT 1, 2 | Captured public physical state agrees | State and observations agree |
| SAGE Cube 3, 4 | qpos/qvel/targets agree, but ctrl/warm-start and other integration fields differ | Captured core physical state and observations agree from step 1 onward |
| E18 Cube 3 | qpos/qvel/targets agree; other integration fields differ | Captured core physical state and observations agree from step 1 onward |
| E18 Cube 4 | qpos/qvel/targets agree; other integration fields differ | Small numerical drift: max qpos difference **6.89e-11** after step 1, **2.23e-8** after step 15; max qvel difference **8.13e-7** at step 15 |

PushT position units are the environment's coordinate units, not a benchmark
success penalty. The first restored-state mismatch is an observed boundary,
not proof that a specific Pymunk cache is the root cause. Complete private
Pymunk integration/contact caches are not exposed by this capture; public
bodies, forces, velocities, contact arbiters and space parameters were logged.

### Correctness versus repeatability

PushT's `_set_state` assigns state and then calls `space.step(dt)`. In all six
PushT pairs, the agent position immediately after this hook differs from the
requested dataset position by velocity times the 0.01-second setter step:
maximum coordinate changes of **0.203750**, **0.937232** and **1.215433** for
cases 0, 1 and 2. The velocities and goal-state assignments match. This
deterministic shift is distinct from the two repeat-dependent block-pose
differences. Whether advancing time during restoration is the intended
evaluation contract must be resolved; this report does not remove that step.

For Cube, all eight valid traces exactly restore requested qpos, qvel,
target position and target quaternion at their respective hooks. However,
the installed `set_state` writes qpos/qvel and invokes `mj_forward`; it does
not replace the entire integration state. The four pairs retain different
ctrl, qacc_warmstart, qacc and external-force fields before action 1. Maximum
initial ctrl differences range from 0.2351 to 150.5860 across the four pairs.
Those fields are measured separately; the fact that three pairs converge
after one action argues against calling every retained-field difference a
demonstrated behavioral defect. The fourth pair has small numerical drift,
not evidence of a meaningful success-rate loss.

The integration snapshot uses the installed `mjSTATE_INTEGRATION` API, with
controller/target and other environment fields outside MuJoCo also recorded.
MuJoCo documents integration state as the inputs to forward dynamics,
including applicable user inputs and warm starts; this motivates the check,
not a causal diagnosis. [MuJoCo state documentation](https://mujoco.readthedocs.io/en/latest/programming/simulation.html).

## Reset RNG and observation overlay

The loaded endpoint columns contain **no seed column** in all five cases.
Both native dataset-evaluation paths therefore call reset with `seed=None`;
E18 additionally passes its native empty variation-options dictionary.
The recorded actual environment RNG seeds differ across every fresh-process
pair despite the stack's global learning-framework seed setup. No seed was
added to the baseline. Gymnasium documents that an uninitialized environment
RNG may acquire entropy when reset receives None; global Torch/NumPy seeding
is not a substitute for that explicit contract. [Gymnasium reset API](https://gymnasium.farama.org/api/env/).

Initial **supplied** state/observation tensors agree in every pair. Fresh
PushT observations and renders already disagree before action 1 in SAGE case
1 and E18 case 0, matching the physical-state discrepancy. Additional info
fields such as block_pose, pos_agent and Cube privileged/proprioceptive fields
can still contain reset information after the dataset overlay. The traces
compare these with freshly derived values; their mismatch is not automatically
an input to the planner or proof of execution error. Dataset control/time/prev
fields can instead describe the recorded trajectory, not the live simulator.

All twenty before-first-action observation/render probes left the captured
physical and RNG state unchanged. Pixel hashes are logged independently;
raw dataset/fresh-render identity across resizing or encoding is not required.
All Cube initial fresh observations/renders match within their pairs even
though the larger integration-state records differ.

## Stack and coverage limits

- Each process has one environment. This does not validate every interaction
  in the original SAGE 50-environment or E18 three-environment vector batch.
- Both interfaces use each selected source's already-exposed interval. SAGE
  uses the endpoint at start+H; E18 retains its native exclusive chunk end,
  hence the last endpoint is start+H-1. These are separately logged contracts,
  not a matched cross-stack evaluation. PushT H50/H125 inputs are engineering
  probes of E18's interface, not new E18 scientific horizons or performance.
- Native SAGE Cube restoration includes pre_step/post_step; E18's original
  YAML hooks include only set_state and set_target_pos. Neither was changed.
- Installed SAGE uses MuJoCo 3.12.0 and Pymunk 6.8.0; E18 uses MuJoCo 3.11.0
  and Pymunk 7.3.0. Both use Gymnasium 1.3.0 and OGBench 1.2.1; the SWM
  implementations differ. Cross-stack bit identity is not an acceptance rule.
- The test is small, selected and outcome-informed. No frequency/error-rate
  estimate or conclusion about benchmark success follows from these cases.
- It does not reconstruct historical CEM actions, resolve author data encoding,
  explain the full SAGE paper gap, or validate all hidden simulator state.

## What follows, without automatically doing it

The next justified work is a separately specified restoration-contract
diagnostic on these exposed records: localize the PushT setter's physical
advance and retained/reset state, decide which full state and environment seed
the intended task contract requires, then regression-test any correction.
Check paired-method initialization before spending a holdout. Do not change
the diffusion architecture, tune benchmark settings, or simply add seed calls
and declare the discrepancy solved. Any changed evaluation stack needs a new
version and explicit disclosure; historical E18/E19 outcomes are not amended.

## Integrity and reproducibility

Initial snapshot: `gdp-cem-e19-r1-2c5ea97ae66b1f47`, source SHA-256
`2c5ea97ae66b1f4714bcd58f7a33d3b57bb9276df672f5023966bf96c6a33a67`.
Job **300297** completed 0:0 in 6m15s; its Cube trace coverage was invalid.

Cube counter correction: `gdp-cem-e19-r1-549757ef959a79ba`, source SHA-256
`549757ef959a79ba77de5a4ec2384edb71ab2639f72d265f66b7c1a64ebe7f6a`.
Job **300298** completed 0:0 in 3m09s. The corrected frozen plan SHA-256 is
`8da0b28ea70db92d2dd9ad0ac4591d4303d05e4651e8e9c1f2cf82afd84a5957`.
Both preparations produced identical stimulus bytes. Each corrected Cube reset
performed two native internal step calls, separately logged from the 15 actions.

Run roots, beneath `/lustreFS/data/superworld/ckontzias/thesis/experiments/gdp-cem-e19-r1/`:
`run-20260905-2c5ea97a` and `run-20260905-549757ef`. All adjacent seals were
verified before aggregation. The analyzer rejects missing before-action or
per-step coverage, even if a trace counter says 15. No invalid Cube trace was
reused as valid evidence.

Full summary SHA-256:
`8c243ee917315ae3c0eba9d06be6c29fb6f9c28f9d31859f6c6a880e465fcca2`.
The 14.2 MB full analysis and raw traces stay on Lustre. The approximately
3.1 MB [review package](e19-r1-evidence/R1-REVIEW.json), with trace inventories,
per-stage differences, restoration/action checks and runtime source hashes,
is stored in the canonical WSL repository on the external SSD. Its hash is
`1939a10896c5c019508b421278798f57cd1ac66649a70d25bab6748b01338fbe`.
Use [the independent package verifier](verify_gdp_cem_e19_r1_result.py).

Final local verification passed all 27 tests (15 R1 harness/reducer tests and
12 existing E18 regression tests), the independent sealed-package verifier,
shell syntax checks and git whitespace checks. No production correction was
implemented by this diagnostic.
