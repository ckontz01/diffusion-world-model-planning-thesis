# WM-DIAG1-SAVED: fixed saved-data discovery plan

This is an outcome-informed follow-up to the completed WM-DIAG0-A2 RC1 publication `4837834b15cffae1fd848108b8737187f4caee06`, not untouched confirmation. Reacher motivates it; PushT is an exposed contrast. The completed study, estimates, intervals, supplier identities, failures and archives remain immutable. No model, training, encoding, rendering, physics, source generation, candidate collection or GPU calls are authorized. No old monitor is resumed.

## Inputs and freezing

`INPUT-MANIFEST.json` identifies all 128 accepted task/backbone parent evaluations, the 64 physical diagnostic source parents shared across backbones, the final accepted supplier paths and seals (including original technical suppliers, RC1 DINO and recovery), active head/representation identities, required files and numeric headers. Its exact identity, this plan, unchanged original pure-array S0 source, new source and artificial-test receipt are pinned by `FREEZE.json` and published before the first derived-result run.

Authenticate only required accepted evidence, not a new whole-study audit: final accepted manifests, selections/external selections and controls; candidate action identities/native index; predicted/realized/goal/cost/action numeric arrays; every candidate's saved oracle PREFIX and two evaluation BRANCH records. Do not read image files, checkpoints, trace banks or unrelated artifacts. No missing-array regeneration or imputation. A genuine scientific schema incompatibility stops with a specific issue. Numeric arrays must be ordinary nonredirected, finite, C-order, nonobject NPY data loaded with `allow_pickle=False`.

The worker streams one parent/backbone at a time and never persists latent banks. Inputs are read-only; new outputs are exclusive and immutable. The manifest stage reads metadata/headers only; it does not calculate new numeric results. Preserve its initial coding-fault source/diagnostic and separately versioned correction.

## Authoritative choices, ranks and original outcomes

Use the saved P0 and O0 indices (rows 0 and 2 of the four saved selections). Saved costs and choices remain authoritative; CPU or float64 rounding never changes them. Record the exact native-return index and candidate identity separately; never equate native return with P0.

Rank candidates by `(saved cost, candidate index)`, with ranks starting at 1. Exact ties, not tolerance ties, take the lowest index. Report each parent's i=P0 and j=O0, identity change, both candidates' predicted/realized saved S0 costs and ranks, two saved outcomes, mean paired outcome difference and native-return identity/outcomes. Include unchanged choices, losses and ties.

Copy original P0/O0 setting means, cell intervals and O0-P0 contrast/interval from the completed RESULTS file. Check their recorded per-parent rows against accepted branch outcomes, but do not call or rerun the old estimator/bootstrap or replace old intervals.

## Terminal squared-distance algebra

At the original decision horizon (position 25 only), let p and r be the saved predicted/realized features, g the saved own-backbone goal and e=p-r. Preserve every native coordinate; flatten only for algebra. Gamma is 1 for Le-WM terminal squared-error SUM and 1/D for DINO terminal squared-error MEAN, D being the complete native feature dimension.

In float64 compute, per candidate:

`Cp64 = gamma * sum((p-g)^2)`

`Cr64 = gamma * sum((r-g)^2)`

`direction = 2*gamma*dot(r-g,e)`

`squared = gamma*sum(e^2)`

Verify `Cp64-Cr64 = direction+squared`. Record signed and absolute residuals. Arithmetic acceptance tolerance is `1e-10 * max(1, abs(Cp64), abs(Cr64), abs(direction), abs(squared))`; it is an algebra check, never a scoring/tie tolerance.

For j=O0 and i=P0, record saved `(Cp[j]-Cp[i])-(Cr[j]-Cr[i])`, the analogous float64 expression, `direction[j]-direction[i]` and `squared[j]-squared[i]`, and their residuals. Record each saved-cost versus float64-cost residual. Large absolute MSE is not by itself harmful relative ordering error.

## One fixed common/candidate-specific decomposition

Per parent, `b=mean_candidates(p-r)` and `u_i=(p_i-r_i)-b`, in float64. Report `E_total=mean_i(sum(e_i^2))`, `E_common=sum(b^2)`, `E_specific=mean_i(sum(u_i^2))`, and coordinate MSE `E_total/D`. Verify `E_total=E_common+E_specific` with the same scale-aware algebra tolerance. Also report each component divided by D; do not compare raw latent units across backbones. A common-energy fraction is null if total energy is zero and is never a fraction of failures caused.

Exactly two new privileged diagnostic selectors are allowed:

- A: `corrected=p-b` (remove common error, retain candidate-specific error).
- B: `corrected=r+b` (remove candidate-specific error, retain common displacement).

Compute each corrected terminal array in float64, cast exactly once to its corresponding stored feature dtype (F32), then call the byte-unchanged original NumPy pure-array `wm_diag0.core.native_terminal_score` with the unchanged stored goal, native feature shape and S0 reduction. The new CPU selectors use exact lowest-index argmin ties. No precision, coefficient, interpolation, subspace, intermediate-position or correction-family search. CPU-versus-saved native/GPU score roundoff is reported separately, not used to alter historical selections.

Seal both new indices/scores before joining evaluation-tail labels. Both selectors use privileged realized features of the tested bank; neither is a deployable or trained repair. A common VECTOR shift can change distances to a fixed goal, whereas an equal SCALAR score offset cannot change ordering. No additive decomposition of success benefit or oracle-recovery ratio is claimed.

## Clocks, absorption and complete descriptive strata

For every saved candidate/draw, identify the first actual success clock from accepted events. Success at clocks 0–25 is prefix success (clock 0 additionally marked initial success). Success after 25 must have remained active at clock 25 and used the one recorded tail replan; classify it as tail success. Otherwise classify full-contract failure and preserve the recorded reason, elapsed clock and prefix-active flag. No unexecuted or post-stop event is inferred.

For each oracle prefix record its action count, success/terminal/truncation flags, `absorbed_after_stop`, and sampled positions strictly beyond its actual stop. The terminal feature is post-stop absorbed only if actual prefix actions<25 and absorption is recorded; stopping exactly at 25 is identified separately. Do not drop absorbed or early-success cases or describe their discrepancies as ordinary continuing dynamics without qualification.

Report P0/O0/A/B/native candidate phases and P0→O0 phase transitions across both recorded draws. Draw counts are descriptive, not extra independent parents. Summaries include the full population and the prespecified original O0-P0 gain/loss/tie strata; no favorable-parent-only analysis. Within each stratum report counts and parent-equal means/median/range for energies and signed selected-pair terms. Reuse published intermediate-position MSE by reference only; no new horizon search.

For O0, A and B versus P0, also report the absolute difference in prefix-success indicators and in tail-success indicators, averaged within each parent and then across parents. Their sum must equal the corresponding full-success difference. This is a disjoint description of recorded outcomes, not a causal partition or an oracle-recovery percentage.

## Four-setting summaries and new uncertainty

For all four fixed settings, report copied P0/O0 results and old intervals; A/B success means, absolute percentage-point differences versus P0, new paired intervals, gains/losses/ties, agreement with O0, original choice changes, error summaries, pair ordering terms, absorption and prefix/tail descriptions. Average two outcomes within each parent, then weight parents equally. Preserve smaller candidate banks without fabricated padding.

Use one RNG `numpy.random.default_rng(20261017)`: generate 10,000 × 32 resample indices for PushT, then 10,000 × 32 for Reacher. Align by source root_index 0–31 and reuse each task's same resample matrix jointly across both backbones and both new selector differences. Percentile 2.5/97.5 intervals are only for A-P0 and B-P0. Do not run new intervals for the old contrasts, pool backbone pairs as independent sources, or add confirmatory/multiplicity/independent-training-seed interpretations.

## Mechanism statement and at most one unlaunched proposal

After all results, answer whether common displacement removal is sufficient for appreciable observed selection benefit, whether candidate-dependent error remains important, whether the Reacher systems agree, what PushT contradicts, and which improvements involve prefix versus tail success. Use “consistent with” where causation is not isolated. No physical/kernel cause, architectural-superiority or universal diagnosis claim. Poor S1 readout accuracy limits that intervention, not score learning in general.

Propose at most one feasible practical intervention, or explicitly recommend against choosing one yet. State its target error, deployment-observable inputs, nonprivileged learning/estimation route, independent future training/development/evaluation data, falsifier and simple matched control/alternative use of the same added data or compute. Retrospective common correction does not establish learnability. A scalar-cost correction is scoring/calibration, not repaired dynamics. All current task cohorts are exposed discovery; transfer claims require an excluded setting. Do not implement any proposal or launch another pipeline. Reuse the existing prior-art ledger; no new literature search.

## Execution and preservation

Use the adopted instruction's separate preparation allowance and exactly one CPU-only saved-data job in the existing compatible environment, four CPU threads, 8 GiB, no GPU. No installations/security/infrastructure changes. Keep all new code, compact outputs, temporary data, logs and all backup copies within 1 GB, with a prospective 768 MB all-copy envelope (source/spec/manifest up to 8 MB × 4; compact outputs up to 100 MB × 5 including conservative local-Git/GitHub logical copies; controls/logs up to 10 MB × 4; tiny artificial roots up to 32 MB; remainder locked). Actual new logical copies are measured at staging, collection and final package readback. Do not copy/unpack/recreate the old 11.3 GB archive.

Deliver this plan, frozen executed source identities, artificial tests and actual resource receipts, RESULTS.md with four-setting tables and every parent row, compact machine-readable results, one mechanism conclusion and at most one unlaunched proposal, a small whole/every-member verified new SSD package and full Git remote commit readback. Old monitors remain paused.
