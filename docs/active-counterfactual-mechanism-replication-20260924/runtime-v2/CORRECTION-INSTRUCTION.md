ACV MECHANISM REPLICATION — NARROW PRE-LAUNCH CORRECTION

Reviewed publication:
bb181cc6b6c60770898afacdcca3fb9e604c90c1

Do not launch this package.

Authorize only the three implementation/acceptance corrections below,
their focused artificial tests, a new immutable export, and publication.

Keep all scientific choices and resource limits unchanged.
No additional design proposal, saved-data analysis or efficacy test.

1. CORRECT THE SBATCH SCRIPT OPERAND

In runtime-v1/dispatch.py command(), remove the extra /bin/bash operand
before run_worker.sh.

Submit the existing shebang script directly, followed by the same five
arguments. Keep all CPU/GPU, time, account, partition, QOS, node, logging
and no-requeue options unchanged.

Add tests of the ACTUAL generated CPU and GPU command vectors:
- The script operand is the exact run_worker.sh pathname.
- Its bytes begin with the accepted shebang.
- Its five arguments remain in the correct order.
- /bin/bash is not accidentally submitted as the batch script.

No live submission or extra hardware allocation is needed for this test.

2. RESTORE THE AUTHENTICATED EVIDENCE METADATA

Before saving evaluation evidence, populate:
- initial_sha256 from arrays['requested_initial'];
- goal_sha256 from arrays['goal_state'];

Use the existing bridge.array_hash convention, exactly as the original
ACV0 worker did.

Do not modify the inherited verifier, remove authorization from the
production readback, normalize arrays, or relax any hash comparison.

Add an artificial production-path regression for all six controls:
evaluation metadata -> actual save -> actual
load_verify(..., authorization=...) -> seal -> acceptance.

Mock hardware, checkpoint loading, reference fixtures and physics as
needed, but do not mock away the saved-evidence authentication branch.

Include rejection tests for absent/wrong hashes, wrong reference binding,
and a changed initial/goal array. Show that the completed output,
including new metadata and seal, remains within the existing byte cap.

3. IMPLEMENT THE PRESPECIFIED CROSS-EPISODE PREFIX CHECK

For evaluation records sharing a source and the exact selected prefix
action sequence, verify identical:
- Recorded initial physical/observation state.
- Delivered prefix actions.
- First-five states, proprioception, dynamics and latents.
- Pixel hashes, native flags, clocks and recorded prefix length.

Handle terminal prefixes at their actual length. Do not invent missing
steps or require post-prefix equality after suffix decisions differ.

Use action identity, not a prefix index alone, as the association.
Keep existing exact tree/action/predicted-feature checks.

Apply this at the included first-source16-cell gate and across every
source in final independent analysis.

The controller may compare bounded technical digests generated from
saved fields; the independent analysis must check the actual arrays.
Do not expose partial efficacy to implement the gate.

Add tests in which:
- Same-prefix histories match and pass.
- A separately sealed, individually valid episode has a mismatching
  prefix latent/dynamic/history field and the cross-episode check rejects it.
- Different-prefix histories and legitimate post-prefix divergence
  are not falsely rejected.
- Terminal-prefix lengths and flags remain consistent.

This is completion of the agreed coupling check, not a new experiment.

4. PRESERVE THE FROZEN SCIENTIFIC SCOPE

Keep:
- Exact512 selected sources and their order.
- Original64 fitting/16 validation roles.
- Original checkpoint pair reused without fitting.
- Four new fits at the declared seeds and192 updates each.
- All six configurations and8,192 evaluation episodes.
-8,197 scheduled task keys.
-H75,150 actions, five-plus-ten initial decision, unchanged tail.
-Candidate tree, model interfaces, randomness, precision and endpoint.
-All seven contrasts and the reviewed interpretation contract.

Keep the existing resource ceilings, per-task limits, information
barriers, no-automatic-retry rule and designated-SSD requirements.

No research checkpoint inference, research-data fitting, new reference
payload access, simulator execution, Slurm submission or GPU allocation
is authorized by this correction.

5. TEST, FREEZE AND RETURN

Use the attached review probes to reproduce the two isolated execution
problems. They are not substitutes for the new production-path tests.

Rerun the relevant integration/preservation regressions after correction.
Do not rerun the saved-data report, original artificial efficacy suite,
historical physics, or completed ACV0.

Correction preparation limit:
two cumulative wall-hours of local scripted tests,
four CPU threads,8GiB RAM,250MB new correction artifacts.
Use existing environments; no dependency or permission changes.

Preserve the reviewed package and its receipts unchanged.
Create a separately identified corrected runtime/export with approval
disabled. Record the exact diff and revised source/export identities.

Preserve the documented historical initializer newline representation.
Do not edit an old source file merely to make a Git/export hash match.

Commit/push and verify the full remote hash.
Back up only the new small corrected package and verify its members.

Return:
- The narrow source diff.
- Command-vector regression results.
- Authenticated saved-reader results for all six controls.
- Cross-episode prefix-coupling rejection results.
- Complete-output footprint.
- New commit, manifest/export hashes and test/backup receipts.

The next review is the narrow execution decision against the corrected
package. No new scientific proposal or expanded study is requested.