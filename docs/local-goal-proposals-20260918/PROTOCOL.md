# LGP1 — local-goal action proposals in a shared planner

18 September 2026. **Preparation only; execution disabled.** One proposal-side
development experiment, not a scorer revision, a renamed CVD, or a native SAGE
reproduction. SI1 at `a99d6d144300a3067c86ee295c94f4775f06267c` is accepted.
Continuation remains the working baseline; no learned evaluator is promoted.
All historical stops, sources, checkpoints and E12 drafts remain unchanged.

## 1. Question and smallest comparison

PushT only, H75/H150, 15 primitive actions per decision. Two newly trained
families: eight-mode trajectory GMM and conditional velocity diffusion.
Both see exactly the same history, state, generated local target, far target
and clocks. Both supply the first 300 actions to the same 30-round, 30-elite
world-model CEM. The proposer family is the intervention, including its
necessary family-specific objective and sampling computation. No learned
scalar evaluator, adapter rollout, density penalty or second-chunk selection.

Three fixed training seeds 8301/8302/8303 per family; all six models reported,
no ensemble or best-seed deployment. Each model runs the same 32 previously
exposed development references and both horizons: **384 primary episodes**.
Native SAGE and existing continuation are distinguished historical reference
systems, not extra live arms and not members of the paired primary contrast.
Historical numerical comparisons are not adjusted into common-planner results.

## 2. Actual released interface and source pins

Inspected pristine `PKU-ML/SAGE` commit
`8219029fd52e89157e05aebb998ab26f0ef46966`, tree
`0c64066eeac97c27fee382c1879bb26968b3fd56`, on Prometheus under
`snapshots/gdp-cem-e19-discrepancy-e347bc087381ecf0/official-sage`.
The metadata certificate `INVENTORY-ELIGIBLE.json` records individual file hashes and
the clean-tree check. Thesis source base is the accepted SI1 commit above;
`SOURCE-PINS.json` binds reused integration files without changing them.

Released `sage/eval/pusht.py`:

- `SAGECostModel._history_latents`: three actual RGB frames spaced five
  primitive steps; initial missing history is left-padded with the first frame.
  LeWM encodes these into history tokens, not a hypothetical future state.
- `_normalized_lowdim`: latest `state` followed by `proprio`, normalized with
  checkpoint statistics. PushT state has seven fields; proprio duplicates
  agent x/y and vx/vy, for 11 inputs total. No replacement of missing fields
  with zeros in the new integration.
- `_local_goal_latents`: the frozen generator takes history, final-goal tokens,
  normalized low-dimensional state, remaining schedule horizon and option
  duration. It predicts a residual-from-goal latent. When remaining <= duration,
  use the actual final latent, not a generator prediction. Cache keys include
  environment, planning call, remaining horizon and duration.
- `sample_candidates`: the action prior receives **both local and far goal**,
  history, lowdim, action-token length and both offsets. The transformer prior
  uses a shared mixture mode for the entire trajectory, not independent modes
  per primitive action. It emits standardized action blocks.
- `PriorInitializedCEM.solve`: score the sampled bank; fit elite mean and
  sample standard deviation; draw Gaussian populations for rounds 2–30 with
  candidate zero set to the previous mean. Return the final elite **mean**,
  not the best sampled member. There is no GMM log-density call or learned
  mixture-parameter dependence in refinement. Therefore a sample-only swap
  is feasible; it is not necessary to turn diffusion into a density estimator.

The released training uses generated local targets (ratio 1.0), including
generated conditioning in validation; action targets are recorded actions.
Default training configuration is 400k/40k pairs, three-frame history,
width512, action decoder depth3/eight modes; generator depth4. Those released
training budgets are reference facts, not the smaller LGP1 allocation.

PushT action is a relative Cartesian controller command: the environment forms
`agent.position + action * 100`, not an absolute pixel target. Five chronological
two-axis primitives form each 10-dimensional LeWM token; tau15 means [3,10].
Raw commands are converted to the pinned world-model planner coordinates via
the existing decoder mean `[-0.007812564379916172, 0.006860687229453032]` and
scale `[0.20846744284501714, 0.20674862637362224]`. New proposer training statistics
must not replace those LeWM coefficients. The affine bridge is tested separately.

## 3. Reuse versus necessary new training

Reuse the released frozen PushT local generator, SHA256
`0b3647a3a41435969d750ec58176ef5f92a419c4eacae2b5cda74b35e63f90da`, its own lowdim
statistics, the accepted frozen LeWM/decoder, image preprocessing, R3 fresh-state
initialization, physical stepping and native success definition. The input lock
already pins the world model and reference-system checkpoints.

Do **not** load VAD weights into the local proposer. Its one-current-latent,
state7, far-goal conditioning and training targets do not implement the released
three-history/local-plus-far/state11 interface. CVD jointly samples local goals
and actions, which would change the target generator as well. Released GMM
weights also are not the matched control: their examples, normalization and
training budget differ. Train **both** local-action families from scratch.
The new definitions reuse velocity-DDIM mathematics, not a checkpoint conversion.

The shared frozen generator/LeWM may have seen relevant expert episodes during
their historical training. Neither is refitted or claimed source-held-out by
LGP1. This limitation is common to both primary arms and blocks an all-components
unseen-data claim.

## 4. Information flow and explicit common refinement control

```
fresh current pixels/history + raw state + fixed far-goal image + clocks
                -> frozen LeWM and frozen local generator
                -> identical history/local/far/state11/clock context
                -> GMM OR diffusion -> 300 normalized 15-action options
                -> raw-action bridge -> shared support projection
                -> frozen LeWM local-target cost -> identical CEM updates
                -> final elite mean -> pinned decoder -> 15 actual actions
                -> observe actual state/history and replan
```

The new common control is intentionally not bit-identical native SAGE:

1. Use FP32 planner reductions and deterministic lowest-original-index elite
   ties, sample std with correction=1, no variance floor, no cross-stage warm
   start, no prior density. Frozen LeWM retains its accepted runtime precision.
2. Give proposal sampling and refinement distinct episode/stage-owned RNG
   streams. GMM's categorical draws and diffusion's noise consumption cannot
   shift the refinement stream. Identical first banks imply identical refinement.
3. Before **every** cost call, convert to raw commands, clip to [-1,1] per axis,
   and convert back with the pinned decoder. This explicit common feasible-set
   projection is needed for the accepted driver, which rejects out-of-support
   delivered actions. Record pre-projection exceedance, post-projection boundary
   occupancy and collisions for both arms and all rounds. Never hide this
   modification under the label native SAGE. Final elite means are in the convex
   support. Do not tune bounds or collision handling after results.
4. Compute one local goal per actual stage and share it across all populations;
   no persistent cross-episode cache. Replanning histories come from each arm's
   actual trajectory. Same target **function and inputs at a common state** does
   not mean forcing identical target tensors after the trajectories diverge.

The sample-only swap itself could preserve native SAGE CEM. The declared common
controls above instead align reproducibility and support with the accepted fresh
driver. A positive result establishes a difference inside this shared control,
not dominance of unmodified SAGE. No refinement/no-refinement factorial is added.

## 5. Data eligibility and exact proposed row construction

There are two distinct identifier namespaces: expert HDF5 **episode IDs** and
the independently collected reference indices 0–5999. The prohibition on reference
payloads 1600–5999 does not authorize opening them via another namespace. No
reference payload at all was opened in this preparation.

Read only the existing P1 train/val identifier-and-length registry, SHA256
`34dcff8a457fb636fbee836e836f752de66013154c36739613b9d5c81dcba5e6`, and released
paper manifest episode identifiers. Original P1 counts: 11,814 train / 1,295 val.
The union of released PushT paper memberships has601distinct episodes. The
final rule excludes the **entire released SAGE validation/test split as well
as paper memberships**, removing2,375train and238val episodes and leaving
**9,439 / 1,057**. Every remaining episode is in the released SAGE training role;
the thesis's existing P1 roles still separate new-proposer fitting and validation.
No official evaluation membership is treated as a new-proposer training role.
Full counts and eligible-set digests are in `INVENTORY-ELIGIBLE.json`.
`INVENTORY.json` preserves the preliminary paper-only counts, not launch eligibility.

Proposed cache: **80,000 fitting and 8,000 validation examples**, equal allocations
over delta={15,30,45,60,75,90,105,120,135,150}, tau=15 only. Complete source
episodes stay in the existing roles. Within each cell, select valid `(episode,t)`
by hash of `lgp1|row|role|delta|episode|t`, then IDs, with no replacement of the
same tuple. Require t>=10 and t+delta<episode_length. Same physical start may
appear at different delta; these are not independent episodes. Report distinct
episodes and windows after construction, not 88,000 independent sources.
The longest-horizon metadata capacities are34,303 / 3,938, above8,000 / 800.
No payload finite-value or action-alignment checks are claimed completed yet.

Use the already audited PushT HDF5-to-JPEG-Lance transport and existing episode
mapping for frame/action access, filtered to these P1 roles. Do not silently
switch to lossless rendering or refit/reopen the accepted transport investigation.
The cache builder must bind the existing source/transport hashes and verify
chronological action blocks before any optimizer call. These are future binding
checks, not permission to decode the payloads during preparation.

At each selected t, history frames t−10,t−5,t; far target frame t+delta; recorded
actions [t,t+15). For delta>15 cache the shared generator prediction; for delta15
use the actual far latent, matching the online final-stage switch. Both families
receive the same cached targets. Recorded expert actions may not reach a generated
target exactly: this is a known conditioning-label mismatch shared by both arms,
not repaired by new simulation or target relabeling. Original E14 one-frame and
mixed-duration caches cannot simply replace this cache.

Fitting-only state/action mean/std, floor1e-6, common to both families; no fitting
of normalization on validation or the 32 development references. Raw latent
tokens use network LayerNorm as in the source, no validation-fitted latent scaling.
The generator continues to use its own frozen historical normalization.

Development episodes are exactly the historical bottleneck 32 indices in
`DATA-ROLES.json`. They are separate collected source keys, not expert episode
indices; all were already exposed and none is a CVL reserved closed-loop source.
They cannot supply proposer targets, statistics or checkpoint choice. H75/H150
goals are their recorded state at index H, with fresh rendered start/goal images;
not the legacy dataset evaluator's exclusive endpoint convention. No new
reference collection and no reserved or 1600–5999 payload access.

## 6. Fixed training specification

`local_goal_models.py` defines both new models: common visual token projection,
state/clock encoders and width512/depth3/eight-head Transformer decoder with
feed-forward width2048, zero dropout. GMM has eight trajectory modes, learned
queries, mean/logstd heads with logstd clamp[-5,1]. Diffusion adds noisy-action
and diffusion-time query inputs and a velocity head, cosine1000 schedule,
five DDIM evaluations at [999,749,500,250,0], no classifier-free guidance or
conditional dropout. No architecture/sampler search is proposed.

GMM objective: trajectory-mixture NLL. Diffusion: per-row velocity MSE using
independent Gaussian noise and uniform training time. Both share exactly the
selected rows, batch indices, normalization, 12,000 updates, batch128, AdamW
lr1e-4, weight_decay1e-4, gradient clip1, FP32. Exactly **six fits, 72,000 updates,
9,216,000 row presentations** (wrap epoch order; full batches). Final checkpoint
only, no validation-selected epochs. Validation reports each family's loss and
fixed offline action coverage; it does not choose settings or scientific access.

Equal width/depth/update counts do not equal parameter count, optimization
difficulty or FLOPs. Actual counts are in `TEST-RESULTS.json`. GMM predicts its
bank parameters once; diffusion uses five batched denoiser passes. Report training
wall time, CPU time, peak memory and inference time separately; no equal-compute
claim. Construction seeds are fixed but weights cannot be elementwise paired
across structurally different heads.

## 7. Technical integration and execution contract (future approval only)

No legacy dataset evaluator. R3 fresh initialization and native success remain
unchanged. A new thin policy adapter must implement the `FreshEpisode` lifecycle
(`planner`, empty diagnostics, stage0, action buffer) without modifying the driver.
It captures raw state before preprocessing, constructs proprio deterministically,
maintains three fresh frames at five-step intervals, and converts sampled actions
through the two distinct affine coordinate systems exactly once. All histories,
caches and RNG streams reset per episode. Initial history repeats the current
frame; it must never invent pre-reset history from dataset images.

Execute15 primitives per stage until native success/termination, truncation or
budget. Budget=2H (150/300 actions); schedule clock restarts at H while physical
remaining budget continues decreasing. Native success at any delivered action
counts, including final action. No model call after termination. At the final
stage of each cycle use the actual goal. Never advance physics during reset.

Before development, fixed exposed first two historical references, both horizons,
both families, training seed8301: eight integration episodes. Exercise complete
budget paths synthetically and early termination/reinitialization/batch1 plus
independent round-robin slots3. Runtime smoke is technical: shapes, valid action
domain, target reuse, actual-state updates, unmutated checkpoint tensors, no
legacy calls, full-budget termination and fixed model identity. No success-rate
threshold. Failures stop with evidence, not case replacement or tuning.

All six models and cache/normalization/model seals must be fixed before opening
new development outcomes. One evaluation randomness stream per reference/H/seed;
no exact repeats presented as independent evidence. Max384 main episodes, plus
eight separate technical episodes. No native SAGE/continuation new runs included.
The stream identifiers are fixed `(reference,H,training_seed,stage,purpose)`;
paired families share the identifiers but not a promise of identical distributional
draws. Training-seed variation and this coupled evaluation randomness are not
separately identified by the small design. Report that limitation explicitly.

## 8. Endpoint and report

Primary: diffusion minus matched GMM **actual native closed-loop success**,
equal weight to each of the32 complete source references, both horizons and
three training seeds within source. Paired source bootstrap intervals are
descriptive development summaries. Report both arms, every source, horizon and
seed, termination causes, action counts, failures, actual cost. An execution
fault blocks an efficacy interpretation; it is not silently scored as a negative
or removed. No retrospective gates or promotion based on a favored cell.

Supporting measures: first-bank and refined predicted local cost, recorded-action
error on validation, candidate spread/duplicates/projection frequency, latency,
LeWM calls and primitive predicted steps. None substitutes for the primary.
No inference of oracle action-space coverage from 300 sampled trajectories.

## 9. Relation to E14/CVD and limits of contribution

E14 used an equation-based SAGE reconstruction, one current CLS/state7 context,
different budgets (one scoring pass for VAD/CVD versus30 for reconstruction),
diagonal-Gaussian controls, and CVD-generated paired subgoals ranked by internal
consistency. Its frozen stop remains `stop_before_gate_c_no_diffusion_endpoint_passed_gate_b`.
CVD's coverage/consistency improvements did not establish better selected local
cost; no E14 closed-loop comparison was produced. Boundary saturation, target
misalignment, world-model exploitation and proxy-versus-success gaps remain relevant.

LGP1 fixes a separately generated target, supplies the same local+far information
to both new action families, compares a true eight-mode GMM and diffusion, and
holds refinement and execution fixed. It is neither CVD nor a claim that VAD can
be inserted unchanged. It reuses interfaces, frozen perception/dynamics and
exposed development cases, not favorable historic selections or scorer models.

This could identify a useful **proposal-family effect conditional on this planner,
training allocation and small exposed population**. A null result would not rule
out diffusion proposals generally. A positive result alone is not a publication
contribution: multi-task/source-held-out confirmation, stronger computational
matching, justified mechanism evidence, broader baselines and related-work
positioning would remain. Diffusion plus subgoals plus CEM is not claimed novel.
No such follow-up is automatically authorized.

## 10. Preparation completeness and launch boundary

The reviewed preparation at `63e1d9229492aa193c625fdf19c78200f4614f22`
is preserved. Its missing bindings have now been implemented: authenticated
cache construction, actual optimizer/data loop, tensor-CEM, fresh-driver adapter,
serial dispatch/accounting, independent artifact checks, aggregate and final
archive verification. See `IMPLEMENTATION-COMPLETION.md` for exact entry points,
tests, corrections and the distinction between implemented and real-runtime-untested.
`CORRECTION-PACKAGE.json` identifies the corrected complete source manifest;
`LAUNCH-PACKAGE.json` preserves the reviewed package. The generated
root `APPROVAL-TEMPLATE.json` is disabled and binds that source/input identity;
the old disabled document template remains historical. No research execution
is authorized. A separate explicit approval must bind the completed package.
