# DTV-EFF0 configuration lineage — 30 September 2026

Preparation only. No research checkpoint was deserialized, no model inference,
GPU allocation, physics, fitting, new success outcome or protected payload was
used. The separate branch starts at
`fad8f21bc756cbd1268c21856aedb52cdb488b6d`. Historical closures and E12 remain
unchanged. ACVM1 is not rerun and no monitor is created.

## Authenticated candidates

Both candidates use exactly the nine existing v1 **true/action-conditioned
epsilon-prediction** diffusion checkpoints: PushT, Reacher and Cube, scorer
seeds 6101/6102/6103. These are not RDX, AE, action proposal diffusion or new
models. [BINDINGS.json](BINDINGS.json) contains every full POSIX path, SHA-256,
configuration, training seed, best step, input hash and source identity.
[AUTHENTICATED-BYTES.json](evidence/AUTHENTICATED-BYTES.json) records current
whole-byte authentication of all 27 diffusion/ACID/forward checkpoints and
the three frozen Le-WM checkpoints; none were copied or loaded.

| Task | Original core training array | Diffusion indices/seeds | Architecture | Parameters |
| --- | --- | --- | --- | ---: |
| PushT | 296631 | 3/6101, 4/6102, 5/6103 | latent 192, action 10, width 384, 3 residual MLP blocks, sigma embedding 64 | 2,026,176 |
| Reacher | 296650 | 3/6101, 4/6102, 5/6103 | same | 2,026,176 |
| Cube | 296669 | 3/6101, 4/6102, 5/6103 | latent 192, action 25, otherwise same | 2,031,936 |

The action dimension includes five grouped primitive actions: primitive
dimension 2/2/5. The transformer reconstruction of ACID has width 192,
4 layers, 3 attention heads, MLP ratio 4, dropout 0 and shared state-token
projection. ACID has 1,821,514 parameters for PushT/Reacher and 1,827,289 for
Cube (exact metadata is authoritative). The forward control's capacity-matched
width is 392 with three residual MLP blocks: 2,005,664 parameters for
PushT/Reacher and 2,011,544 for Cube. These are checkpoint-summary values,
not the unexecuted width-416 default.

Training source manifest:
`3074081ea1ebadd9ef08fef68ce1d81e6b7db656d873ef9d8470690b6fd0c1fc`.
Original training used 200,000 maximum updates, batch 256, bf16 autocast,
AdamW and checkpoint selection as recorded historically. No selection is
performed now. Parameters were created in float32; inference code has no
autocast and uses float32 captured tensors. State-dict precision is inferred
from executed training source, not inspected by loading in preparation.
The future entry point explicitly rejects non-FP32 stored floating tensors.

Recovered members have been checked against executed source manifests, not
just against today's repository. [SOURCE-AUTHENTICATION.json](SOURCE-AUTHENTICATION.json)
records each member and manifest. The exact D1 evaluator is core
`52acea39e4a1f6da…`; diagnostics are `2a55d07d912bf1b6…` and
`53065f818adf09b3…`. The v3 pre-amendment closure is `875a9cbc19dba78d…`,
and its corrected literal scoring closure is `2c8f890c31e9f5bf…`.

## Score and deployed configuration

For a predicted trajectory z0…z5, actions a0…a4, saved latent mean μ/std s:
normalize current and successor latents with (z−μ)/s. For each σ, add σ ε to
the normalized successor and predict ε with the action-conditioned MLP.
Raw cost is mean squared epsilon error over 192 latent dimensions, then
mean over five transitions, then mean over noise levels. **Lower is better.**
Actions are native standardized planner coordinates; they are not silently
renormalized for DTV/forward. ACID uses native latents, reconstructs normalized
action with one Euler flow step, inverse-transforms it to the planner action
coordinates, then sums squared error over action dimensions and averages
over horizon. The forward control uses normalized successor MSE, averaged
over latent dimensions and horizon.

Combined planning cost = goal cost + λ × unbiased candidate goal std /
max(unbiased candidate checker std, 1e−8) × raw checker cost. This is adaptive
per candidate bank; neither scores nor scaling may be cached across changed
banks. It is not simply a fixed λ times raw cost.

| Configuration | Same weights? | Noise | λ | Executed historical callable |
| --- | --- | --- | ---: | --- |
| Candidate A, v3 legacy DTV | Yes | .10/.25/.50; one fixed CPU-generator draw per level/transition, broadcast over candidates | .005 | `legacy_dtv_costs`, chunked offline; `D2CostModel` is the frozen planning binding, but v3 Stage B was never executed |
| Candidate B, D1 single noise | Yes | .25 only; freshly constructed shape-(1,5,192) private CPU bank for scorer seed | .07 | `SharedRolloutCostModel._diffusion_cost` inside `get_cost`; all nine executed sensitivity summaries authenticated |
| D1 primary three-noise timing | Yes | .10/.25/.50; fixed common bank | .07 | `SharedRolloutCostModel`; **not** Candidate B or Candidate A's deployed weight |

The single-noise implementation regenerates the original one-level bank.
It does not slice the middle (.25) bank from the three-level configuration.
The actual 5×192 normal generator shapes share the first bank for the current
CPU implementation, not the middle bank; this is not assumed generically
for all tensor sizes or runtimes. Artificial testing caught a shape-dependent
CPU-randn tail in a tiny fixture and preserved that finding.

The v1 wrapper performs full 300×5 calls, retains its noise banks, and includes
finite checks, candidate reductions and operational diagnostic CPU copies.
v3's `legacy_dtv_costs` flattens transitions and permits 8,192-transition
chunks; its cost matches v1 within the pre-existing 1e−6 tolerances.
The v3 **ACID** comparator instead draws independent noise per candidate and
transition, with a CPU generator keyed by task, scorer seed, planner seed and
cost-call index. D1 ACID used one common fixed draw per horizon position.
These are different operational RNG/callable paths, not interchangeable
timing evidence. All such generation stays where its original implementation
places it.

## Planning and input boundaries

Released stable-worldmodel 0.0.6 CEM: population 300, 30 rounds, 30 elites,
horizon 5, action block 5, var_scale 1.0, candidate zero equals current mean,
private device torch generator. The variable called `var` is multiplied
directly as a scale; updates use elite sample std. The returned plan is the
**final elite mean**, not the minimum-cost sampled action. Original top-k/tie
behavior, reductions, per-round CPU cost-list conversion and final CPU action
copy/print are retained. No substitute solver or compiler is introduced.

Selected inputs are rows 0 and 1 of each historical D1 task-specific manifest,
fixed without outcomes: six distinct planning contexts, reused descriptively
over three scorer seeds (18 context/seed pairs), not 18 independent sources.
Exact episode/start identities are in `BINDINGS.json`. They are not the later
PushT 0–1599 role. Captures retain preprocessed observation/history/goal and
final candidate banks; saved-score artifacts retain predicted trajectories.
Their 300×5 structure is proved by source/manifests; tensor contents remain
unopened during preparation. The future harness checks exact row identity,
schema and reproduction, and stops for missing pixels/goal or latent-cache
inputs instead of regenerating anything.

Level C is a fresh original CEM solve from saved **preprocessed** observation,
history and goal, with init_action=None. It includes image encoding inside
the real world-model interface, goal encoding, rollouts and returned planner
actions. Raw-image preprocessing, action inverse-processing, physics and
action-buffer execution are outside this boundary. It is not a closed-loop
episode or universal observation-to-physical-action latency.

Missing timing: no exact σ=.25 standalone-call/complete-solver measurement
was found in the historical latency directory. Its sensitivity evaluator has
a recorded elapsed total, but that batched 24-source scientific evaluator is
not the single-environment dedicated latency benchmark. We preserve both
facts; its success is never paired with three-noise timing.
