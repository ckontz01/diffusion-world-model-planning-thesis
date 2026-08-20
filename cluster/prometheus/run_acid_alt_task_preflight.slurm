#!/usr/bin/env bash

# Per-task immutable-stack gate: unit tests plus released-model wrapper parity.

#SBATCH --job-name=acid-alt-task-preflight
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=48G
#SBATCH --time=03:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-task-preflight-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-task-preflight-%j.err

set -euo pipefail
: "${TASK:?submit with TASK=pusht|reacher|cube}"
: "${CORE_SNAPSHOT:?submit with immutable core snapshot path}"
ROOT="/lustreFS/data/superworld/ckontzias/thesis"
SOURCE_MANIFEST="${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
STABLEWM_HOME="${ROOT}/data/stablewm"
OUTPUT="${ROOT}/results/acid-alternative/preflight/${TASK}/job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-acid-alt-${TASK}-preflight-${SLURM_JOB_ID}"

for required in "${IMAGE}" "${SOURCE_MANIFEST}"; do test -f "${required}"; done
(cd "${CORE_SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
eval "$(apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONPATH="${CORE_SNAPSHOT}" "${ENV_DIR}/bin/python" \
  -m acid_alternative.print_task_spec "${TASK}" --format shell)"
DATASET="${STABLEWM_HOME}/${DATASET_RELATIVE_PATH}"
CHECKPOINT="${STABLEWM_HOME}/${CHECKPOINT_RELATIVE_PATH}"
for required in "${DATASET}" "${CHECKPOINT}"; do test -f "${required}"; done
if [[ -e "${OUTPUT}" ]]; then echo "Refusing existing output: ${OUTPUT}" >&2; exit 2; fi
mkdir -p "${OUTPUT}" "${JOB_TMP}/apptainer"
trap 'rm -rf -- "${JOB_TMP}"' EXIT
export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
nvidia-smi

apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" --bind "/usr/share/glvnd/egl_vendor.d/10_nvidia.json:/usr/share/glvnd/egl_vendor.d/10_nvidia.json:ro" \
  "${IMAGE}" env \
  PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${CORE_SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" \
  PYTHONHASHSEED=42 CUBLAS_WORKSPACE_CONFIG=:4096:8 \
  MUJOCO_GL=egl PYOPENGL_PLATFORM=egl SDL_VIDEODRIVER=dummy MPLBACKEND=Agg \
  TMPDIR="${JOB_TMP}" python -m pytest -q -p no:cacheprovider \
  "${CORE_SNAPSHOT}/acid_alternative/tests" \
  > "${OUTPUT}/unit-tests.txt"

apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" --bind "/usr/share/glvnd/egl_vendor.d/10_nvidia.json:/usr/share/glvnd/egl_vendor.d/10_nvidia.json:ro" \
  "${IMAGE}" env \
  PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  MUJOCO_GL=egl PYOPENGL_PLATFORM=egl SDL_VIDEODRIVER=dummy \
  "${ENV_DIR}/bin/python" -c 'from dm_control import mjcf; print("dm_control_egl_import=pass")' \
  > "${OUTPUT}/egl-smoke.txt"

apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" env \
  PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  "${ENV_DIR}/bin/python" - "${DATASET_NAME}" "${STABLEWM_HOME}" "${DATASET}" \
  > "${OUTPUT}/dataset-resolution.txt" <<'PYTHON'
import pathlib
import sys

import stable_worldmodel as swm

name, cache_dir, declared = sys.argv[1:]
dataset = swm.data.HDF5Dataset(name, keys_to_cache=[], cache_dir=cache_dir)
resolved = dataset.h5_path.resolve()
expected = pathlib.Path(declared).resolve()
if resolved != expected:
    raise SystemExit(f"logical dataset resolved to {resolved}, expected {expected}")
print("dataset_resolution=pass")
print(f"logical_name={name}")
print(f"resolved_path={resolved}")
PYTHON

apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" --bind "/usr/share/glvnd/egl_vendor.d/10_nvidia.json:/usr/share/glvnd/egl_vendor.d/10_nvidia.json:ro" \
  "${IMAGE}" env \
  PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${CORE_SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" \
  PYTHONHASHSEED=42 CUBLAS_WORKSPACE_CONFIG=:4096:8 \
  MUJOCO_GL=egl PYOPENGL_PLATFORM=egl SDL_VIDEODRIVER=dummy MPLBACKEND=Agg \
  TMPDIR="${JOB_TMP}" python -m acid_alternative.real_stack_smoke \
  --stablewm-home "${STABLEWM_HOME}" --policy "${WORLD_MODEL_POLICY}" \
  --checkpoint-file "${CHECKPOINT}" --dataset "${DATASET}" --frameskip 5 \
  --horizon 5 --samples 17 --seed 42 --output-json "${OUTPUT}/smoke.json"

apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 "${ENV_DIR}/bin/python" - \
  "${TASK}" "${SOURCE_MANIFEST}" "${OUTPUT}/unit-tests.txt" \
  "${OUTPUT}/egl-smoke.txt" "${OUTPUT}/dataset-resolution.txt" \
  "${OUTPUT}/smoke.json" "${OUTPUT}/gate.json" <<'PYTHON'
import hashlib
import json
import pathlib
import sys


def digest(path):
    value = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


task, source, tests, egl_smoke, dataset_resolution, smoke, output = sys.argv[1:]
if pathlib.Path(egl_smoke).read_text(encoding="utf-8").strip() != "dm_control_egl_import=pass":
    raise SystemExit("dm_control EGL smoke did not pass")
if not pathlib.Path(dataset_resolution).read_text(encoding="utf-8").startswith("dataset_resolution=pass\n"):
    raise SystemExit("logical dataset resolution smoke did not pass")
payload = json.loads(pathlib.Path(smoke).read_text(encoding="utf-8"))
if payload.get("status") != "ok":
    raise SystemExit("wrapper smoke did not pass")
result = {
    "status": "pass",
    "kind": "acid_alternative_task_preflight_v1",
    "task": task,
    "source_manifest_sha256": digest(source),
    "unit_tests_sha256": digest(tests),
    "egl_smoke_sha256": digest(egl_smoke),
    "dataset_resolution_sha256": digest(dataset_resolution),
    "smoke_sha256": digest(smoke),
}
pathlib.Path(output).write_text(
    json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
PYTHON
printf '%s\n' "task=${TASK}" "job_id=${SLURM_JOB_ID}" "node=$(hostname)" \
  > "${OUTPUT}/provenance.txt"
sha256sum "$0" "${SOURCE_MANIFEST}" "${OUTPUT}/unit-tests.txt" \
  "${OUTPUT}/egl-smoke.txt" "${OUTPUT}/dataset-resolution.txt" \
  "${OUTPUT}/smoke.json" "${OUTPUT}/gate.json" "${OUTPUT}/provenance.txt" \
  > "${OUTPUT}/sha256.txt"
