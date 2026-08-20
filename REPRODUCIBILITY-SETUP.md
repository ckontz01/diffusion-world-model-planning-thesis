# Thesis workstation setup

Last verified as a complete local-data setup: 2026-07-30

> **Current status (20 August 2026):** this file records the original SSD-backed
> workstation bootstrap. On 8 August, the large datasets, released checkpoints,
> containers, and experiment outputs moved to Prometheus Lustre. The local WSL
> distribution and environment remain useful for source work and lightweight
> checks, but `verify_wsl_setup.py` requires the retired local data/checkpoint
> mirror and is therefore a historical full-stack verification script. See
> `STORAGE-LAYOUT.md` and `README.md` for the active layout.

## Storage layout

- WSL distribution: `Thesis-Ubuntu` (Ubuntu 24.04.4 LTS, WSL 2)
- Physical Windows location: `D:\WSL\Thesis-Ubuntu\ext4.vhdx`
- Virtual-disk maximum: 420 GB
- Linux workspace: `/home/chris/thesis`
- Conda environment: `/home/chris/miniforge3/envs/thesis`
- Dataset/checkpoint root: `/home/chris/thesis/data/stablewm`
- Hi-LeWM artifact: `/home/chris/thesis/vendor/hi-lewm/artifact/package`
- LeWM checkout: `/home/chris/thesis/vendor/hi-lewm/artifact/package/code/third_party/lewm`

The Linux distribution, environment, repository, checkpoints, and datasets are all inside the external SSD's WSL virtual disk. Windows and WSL retain small system/runtime components on C:, which WSL does not support relocating with the distribution.

## Starting the environment

From PowerShell:

```powershell
wsl.exe -d Thesis-Ubuntu
```

Then in Linux:

```bash
source /home/chris/miniforge3/bin/activate thesis
export PYTHONPATH=/home/chris/thesis/vendor/hi-lewm/artifact/package/code:/home/chris/thesis/vendor/hi-lewm/artifact/package/code/third_party/lewm
export STABLEWM_HOME=/home/chris/thesis/data/stablewm
export MUJOCO_GL=osmesa
cd /home/chris/thesis/vendor/hi-lewm/artifact/package/code
```

The local environment deliberately uses CPU-only PyTorch (`torch==2.13.0+cpu`). A CUDA environment should be created separately on Prometheus or another GPU system from the project requirements; do not replace this known-working local environment in place.

## Installed stack

- Python 3.10.20
- `stable-worldmodel[train,env,format]==0.1.1`
- `transformers==4.57.6`
- `pytest==9.1.1`
- CPU PyTorch 2.13.0 and torchvision 0.28.0
- Box2D, MuJoCo, OGBench, MiniGrid, Gymnasium Robotics, Craftax, FFmpeg, HDF5/video codecs, and build tools

The full Python lock snapshot is in `requirements-wsl-cpu-lock.txt`.

## Source provenance

- Hi-LeWM archive size: 2,299,863,924 bytes
- Hi-LeWM archive MD5: `aaf78b8b4fd6f5d1f5e720927951152f`
- Hi-LeWM archive SHA-256: `b89046841d679fe70f435540d62ae87b662ec34eb457919b098d152263f63967`
- LeWM Git commit: `8edfeb336732b5f3ce7b8b210d0ba370a09e2cac`

The Hi-LeWM code contains a small compatibility patch in `h_le_wm/checkpoint_compat.py` and its callers. It maps legacy checkpoint pickle module names such as `hi_jepa` to the released package layout.

## Data and checkpoint inventory

Datasets:

- `pusht_expert_train.h5`: 46,300,921,856 bytes
- `cube_single_expert.h5`: 101,942,558,720 bytes

Checkpoint SHA-256 values:

- PushT LeWM baseline: `bd50860a45edc39feefff56f0d0812e74dc809029eac6d014efc89cc33bb2353`
- Cube LeWM baseline: `ba14290ad48081c241d3f7150578102d41559b62d650b35b906fe339d801a9a0`
- PushT hierarchical: `b87805747d40037841877ce7b99b7dda3ebe7a52202c0ba46bf0006ab5d6f008`
- Cube hierarchical: `50aaae8539904e86a835939f8d85af56ca83549ef181d0f6bca7e444437fe4c4`
- PushT phase-A probe: `f590b9dcce9889b9539d6d6f01e411585b38f5103d2ef3c44d44f9397f38f5d2`
- PushT phase-B probe: `389682e8b06968f9248ec1371a90e12e4ade9f14768d9ccb9b7b48a35e16902e`

Both baseline checkpoints were converted from the official Hugging Face weights and loaded with `strict=True` with zero missing or unexpected keys. Both HDF5 files were enumerated and boundary-read after extraction. Compressed dataset downloads were removed after verification to preserve SSD space and can be downloaded again from their official sources.

## Verification status

- `python -m h_le_wm.validate preflight --tier supported-first-class`: passed
- Supported workflow smoke dry-run: passed
- Seeded PushT and OGBench Cube resets: passed
- All six checkpoint deserializations: passed
- Both HDF5 datasets and boundary reads: passed
- Supported test directory with the Conda environment on `PATH`: 90 passed, 4 failed

The four remaining test failures were packaging/test-harness issues rather than model or planner failures: one assertion expected the word `usage:` in valid Hydra help output, and three tests expected public documentation files or links omitted from the distributed archive. Running bare `pytest` at the archive root also collects `scripts/diagnostics/test_macro_action_manifold.py`, whose sibling module is not installed or added to the default import path; use `pytest -q tests` for the distributed supported test directory. `decord==0.6.0` imports and reports its version successfully, although `pip check` under pip 26 flags its older wheel metadata as unsupported on this platform.

## Quick recheck

From `/home/chris/thesis` with the environment activated:

```bash
python verify_wsl_setup.py
cd /home/chris/thesis/vendor/hi-lewm/artifact/package/code
python -m h_le_wm.validate preflight --tier supported-first-class
```
