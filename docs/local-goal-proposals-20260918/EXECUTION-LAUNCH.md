# LGP1 conditional execution — pre-submission stop

The 18 September conditional researcher approval authorizes the existing
scientific execution after the exact observed-angle correction and publication.
Its supplied text SHA-256 is
`f24a4b38314474b99af320a7ff5db1c9818c091199744cafd5088d2ab53cdec7`.
The separate execution approval binds the new immutable angle package; old
packages and disabled templates are unchanged.

## Technical preflight blocker

No LGP1 allocation was submitted. The study namespace was absent and the
read-only Slurm accounting query returned no prior LGP1 job. This turn incurred
zero research allocation seconds, fits, optimizer updates, or episodes.

The host Python 3.9 (and host Python 3) cannot import NumPy. The controller
imports `lgp1_verify.task`, but that module imports NumPy at module scope even
though `task` does not use it. The pinned scientific venv interpreter resolves
to `/opt/conda/bin/python` and is usable inside the existing container; a
read-only container check found neither `sbatch` nor `sacct` there. No
dependencies, environments, permissions, or runtime bindings were changed.

The proposed narrow operational correction is to defer the NumPy import to
`lgp1_verify.cache`, its actual consumer. This has NOT been implemented. It
requires the scoped decision stipulated by the conditional approval, followed
by focused tests, a new immutable source package and an updated separate
execution binding. Do not submit the current package or attempt a fallback.

## Preservation

The new source export and member-verified tar are on the designated THESIS_SSD
under `local-goal-proposals-20260918/preparation-angle-20260918` (and `.tar`).
This is preparation preservation, not a claim of completed research backup.
The external volume identity was verified and had 331265720320 bytes free at
preflight. Research outputs do not yet exist.
