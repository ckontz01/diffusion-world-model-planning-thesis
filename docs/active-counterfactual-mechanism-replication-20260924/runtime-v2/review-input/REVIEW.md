# ACV mechanism replication: narrow pre-launch review

Reviewed publication: bb181cc6b6c60770898afacdcca3fb9e604c90c1.
Date: 24 September 2026.

## Scope

Read the pinned delivery report and source through the GitHub connector. Ran the included source-excerpt probes with artificial arrays, temporary files and mocked runtime dependencies. Did not run the supplied nineteen-test suite, a Slurm client, a research model, physics, cluster/SSD verification or a training/evaluation campaign. The probes are NOT full production integration tests. The published binary source archive could not be retrieved in this environment, so its byte identity was not independently verified here.

## 1. Wrong sbatch script operand

runtime-v1/dispatch.py command() appends `/bin/bash` before the intended `run_worker.sh`. Under sbatch's documented `script [args...]` interface, this supplies the bash executable as the batch script, rather than invoking bash on the script. The wrapper already begins with `#!/bin/bash`.

Both the CPU and GPU command-builder probes find `/bin/bash` as the script operand. On the review machine it is an ELF binary, not a shebang script. No sbatch command was run. Correct by passing the existing `run_worker.sh` directly, followed by its five original arguments; do not use the review probe to submit jobs.

## 2. Missing authenticated-reader metadata

runtime-v1/worker.py evaluation() supplies reference_identity but not initial_sha256 or goal_sha256. The inherited episodes.evaluate()/save() path does not supply them either. The inherited verify.load_verify(..., authorization=auth) requires both. The original ACV0 worker populated both fields using bridge.array_hash before saving.

The included probes execute the current evaluation-function excerpt against an artificial episode-schema producer and the unmodified independent-reader excerpt (unrelated physics/endpoint checks mocked). Every one of the six control modes reaches KeyError('initial_sha256'). Supplying both fields with the original array-hash convention resolves this isolated reader-contract failure. This is not evidence that the complete corrected production pipeline passes.

## 3. Prespecified cross-episode prefix coupling is not checked

The current first-source gate compares tree_digest and initial_goal_digest. The final analysis compares candidate-tree bytes and requested initial/goal/image digests, then calls the individual-episode verifier. The inherited cross-prefix physical replay loop runs only for collection records, whereas this replication contains evaluation records.

No examined path compares the first-five executed histories ACROSS evaluation episodes sharing a source and identical selected prefix. Add that prespecified check at the first-source gate and over every source in final analysis: group by actual prefix action identity, compare initial physical/observation fields and recorded prefix actions/states/dynamics/latents/pixel hashes/flags/clocks/length. Do not require post-prefix or different-prefix trajectories to match. This finding is source inspection, not an observed physical mismatch.

## Tests to require in the corrected package

- Generated CPU/GPU sbatch vectors point to the actual shebang wrapper, retaining its five arguments and all resource options.
- Artificial execution through the production worker save -> load_verify(authorization=...) -> seal -> acceptance route for all six controls; tampered required hashes rejected without weakening the reader.
- Same-prefix cross-episode pairing succeeds for equal histories and rejects an otherwise individually valid mismatch; different-prefix and post-prefix divergence permitted.
- Corrected package is refrozen, with historical source/science/protocol/grid/input/role bindings and all resource caps preserved.

## Source ledger

All repository paths below are at the reviewed commit:

- docs/active-counterfactual-mechanism-replication-20260924/runtime-v1/dispatch.py
- docs/active-counterfactual-mechanism-replication-20260924/runtime-v1/run_worker.sh
- docs/active-counterfactual-mechanism-replication-20260924/runtime-v1/worker.py
- docs/active-counterfactual-mechanism-replication-20260924/runtime-v1/test_runtime.py
- docs/active-counterfactual-mechanism-replication-20260924/runtime-v1/acceptance.py
- docs/active-counterfactual-mechanism-replication-20260924/runtime-v1/analysis.py
- docs/active-counterfactual-verification-20260923/bindings-r1/episodes.py
- docs/active-counterfactual-verification-20260923/bindings-r1/verify.py
- docs/active-counterfactual-verification-20260923/bindings-r1/worker.py

Upstream primary documentation:
https://slurm.schedmd.com/sbatch.html
https://raw.githubusercontent.com/SchedMD/slurm/master/src/sbatch/sbatch.c
