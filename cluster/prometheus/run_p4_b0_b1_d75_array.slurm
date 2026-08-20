#!/usr/bin/env bash

# B0/B1 x the same 40 immutable P4 PushT D75 queries.

#SBATCH --job-name=p4-b0-b1-d75
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --array=0-79%4
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/p4-b0-b1-d75-%A_%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/p4-b0-b1-d75-%A_%a.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
SCRIPT="${ROOT}/scripts/run_p2_b0_b1_d75_query.py"
SHARED_SCRIPT="${ROOT}/scripts/run_p2_augmented_closed_loop_query.py"
RUNNER="${ROOT}/scripts/run_p4_b0_b1_d75_array.slurm"
LOCK="${ROOT}/protocol/P3-PRE-EXECUTION-LOCK-2026-08-09.md"
LOCK_SHA256="a9f5c93bea7562c9f83c97c74f1cbf6041772626f3abd4d20fcd236a0b385d35"
STABLEWM_HOME="${ROOT}/data/stablewm"
QUERY_DIR="${STABLEWM_HOME}/derived/closed-loop-confirmation/pusht-v1/p4-query-artifact-job-295120"
DATASET="${STABLEWM_HOME}/pusht_expert_train.h5"
CHECKPOINT="${STABLEWM_HOME}/runs/pusht_hierarchical_default/pusht_hierarchical_default_epoch_15_object.ckpt"
EVAL_CONFIG="${CODE}/h_le_wm/config/eval/hi_pusht.yaml"
OUTPUT_ROOT="${STABLEWM_HOME}/derived/closed-loop-confirmation/pusht-v1/b0-b1-d75-job-${SLURM_ARRAY_JOB_ID}"
JOB_TMP="/tmp/ckontzias-p4-b0-b1-d75-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"

ARMS=(B0 B1)
arm_index=$(( SLURM_ARRAY_TASK_ID / 40 ))
query_index=$(( SLURM_ARRAY_TASK_ID % 40 ))
arm="${ARMS[arm_index]}"
printf -v QUERY_PAD "%02d" "${query_index}"
OUTPUT_DIR="${OUTPUT_ROOT}/arm-${arm}/query-${QUERY_PAD}"

REQUIRED=(
  "${IMAGE}" "${SCRIPT}" "${SHARED_SCRIPT}" "${RUNNER}" "${LOCK}"
  "${ROOT}/scripts/execute_fixed_subgoal_candidates.py"
  "${QUERY_DIR}/queries.h5" "${QUERY_DIR}/manifest.json" "${QUERY_DIR}/checksums.sha256"
  "${DATASET}" "${CHECKPOINT}" "${EVAL_CONFIG}"
)
for required in "${REQUIRED[@]}"; do
  if [[ ! -s "${required}" ]]; then echo "Missing or empty required input: ${required}" >&2; exit 2; fi
done
echo "${LOCK_SHA256}  ${LOCK}" | sha256sum -c - >/dev/null
(cd "${QUERY_DIR}" && sha256sum -c checksums.sha256 >/dev/null)
if [[ -e "${OUTPUT_DIR}" ]]; then echo "Refusing to overwrite P4 baseline result: ${OUTPUT_DIR}" >&2; exit 2; fi
mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT
export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
mkdir -p "${APPTAINER_TMPDIR}"

{
  echo "classification=p4_b0_b1_d75_confirmation"
  echo "array_job_id=${SLURM_ARRAY_JOB_ID}"
  echo "array_task_id=${SLURM_ARRAY_TASK_ID}"
  echo "arm=${arm}"
  echo "query_index=${query_index}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "${SCRIPT}" "${SHARED_SCRIPT}" "${RUNNER}" "${LOCK}" \
    "${ROOT}/scripts/execute_fixed_subgoal_candidates.py" \
    "${CODE}/h_le_wm/planning/policies.py" "${EVAL_CONFIG}" "${CHECKPOINT}" \
    "${QUERY_DIR}/queries.h5" "${QUERY_DIR}/manifest.json"
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
    export TMPDIR="'"${JOB_TMP}"'"
    export MPLBACKEND=Agg
    export MUJOCO_GL=egl
    export SDL_VIDEODRIVER=dummy
    cd "'"${CODE}"'"
    python "'"${SCRIPT}"'" \
      --partition P4 --candidate-dir "'"${QUERY_DIR}"'" \
      --dataset "'"${DATASET}"'" --checkpoint-file "'"${CHECKPOINT}"'" \
      --policy runs/pusht_hierarchical_default/pusht_hierarchical_default_epoch_15 \
      --stablewm-home "'"${STABLEWM_HOME}"'" --eval-config "'"${EVAL_CONFIG}"'" \
      --arm "'"${arm}"'" --pool-index "'"${query_index}"'" \
      --output-h5 "'"${OUTPUT_DIR}"'/result.h5" --output-json "'"${OUTPUT_DIR}"'/manifest.json"
  '

test -s "${OUTPUT_DIR}/result.h5"; test -s "${OUTPUT_DIR}/manifest.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 | sort -z | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
