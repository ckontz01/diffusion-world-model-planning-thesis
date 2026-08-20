#!/usr/bin/env bash

# B0/B1 x 12 immutable Cube P2 D75 environment-selection queries.

#SBATCH --job-name=cube-b0-b1-gate
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --array=0-23%1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/cube-b0-b1-gate-%A_%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/cube-b0-b1-gate-%A_%a.err

set -euo pipefail
ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
SCRIPT="${ROOT}/scripts/run_cube_b0_b1_d75_query.py"
RUNNER="${ROOT}/scripts/run_cube_b0_b1_d75_gate_array.slurm"
STABLEWM_HOME="${ROOT}/data/stablewm"
QUERY_DIR="${STABLEWM_HOME}/derived/environment-selection/cube-v1/p2-d75-query-job-295156"
DATASET="${STABLEWM_HOME}/cube_single_expert.h5"
CHECKPOINT="${STABLEWM_HOME}/runs/cube_hierarchical_default/cube_hierarchical_default_epoch_15_object.ckpt"
EVAL_CONFIG="${CODE}/h_le_wm/config/eval/hi_cube.yaml"
OSMESA_ROOT="${ROOT}/software/osmesa-ubuntu22.04"
OSMESA_LIBDIR="${OSMESA_ROOT}/prefix/usr/lib/x86_64-linux-gnu"
OUTPUT_ROOT="${STABLEWM_HOME}/derived/environment-selection/cube-v1/b0-b1-d75-job-${SLURM_ARRAY_JOB_ID}"
JOB_TMP="/tmp/ckontzias-cube-b0-b1-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"

ARMS=(B0 B1)
arm_index=$(( SLURM_ARRAY_TASK_ID / 12 ))
query_index=$(( SLURM_ARRAY_TASK_ID % 12 ))
arm="${ARMS[arm_index]}"
printf -v QUERY_PAD "%02d" "${query_index}"
OUTPUT_DIR="${OUTPUT_ROOT}/arm-${arm}/query-${QUERY_PAD}"

for required in "${IMAGE}" "${SCRIPT}" "${RUNNER}" \
  "${QUERY_DIR}/queries.h5" "${QUERY_DIR}/manifest.json" "${QUERY_DIR}/checksums.sha256" \
  "${DATASET}" "${CHECKPOINT}" "${EVAL_CONFIG}" \
  "${OSMESA_LIBDIR}/libOSMesa.so.8" "${OSMESA_ROOT}/checksums.sha256"; do
  if [[ ! -s "${required}" ]]; then echo "Missing Cube gate input: ${required}" >&2; exit 2; fi
done
(cd "${QUERY_DIR}" && sha256sum -c checksums.sha256 >/dev/null)
(cd "${OSMESA_ROOT}" && sha256sum -c checksums.sha256 >/dev/null)
if [[ -e "${OUTPUT_DIR}" ]]; then echo "Refusing to overwrite Cube gate result" >&2; exit 2; fi
mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT
export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
mkdir -p "${APPTAINER_TMPDIR}"

{
  echo "classification=cube_p2_d75_environment_substitution_gate"
  echo "array_job_id=${SLURM_ARRAY_JOB_ID}"
  echo "array_task_id=${SLURM_ARRAY_TASK_ID}"
  echo "arm=${arm}"
  echo "query_index=${query_index}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${CHECKPOINT}" \
    "${EVAL_CONFIG}" "${QUERY_DIR}/queries.h5" "${QUERY_DIR}/manifest.json" \
    "${OSMESA_ROOT}/manifest.txt" "${OSMESA_ROOT}/checksums.sha256"
  nvidia-smi --query-gpu=name,uuid,driver_version,memory.total --format=csv,noheader
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONPATH="'"${ROOT}"'/scripts:'"${CODE}"'/scripts/diagnostics:'"${CODE}"':'"${CODE}"'/third_party/lewm"
    export STABLEWM_HOME="'"${STABLEWM_HOME}"'"
    export PYTHONHASHSEED=20260728
    export CUBLAS_WORKSPACE_CONFIG=:4096:8
    export EVAL_DETERMINISM=strict
    export LD_LIBRARY_PATH="'"${OSMESA_LIBDIR}"':${LD_LIBRARY_PATH:-}"
    export TMPDIR="'"${JOB_TMP}"'"
    export MPLBACKEND=Agg
    export MUJOCO_GL=osmesa
    export PYOPENGL_PLATFORM=osmesa
    export SDL_VIDEODRIVER=dummy
    cd "'"${CODE}"'"
    python "'"${SCRIPT}"'" --query-dir "'"${QUERY_DIR}"'" \
      --dataset "'"${DATASET}"'" --checkpoint-file "'"${CHECKPOINT}"'" \
      --policy runs/cube_hierarchical_default/cube_hierarchical_default_epoch_15 \
      --stablewm-home "'"${STABLEWM_HOME}"'" --eval-config "'"${EVAL_CONFIG}"'" \
      --arm "'"${arm}"'" --query-index "'"${query_index}"'" \
      --output-h5 "'"${OUTPUT_DIR}"'/result.h5" \
      --output-json "'"${OUTPUT_DIR}"'/manifest.json"
  '

test -s "${OUTPUT_DIR}/result.h5"; test -s "${OUTPUT_DIR}/manifest.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 | sort -z | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
