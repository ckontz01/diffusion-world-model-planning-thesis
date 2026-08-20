# E9: AE-only exposed-D2 closed-loop development protocol

Date frozen: 2026-08-17  
Role: post-v3 exploratory planning test on already exposed D2 starts  
Protected inputs: D3, C1, and I1 remain sealed and forbidden

## Why this study is legitimate but not confirmation

The v3 fresh-D2 Stage-A result is fixed at
`/lustreFS/data/superworld/ckontzias/thesis/results/acid-alternative/v3-d2/stage-a/analysis/job-297565/summary.json`,
SHA-256
`0af2181b1060d761a295c885f2eae34af47a0fd94992a8f3a59cf05e57ecbe37`.
Its decision was `stop_before_stage_b`: four of five joint gates passed, while
RDX missed its non-inferiority margin against the deterministic forward
verifier. Therefore the preregistered v3 Stage B remains blocked and will not
be relabeled as passed.

The same Stage-A result also showed that the separately frozen diffusion
action-evidence endpoint (AE) passed every AE-specific gate. On identical
physically executed candidate pools, AE minus reconstructed ACID was `+0.01778`
in success and `-0.00245` in standardized rollout RMSE. AE minus shuffled AE
was positive in every task. Those D2 outcomes are now known, so they cannot be
confirmation. They do justify one explicitly new question:

> When AE changes every CEM update rather than reranking a fixed final pool,
> does it retain a diffusion-specific advantage and match or exceed the
> published-equation ACID reconstruction?

E9 executes only that already defined endpoint. It changes no model, score,
weight, seed, start, CEM setting, or ACID equation. Passing E9 authorizes only
the design of a separately frozen fresh-D3 confirmation; it creates no claim.

## Immutable upstream methods and data

The frozen method specification remains
`ACID-ALTERNATIVE-V3-MULTISEED-D2-PROTOCOL-2026-08-16.md`, SHA-256
`c38e086ee09cbabaa9ab53246add92835d59f95173b5f35290f474abb94a4dfb`,
including its audited ACID reconstruction, residual-diffusion AE definition,
three scorer seeds, planner pairing, adaptive weights, and CEM settings.

Use the exact P3 D2 manifests from job `297535`, 50 episode-isolated starts per
task. Their manifest/provenance hashes are:

| Task | `d2-fresh.tsv` | `provenance.json` |
|---|---|---|
| PushT | `85fd2bc499892be09a5e92000aab879e314ebc3100b11017c3864104d4d25e89` | `fcb07dfb55822bc6717c56016f62f26646a7486b8c834762d4bf0fd8eb771ede` |
| Reacher | `a8683cccfd998017fdf52f21ec6b3a588a4cbda2578049ba007f8bd4f817fd61` | `f175561fd58908ef9d226c4dcd9bda0e67d8dd4adfe1d01b35a4a3dd2fe46a11` |
| Cube | `bd131f4fc43e69311cf9722dfd678abb7cf888fe067ddf00f7310ff866eb7388` | `fa0dfb090aadeb1daadaf703707a64f049cac988c1c9074f0a09345eebb8a62b` |

D2 is explicitly exposed development data. No D2 endpoint, arm, seed, task,
or start may be omitted. D3/C1/I1 paths are rejected.

## Frozen arms and pairing

Run exactly five arms on PushT, Reacher, and Cube:

1. released original CEM (`b0`);
2. the v3 published-equation ACID reconstruction (`acid`);
3. the capacity-matched deterministic forward verifier (`forward`);
4. true-action residual-diffusion action evidence (`ae`);
5. matched shuffled-action residual-diffusion action evidence (`ae_shuffled`).

Use scorer seeds `6101`, `6102`, and `6103`, paired respectively with planner
seeds `8301`, `8302`, and `8303`. B0 is repeated under all planner seeds.
Every arm uses the same task/start/seed ordering and the exact frozen upstream
checkpoint set already audited by v3. Specifically, the true and shuffled AE
models for seed `6101` are retained from the v2 residual-diffusion pilot job
`297483`; the corresponding seed `6102` and `6103` models are from v3 training
job `297533`. The ACID and deterministic-forward models are the retained core
scorers from jobs `296631` (PushT), `296650` (Reacher), and `296669` (Cube)
that v3 audited and used. E9 neither retrains nor substitutes any scorer.

The unchanged planning settings are: 300 candidates, 30 CEM iterations, 30
elites, horizon five, action block five, receding horizon five, goal offset 25,
and evaluation budget 50. AE and forward use the v3 spread-adaptive
`lambda=0.005`; ACID uses published Le-WM `lambda=0.07`. AE retains sigmas
`{0.25,1.0,4.0}`, eight common deterministic draws, and its fixed
`log(conditional MSE + 1e-12) - log(unconditional MSE + 1e-12)` definition.

## Analysis and frozen advancement rule

The primary outcome is per-episode closed-loop success. For each arm, average
the three paired scorer/planner seeds within each start and report every task
and the equal-task mean. Use 100,000 task-stratified start-cluster bootstrap
replicates with seed `2026081704`. Report two-sided 95% and one-sided 95%
intervals for every paired contrast, plus exact start-cluster sign tests.

E9 advances to fresh-D3 design only if all are true:

1. AE's equal-task success point estimate is strictly above ACID;
2. AE minus ACID has one-sided 95% lower bound above `-0.05` equal-task and
   above `-0.10` on every task;
3. AE minus shuffled AE has a two-sided 95% lower bound above zero equal-task,
   and its point estimate is positive in all three tasks;
4. AE minus B0 has a positive equal-task point estimate and a one-sided 95%
   lower bound above `-0.05`;
5. AE minus forward has a one-sided equal-task lower bound above `-0.05`;
6. AE has a higher point estimate than ACID on at least two of three tasks;
7. all runs, hashes, paired starts, deterministic settings, and artifact checks
   pass without dropping any task, seed, or episode.

The selection rule is conjunctive; no alternate lambda, endpoint, score mix,
subgroup, success definition, seed weighting, or task weighting is permitted.
Failure is recorded as failure of this fixed AE planning endpoint on exposed
D2. Success is promising exploratory evidence only. A publication claim still
requires new D3 data, confidence intervals under a frozen confirmation plan,
the non-diffusion controls, and disclosure that ACID is a transparent
published-equation reconstruction until official code is available.
