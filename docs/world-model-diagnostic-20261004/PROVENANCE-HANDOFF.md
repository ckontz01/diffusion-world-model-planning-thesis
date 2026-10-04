# WM-DIAG0: provenance handoff and targeted binding stop

Final bounded handoff, 2026-10-04 UTC. BIND1 is accepted as completed preparation/feasibility, **not** as approval of a research campaign. This note adds no scientific result or execution authority and changes no frozen source.

## Current status

| Action | Status |
|---|---|
| DINO release acquisition/binding | STOPPED_PENDING_PROVENANCE |
| Historical root/replay binding | STOPPED_PENDING_PROVENANCE |
| Research execution | DISABLED |
| WM-DIAG0 scientific outcome | NOT TESTED |
| Revised parent roles | PROPOSED_NOT_ALLOCATED |

Unused pools, historical roles/results/checkpoints/approvals, E12 and paused monitors remain unchanged. These are information-dependency stops, not evidence that the diagnostic hypothesis failed. No further searches, tests, downloads, model loading, dataset payload/header inspection, fitting, physics, new labels, jobs or monitoring follow this handoff. Neither request below has been sent; no issue, author contact, email or account-access request is authorized by this handoff.

## Request 1 — UNSENT: exact DINO release provenance

Intended recipient: the publisher or authenticated artifact custodian; no recipient address has been selected.

Please identify the **released DINO-WM-no-proprioception checkpoints for both PushT and Reacher**, with an accessible publisher-linked location or a documented, authenticated copy. The baseline-folder route published in the Le-WM release README returned **404 Not Found in our recorded access attempt**:
https://drive.google.com/drive/folders/1r31os0d4-rR0mdHc7OlY_e5nh3XT4r4e

This describes that access attempt only; we do not assert deletion or global unavailability. Please supply, where retained:

- Corresponding model/configuration files and loader/source revision.
- Required encoder weights/revision and dependency versions.
- Image preprocessing, visual-history length, temporal grouping, action coordinates/normalization and decoder, goal handling, and the exact native planning score/reduction.
- File names/identities, sizes and publisher checksums where available.
- License and available training-data/split provenance; please explicitly identify unknown fields.

The original DINO-WM repository alone does not authenticate this specific released no-proprioception contract. We do not request credentials, account changes or permission bypass. If publisher-certified checksums do not exist, please say so: any subsequently computed transfer hash would establish local byte identity, **not publisher-certified identity**. A working location would reopen a scoped binding review, not by itself authorize loading or execution.

## Request 2 — UNSENT: exact historical-origin provenance

Intended recipient: the dataset-generation/archive custodian; no recipient address has been selected.

For the exact selected PushT/Reacher trajectories, **was the provenance needed to reconstruct or restore their historical roots retained?** The immutable proposed 32 diagnostic / 16 fit / 12 validation parent IDs per task and exact source/goal/readout rows are specified in:

- [ROLE-PROPOSAL.json at BIND1](https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/02c8ea4609911611ab8085225cb4ab37447c85d6/docs/world-model-diagnostic-20261004/ROLE-PROPOSAL.json), SHA256 `8556179e202be4905f1891cd60c7476eef3e28ed9ba187f24825336f62f6c9f0`.
- [SOURCE-ROWS-PROPOSED.json at BIND1](https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/02c8ea4609911611ab8085225cb4ab37447c85d6/docs/world-model-diagnostic-20261004/SOURCE-ROWS-PROPOSED.json), SHA256 `46c83e35ededdb0b82e8b5b49a820922bad8f09f65ff0fbdfe27f2ed745ed6eb`.

These are proposals, not newly allocated parents. The existing cohort/role namespace and live episode-master identities were authenticated as metadata; no new HDF5 payload/header inspection was performed. Please identify existing records and schema documentation covering:

- Dataset-generation source/configuration and simulator/model versions.
- Episode-to-root mapping, with either reproducible root seeds/configuration **or** restorable complete root state, according to the actual generator/simulator implementation.
- Relevant model variations, controller/internal state, random-generator state, timing and action-repeat conventions.
- Action coordinate/normalization and observation-recording conventions.
- Available reference root/replay observation and state identities, and documentation showing where the retained fields live.

We do not assume that a dataset seed or complete hidden-state snapshot exists, or demand a redundant field when another authenticated reconstruction supplies its function. Please distinguish **known records not yet authorized/read**, **records whose existence is unestablished**, and **information explicitly confirmed by the custodian as not retained**.

Current evidence classification: the cohort/master/role metadata are known and already inspected; detailed historical-origin records remain **existence unestablished**. No custodian has confirmed they were not retained. No currently identified unread origin record is claimed to exist. A qpos/qvel setter is not proof of historical equivalence; a newly constructed root must not be described as the old root.

## Reopening criteria and limits

Concrete artifact/origin provenance permits a **new scoped binding review only**, not automatic research-model loading, payload access or physics. Both dependency contracts must be addressed before considering the complete four-setting campaign. No Le-WM-only half-launch, task/backbone substitution, endpoint alteration, angle privilege or origin-protocol change is permitted.

If the supplied provenance cannot establish historical replay, return exactly:

> Historical-replay contract cannot be established from supplied provenance; a separately reviewed source-construction amendment would be required.

Do not implement that amendment now. A constructed-origin comparison could be separately reviewed, but is not authorized by this handoff and cannot be presented as historical reconstruction. Later review must reconcile actual artifact sizes, native interfaces, throughput and all remaining resource reservations. Conditional caps are neither allocated compute nor permission to expand the study.

## Immutable evidence and delivery identity

- Accepted feasibility package: `02c8ea4609911611ab8085225cb4ab37447c85d6`.
- Reviewed preservation-receipt commit: `4448ffd23d0ba8c54575e2ff584797f3026a77a9`; [existing SSD receipt](https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/4448ffd23d0ba8c54575e2ff584797f3026a77a9/docs/world-model-diagnostic-20261004/delivery/SSD-VERIFIED-BIND1-002.json).
- [Completed GPT-6 Pro review and final handoff instruction](https://chatgpt.com/c/6a8714c3-0da0-83eb-b9e5-9171a1dadcd5).
- Existing 36 artificial checks are reused, not rerun; cumulative scripted preparation before this handoff was `34.25960440002382` seconds, including failures, metadata checks and both backups. No scientific performance is claimed.
- This handoff is limited to 30 minutes of local scripted/documentation work, four CPU threads, 8 GiB RAM and 10 MB new documentation/receipt bytes, within the original cumulative ceiling. Only these new bytes are published/preserved. Completed preparation archives are not rebuilt or rebacked.

The Git commit containing this exact new note is its immutable handoff reference (no self-referential commit is embedded). A new dated delivery receipt records its blob/SHA256, full remote commit verification and the hash-verified copy on the designated THESIS_SSD volume. Remain stopped until concrete new provenance or a separately authorized protocol amendment is supplied.
