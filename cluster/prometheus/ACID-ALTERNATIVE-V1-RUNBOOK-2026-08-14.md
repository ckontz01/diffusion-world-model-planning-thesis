# ACID-alternative v1 execution runbook

Status: implementation-ready locally; cluster deployment and full GPU preflight pending  
Scope: Le-WM on PushT, Reacher, and single-cube OGBench Cube  
Primary arms: original CEM, reconstructed native ACID, learned reachability,
diffusion transition verification, and a capacity-matched deterministic forward
verifier

This runbook is operational. The frozen scientific rules remain in
`ACID-ALTERNATIVE-V1-PROTOCOL-2026-08-12.md` and its amendment log. Do not use
the older PushT-only launchers for a claim-bearing run.

## 1. Deployment boundary

Use three independent read-only snapshots:

- core: `acid_alternative/` and its tests;
- diagnostics: `acid_alternative_diagnostics/` and its tests;
- orchestration: only the generic v1 Slurm/submission scripts, the graph test,
  and the protocol documents.

From the staged `prometheus` directory on the cluster login node:

```bash
bash freeze_acid_alt_sources.sh \
  /lustreFS/data/superworld/ckontzias/thesis/staging/acid-alternative-v1/prometheus \
  /lustreFS/data/superworld/ckontzias/thesis/snapshots
```

Record the three printed paths and full tree hashes. Each submission script
checks every file against `SOURCE-MANIFEST.sha256`; a mismatch stops before any
job is submitted. Never edit a published snapshot.

## 2. Pre-submission checks

Run the orchestration dry run from the orchestration snapshot:

```bash
bash ORCH_SNAPSHOT/tests/test_submission_graphs.sh
```

Confirm all three benchmark datasets and released Le-WM checkpoints in
`data/stablewm` match the task registry. The D1 graph then runs a GPU preflight
for each task. That preflight runs the complete core test suite and real-stack
wrapper parity before training or efficacy evaluation is released.

## 3. Development submission

Submit exactly once:

```bash
bash ORCH_SNAPSHOT/submit_acid_alt_lewm_d1.sh \
  CORE_SNAPSHOT DIAG_SNAPSHOT ORCH_SNAPSHOT
```

Save the printed `submission_state` path. It binds every job ID and all three
source manifests. The graph performs, per task:

1. frozen manifest preparation and verification, including the outcome-free I1
   episode manifest;
2. task preflight;
3. P1 latent extraction and transition/reachability caches;
4. three-seed ACID, diffusion, forward, reachability, and null-control training;
5. B0 and ACID R0 reproduction gates;
6. the five-arm D1 closed-loop matrix;
7. same-candidate mechanism audit, development identification, sensitivity,
   and latency analysis.

The D1 graph has no code path that can submit C1.

Review the four D1 evidence summaries only after their jobs complete:

- matched closed-loop analysis;
- P1-validation identification analysis (development-only);
- same-candidate mechanism analysis;
- sensitivity analysis.

Implementation failures may be repaired and logged. D1 outcomes may not be
used to invent a new primary arm, choose a new C1 start set, or tune an
undeclared primary value.

## 4. C1 authorization

Do not authorize while any C1 result, C1 diagnostic, I1 latent cache, or I1
transition cache exists. The authorization command checks this boundary and
binds:

- all four D1 evidence summaries and the D1 submission state;
- core, diagnostic, and orchestration manifests;
- all three C1 evaluation manifests and world-model checkpoints;
- all three I1 episode manifests and contamination-scan summaries;
- the complete `8 scorer variants x 3 seeds x 3 tasks` checkpoint matrix;
- the primary CEM and verifier configuration.

Only after reviewing D1 and confirming that no C1/I1 outcome has been seen:

```bash
export AUTHORIZED_BY="Chris Kontzias"
export DECISION_NOTE="D1 completed; implementation and all primary C1 inputs are frozen"
export ATTEST_C1_OUTCOMES_UNSEEN=YES
bash ORCH_SNAPSHOT/authorize_acid_alt_lewm_c1.sh \
  CORE_SNAPSHOT DIAG_SNAPSHOT ORCH_SNAPSHOT D1_SUBMISSION_STATE
```

Preserve the printed authorization path and its `.sha256` companion.

## 5. Confirmation submission

Submit C1 exactly once:

```bash
bash ORCH_SNAPSHOT/submit_acid_alt_lewm_c1.sh \
  CORE_SNAPSHOT DIAG_SNAPSHOT ORCH_SNAPSHOT \
  C1_AUTHORIZATION D1_SUBMISSION_STATE
```

The dependency graph enforces this order:

1. all three complete five-arm C1 primary matrices;
2. locked task-stratified primary closed-loop analysis;
3. I1 latent extraction and transition-cache construction;
4. true diffusion, true forward, and shuffled-action diffusion identification;
5. C1 same-candidate mechanism analysis;
6. the five-gate claim decision;
7. only then, post-primary C1 sensitivity.

I1 preprocessing reuses P1-training statistics and cannot alter any scorer.
I1 outcomes cannot influence the already-locked primary analysis.

## 6. Claim interpretation

The claim decision is generated mechanically. A diffusion-as-ACID-alternative
claim on Le-WM requires all five gates: usefulness over original CEM, ACID
non-inferiority, diffusion-specific benefit over the forward verifier and null,
breadth across tasks, and mechanism evidence. If the diffusion-specific gate
fails, the allowed conclusion is only that learned transition verification is
competitive. PLDM is a separate extension and is required before claiming
generalization across world-model families.

Every failed, cancelled, or superseded job remains in its unique job-ID
namespace. Never overwrite it or silently reuse it as scientific evidence.
