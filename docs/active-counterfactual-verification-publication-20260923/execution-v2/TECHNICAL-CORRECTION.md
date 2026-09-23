# ACV0 prelaunch technical correction, bindings-v2

The direct instruction **FIX ALL TECHNICAL ISSUES TO ACHIEVE WHAT WAS SAID IN THE INSTRUCTIONS** authorizes the prelaunch corrections below and continuation toward the already delegated finite ACV0 pilot. It does not alter science, roles, seeds, job counts, fitting, resources, information barriers or fail-stop rules. The original execution message remains recorded as direction under standing delegation, not a newly obtained direct user signature.

## Reconciled faults

The original transport exceeded Windows command-line length before SSH started. Its R1 correction sends a bounded binary-safe envelope on SSH stdin. The subsequent read-only preflight found that the worker Python points into `/opt/conda` inside its pinned container, not the host. Running the controller in that container would omit host Slurm tools. No research job, source stage, controller or run existed at those failures; evidence remains in `../execution-v1/` at commit c7504522826d8a614734e4edf88d548e78a479cb.

The actual dependency defect was the controller's import of `fitting.model_freeze`. That function only validates JSON and seals but unnecessarily imports NumPy via the fitting module. Bindings-v2 moves its identical body into a stdlib-only module and pins the already existing Python3.9.6, sbatch and sacct binaries. The controller uses host Python with `-B -S`; all workers retain the unchanged container, Python3.11.10, NumPy2.2.6 and scientific runtime. There is no dependency installation, permission/account change, or extra allocation.

## Verification and preservation

All 15 local test groups passed: the 12 existing integration groups and three revision-specific groups. The latter prove byte-identical model-freeze output, reject incorrect update counts/tampered seals, and authenticate unchanged worker/scientific modules, inputs and grid. Tests reuse preserved artificial fit artifacts; no original efficacy grid or192-update fit was repeated. The test used 31.968 wall seconds and171,282,432 peak Job Object bytes under four-core affinity. Its two attempt records were appended to the old append-only test ledger; the exact historical prefix and all38 sealed v1 members remain unchanged. Subsequent testing uses a v2 ledger accounting cumulatively for both versions.

New source manifest: `5630b222e8a88d0eaa45408876929724734d1f992afa657131ac770fb0400fa9`.

New thin source archive:542,720 bytes,39 members, SHA256 `ef5343b6cf1a686585987f99dccc8789612418c08ac30f99b9680a78a7566d5e`.

This changes the hash-derived exclusive namespace, not the fixed grid. Both old and new namespaces and all matching scheduler attempts must be reconciled as absent before any launch. Existing v1 packages, false approvals, fault records, SSD backup, prior studies and E12 drafts remain untouched. A separate enabled approval records the original delegated instruction together with this direct technical correction's provenance. No running snapshot is modified.

Source transport authenticates every member and imports the stdlib controller on the actual pinned host before launch. The same included first two collection jobs490/545 must pass the complete technical gate before the unchanged remainder proceeds. No additional research pilot or retry is authorized by this correction.
