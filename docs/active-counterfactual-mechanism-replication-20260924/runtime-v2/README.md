# ACV mechanism replication: narrow pre-launch correction

This is the separately identified `runtime-v2` correction to publication `bb181cc6b6c60770898afacdcca3fb9e604c90c1`. The entire reviewed `runtime-v1`, its export, manifests, approval and receipts remain unchanged. **Research execution is disabled.** This package is for the next narrow execution decision, not a launch or a scientific redesign.

## Exact implementation scope

1. `dispatch.command()` submits the unchanged `run_worker.sh` shebang script directly, followed by the same five arguments. It removes only the erroneous `/bin/bash` script operand. Resource, logging, no-requeue and site options are unchanged.
2. `worker.evaluation()` sets `initial_sha256` and `goal_sha256` with the inherited `bridge.array_hash` convention before the actual save. The inherited reader/verifier is unchanged and still receives the production authorization object. No array is normalized or converted for this correction.
3. `prefix_coupling.py` associates episodes by source plus the exact selected five-action sequence (shape, dtype and bytes), not by a prefix index. It checks recorded prefix length, initial state/proprioception/dynamics/latent/pixel hash/flags/action/image, delivered actions and first-prefix states/proprioception/dynamics/latents/pixel hashes/flags/clocks/remaining budget/plan association/images. The prefix is cut at its actual terminal length, never padded. Different selected actions and post-prefix trajectories are not forced equal.

The worker's bounded technical digest is made from the **authenticated saved readback**. The first-source16-cell `acceptance.gate()` checks those technical digests without opening efficacy. Final `analysis.analyze()` compares the **actual saved array bytes**, retaining only one source block in memory; it does not trust matching controller hashes. Existing exact initial/tree/action/predicted-feature checks remain in place. Model, planner and physical interfaces are not changed.

The other code changes are preparation plumbing only: `bounded_run.py` enforces this correction's7200-second/four-thread/8GiB/250MB envelope; `seal_package.py` requires focused and preservation receipts and emits a new `preparation-runtime-v2-<manifest>` SSD namespace. Focused tests and the supplied-review adapter are not campaign entry points.

## Fixed scope and entry points

The original64 fitting/16 reporting-only validation roles, exact512 evaluation IDs/order, reused94011/94012 checkpoints, four192-update fits with94411/94412 and94421/94422, all six configurations,8192 episodes and8197 task keys are unchanged. H75,150 actions,5+10 initial decisions, fixed baseline tail,4×4 tree,128 integration responses, all seven contrasts, multiplicity and reporting interpretations remain frozen. Original32 outcomes stay outside the new estimate. No fitting, inference on research checkpoints, simulator, payload access, Slurm submission or GPU allocation is part of this correction.

Use the same production CLI forms as the reviewed package, with this `runtime-v2` pathname: `transport.py stage/launch`, `dispatch.py`, `run_worker.sh`/`supervise.py`/`worker.py`, `finalize.py`, `preserve.py archive/backup`. `common.Authorization` still rejects disabled approval before any production operation. Source/input/grid/role/model-reuse/resource bindings remain the same except the new source-manifest identity and derived exclusive namespace. No command automatically enables approval.

## Focused validation and review probes

`reproduce_review.py` authenticates every supplied ZIP member and verifies the three source excerpts against the preserved reviewed code. The supplied script is unchanged. Its Linux `/bin/bash` ELF-header read is an explicit artificial binary fixture on Windows; the command operands and missing-metadata reader failures execute exactly as supplied. `PROBE-REPRODUCTION.json` is distinct from the supplied `review-input/PROBE-RESULTS.json`. These isolated probes are not production acceptance tests.

`test_correction.py` exercises actual generated command vectors and actual production worker save → inherited `load_verify(authorization=...)` → seal → acceptance for all six controls. Only runtime dependencies, reference NPZ files, model objects and physical world are artificial; the saved authorization branch and endpoint verifier are not mocked in these six paths. Missing/wrong hashes, wrong source identity and changed initial/goal arrays must be rejected. Coupling tests cover independently valid mismatches, terminal prefixes, matching prefixes, different prefixes and post-prefix divergence. The full8192-record/512-source analysis-loop test uses saved-reader/seal fixtures but checks actual array coupling and rejects a last-source mismatch; it does not rerun the scientific estimator. Relevant existing controller, identity, resource, restart and preservation regressions are included. No favorable artificial efficacy outcome is required.

Final receipts are `TEST-CORRECTION.json`, `TEST-PRESERVATION.json`, `PREPARATION-RECEIPT.json`, `SOURCE-MANIFEST.json`, the false `EXECUTION-APPROVAL.json` and `PACKAGE-VERIFIED.json`. Publication provides the exact source diff and final identities outside the frozen closure.

## Resources and unchanged limitations

The proposed research caps remain: serial one exact RTX6000 Ada on gpu09/gpu09.cluster; evaluation300s (240work+60preserve),4CPU24GiB and2MB complete output; four fits and one analysis each4CPU8GiB7200s;18GB live,18.5GB archive,80GB inclusive. Full remaining-work reservations and retained failures count. No automatic retries, cap resets or evidence deletion are introduced. The existing forecast and complete-footprint document are carried byte-for-byte.

Only this new small corrected export is copied to the designated THESIS_SSD, with whole-file and every-member verification. The old archive/export is not recreated or retransferred. The historical initializer's documented CRLF runtime representation versus LF Git representation is preserved; deploy the byte-authenticated tar, not a normalized reconstruction. Current role metadata is carried from the verified same-day check; reconcile any intervening role conflict before a separately authorized launch, never silently replace IDs. Real cluster hardware/runtime availability, payload authentication, throughput, per-task tail behavior, scheduler latency and large-archive transfer remain execution-time uncertainties. Old monitors stay paused; historical results and E12 remain unchanged.
