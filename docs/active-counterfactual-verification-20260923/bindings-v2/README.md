# ACV0 bindings-v2: technical controller integration correction

The user instructed: **“FIX ALL TECHNICAL ISSUES TO ACHIEVE WHAT WAS SAID IN THE INSTRUCTIONS”**, following the approved EXECUTE ACV0 direction and two preserved prelaunch fault reports. This directly authorizes technical corrections, re-freezing and continuation toward the same bounded pilot, not scientific changes or expanded resources. The earlier execution direction remains recorded under standing delegation, not a newly invented direct signature. No research allocation occurred under bindings-v1.

## Minimal runtime correction

The previous controller imported `fitting.model_freeze`, accidentally requiring NumPy on the Slurm login host. That function performs only JSON and hash checks. `model_seal.py` copies its exact body into a standard-library-only module, and `dispatch.py` imports that module instead. A separate controller check pins the existing Python3.9.6, sbatch and sacct binaries. No dependency installation, host/container modification, command bridge or extra allocation is required. The model-seal output is tested byte-identical to v1.

All scientific worker modules, the image/physics bridge, planner, models, losses,192-update recipe, analysis, input bindings and grid are byte-identical to bindings-v1. Workers still use the existing pinned container Python3.11.10/NumPy2.2.6 environment. Tests reuse the preserved artificial192-update fit artifacts and do not retrain or rerun the original efficacy grid.

The approved64/16/32 roles,339 allocations, first included sources490/545, eight arms, three primaries, H75,150 actions,4×4 tree,128 response samples, seeds and every resource/storage/fail-stop cap are unchanged. The same information barrier remains: technical checks only until all jobs and final external preservation are verified. No favorable selection, extra research attempt, automatic retry, model promotion or follow-up experiment is added.

The v1 source snapshot/run/control namespaces were never created. The v2 manifest necessarily has a new hash and thus its own hash-derived exclusive namespace; this is a recorded technical revision, not a way to bypass an existing namespace. Launch must check both old and new namespaces and historical matching allocations before any submission. Original packages, failed preflights, receipts, scientific decisions and E12 drafts remain preserved.

See `../bindings-v1/README.md` for the unchanged complete scientific, cost, evidence and preservation contract. The corrected campaign entry point remains `dispatch.py --approval <separate enabled approval> --run <exact manifest-derived run>`. Original and v2 false approval templates remain false; execution authority is a separate publication record combining the original direction and this technical-correction instruction.
