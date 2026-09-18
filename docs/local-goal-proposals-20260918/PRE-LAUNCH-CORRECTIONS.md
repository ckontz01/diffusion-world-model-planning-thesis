# LGP1 — three pre-launch corrections

Preserved reviewed commit: `dc073fd6f211099126b5395b65f1a44c80e25e8a`.
Preserved source-manifest SHA256:
`3ff10f8ebe9906f532ae2fd06ac8c89581a123165e90f41ebd5ad931f036349e`.
The previous SSD directory `preparation-complete-20260918` is not overwritten.
The new directory/archive is `preparation-correction-20260918` / `.tar` under
`D:/THESIS-BACKUPS/local-goal-proposals-20260918`.

No scientific redesign, new conditions, research fitting, frozen inference,
simulation, labels, GPU allocations or reserved data access. This receipt
supersedes only the three faulty implementation claims in the reviewed package.

## 1. LeWM goal shape

`FrozenBackend.cost_function` now passes the local target as rank3 `[B,1,192]`.
The pinned `LeWM.criterion` itself inserts the candidate axis with
`goal_emb[:, None, -1:, :].expand_as(pred_emb)`. The extra axis in the reviewed
wrapper caused the reported rank5/rank4 failure.

The regression extracts the actual `get_cost` and `criterion` methods from
authenticated source and invokes the production wrapper. Only frozen encoding
and rollout are replaced by artificial tensors; the entire cost method is not
mocked. It verifies exact per-candidate costs and reproduces the old rank4-goal
failure. Criterion source SHA256:
`f29797b1ed2b90b4977f38a953d251e8be8df6c8cfe7b59bb4c00bfd609f0d8f`.

## 2. Decoder arithmetic and provenance

Read the preserved `PILOT-VERIFIER-CORRECTION-20260914.md` and the regression at
`e7188b75a20d25c06ce5c168d15c56510e4daf2b`. The reviewer was correct: the new
bridge's double arithmetic followed by float stores did **not** match the pinned
cluster decoder. Its unspecified local-sklearn comparison was insufficient.

Authenticated installed **scikit-learn 1.9.0**, under the unchanged runtime
`/lustreFS/data/superworld/ckontzias/thesis/envs/hi-lewm-artifact-py311-cu121-swm006`,
inside the already pinned container, without `--nv` and with CUDA hidden.
`sklearn/preprocessing/_data.py` SHA256:
`361f058b427be49ff21c7ac10cda03ac59e2768a13b8d71a9f69c27b69558133`.
Its bytes match the entry in the previously accepted package RECORD, SHA256:
`45c5a47b07f6225659dd7db064c190f80ddaf94482405105a6dd1e18cdb14139`.
No dependency was installed or changed.

Dense FP32 `inverse_transform` casts scale and mean to X.dtype **before**
multiplication/addition; `transform` similarly casts before subtraction/division.
Both new NumPy and tensor bridges now do exactly that. FP32 CEM banks, noise,
projection and reductions stay fixed. Coefficients, bounds, ties and existing
tolerances are unchanged. The representability adjustment at projected support
boundaries remains the same inward-ULP operation, not a changed physical bound.

`PINNED-CONTRACTS-CORRECTION.json` preserves authenticated full source bytes,
method text, versions, and artificial FP32 input/output fixtures produced by
that exact installed StandardScaler in both directions. Exported-package tests
compare both bridges against these saved pinned-runtime fixtures; they do not
depend on whatever sklearn happens to be installed locally. The e7188b75
adversarial coefficients and projection/round-trip support boundaries are also
tested. No real action bank or checkpoint was loaded.

The first source-capture invocation found that the venv Python symlink resolves
only inside the pinned container. The helper was corrected to use that CPU-only
container. A subsequent source-byte check caught universal-newline conversion
of RECORD; capture now preserves bytes before decoding. Neither helper failure
ran a research computation or scheduler allocation.

## 3. Compact primary-endpoint evidence

Each existing planned episode writes `endpoint-h<H>.npz`: authenticated requested
initial and goal identity, actual initialized state, every post-action raw
float64 physical state, delivered float32 actions, native terminated/truncated
booleans, absolute action indices, physical remaining budget and action-stage
indices. The worker checks physical observations against returned raw state.
Only post-action states determine success; t0 is not an outcome observation.
Reference identities bind the original NPZ hash and exact keys/goal index. Both
worker and aggregate independently compare saved initial/goal arrays with the
same allowlisted exposed source. No reserved or additional source is read.

`lgp1_endpoint.py` independently reconstructs the unchanged native predicate:
the **combined four-coordinate agent/block position norm <20** AND the reviewed
angle difference **<pi/9 at the same step**. Angles must remain in `[0,2pi)`;
invalid domains are rejected rather than silently normalized. Native source
SHA256: `d8d0de35aaab5b846db4e79b0fbfd6b17375178cce40a25df5301c8030ca6d68`.

The unchanged native environment returns no truncation. The existing World
configuration supplies Gymnasium TimeLimit300, whose authenticated wrapper
sets truncated at step300. Wrapper source SHA256:
`2a2cd78973296d5871af0ae1334f4c567cacef380bc69b4a759fcc29cbcff51a`.
Consequently the verifier requires the full 2H physical budget unless a recorded
legitimate terminal event occurs; it rejects early nonterminal stopping,
missing/incorrect flags, and any action after termination. It checks the
reported success/termination/counts, every absolute action index, stage index,
stage elapsed time, cycle remaining horizon, physical remaining budget and
final-goal switch. This is endpoint verification, not a new scientific gate.

Rejection regressions cover the one-step nonterminal failure, false positive
label, missing/mislabeled terminal flags, false/missing truncation, actions after
termination, invalid angles and incorrect absolute schedule fields. Valid
first-chunk and final-budget-step successes remain valid. Source-extracted
`PushT.eval_state` confirms combined-position, same-step and boundary cases
without constructing an environment or stepping physics.

## Tests, resources and launch boundary

`CORRECTION-TEST-RESULTS.json` records the corrected checkout regressions;
`CORRECTION-EXPORTED-TESTS.json` records rerunning them from the exported,
hash-verified package. The prior 22-test record and old NumPy dtype reproducer
are retained. Artificial optimizer tests exercise six updates; no optimizer
ever receives research data in this preparation. All model/physics runtime
claims remain limited to source inspection and synthetic contracts.

Compact evidence payload is 90 bytes per delivered action plus168 bytes per
episode before NPZ headers/compression (including the formerly saved actions).
At the fixed maximum88,200 actions across392 episodes this is8,003,856 raw bytes.
A50KB cap per endpoint file bounds all392 files to19.6MB; each file plus its
episode diagnostics must still fit the existing10MB episode cap. No full banks
or video are added. The5.9GB worker,200MB source/control and12GB total remote
caps remain unchanged; archive space is still reserved from actual bytes.

Six fits;72,000 updates;384 main plus8 technical episodes;203 GPU allocations;
336,000 GPU seconds; one4CPU/8GiB/7,200s analysis allocation. No extra episode,
job, seed, retry or budget. Endpoint verification runs inside those existing
workers/analysis; its actual time is charged to their unchanged limits.

`CORRECTION-PACKAGE.json` records new source/input and source-tar hashes.
INPUTS only adds source authentication for the scaler and TimeLimit wrapper;
research payloads, coefficients, role assignments and checkpoint identities
are unchanged. The new package emits a separate disabled approval template.
Remaining uncertainty is real checkpoint/model/GPU/simulator integration and
throughput—not an assertion that the synthetic checks ran the full experiment.
**Research execution remains disabled.** Continuation, historical decisions,
checkpoints, artifacts and E12 drafts remain preserved.
