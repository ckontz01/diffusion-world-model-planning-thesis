#!/usr/bin/env bash

# 2 locked strata x 24 pools x 5 frozen repeats.

#SBATCH --job-name=p3-real-exec
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --array=0-239%4
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=01:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/p3-real-exec-%A_%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/p3-real-exec-%A_%a.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
STABLEWM_HOME="${ROOT}/data/stablewm"
SCRIPT="${ROOT}/scripts/execute_p2_real_frame_candidates.py"
RUNNER="${ROOT}/scripts/run_p3_real_frame_execution_array.slurm"
LOCK="${ROOT}/protocol/P3-PRE-EXECUTION-LOCK-2026-08-09.md"
LOCK_SHA256="a9f5c93bea7562c9f83c97c74f1cbf6041772626f3abd4d20fcd236a0b385d35"
CANDIDATE_DIR="${STABLEWM_HOME}/derived/candidate-pools/pusht-v1/p3-real-frame-job-295090"
STATS_DIR="${STABLEWM_HOME}/derived/latents/hi-lewm-pusht-epoch15/p1-train-stats-job-294596"
DATASET="${STABLEWM_HOME}/pusht_expert_train.h5"
CHECKPOINT="${STABLEWM_HOME}/runs/pusht_hierarchical_default/pusht_hierarchical_default_epoch_15_object.ckpt"

STRATUM_INDEX=$((SLURM_ARRAY_TASK_ID / 120))
WITHIN_STRATUM=$((SLURM_ARRAY_TASK_ID % 120))
POOL_INDEX=$((WITHIN_STRATUM / 5))
REPEAT_INDEX=$((WITHIN_STRATUM % 5))
printf -v POOL_PAD "%02d" "${POOL_INDEX}"
OUTPUT_ROOT="${STABLEWM_HOME}/derived/candidate-executions/pusht-v1/p3-real-frame-job-${SLURM_ARRAY_JOB_ID}"
OUTPUT_DIR="${OUTPUT_ROOT}/stratum-${STRATUM_INDEX}/pool-${POOL_PAD}-repeat-${REPEAT_INDEX}"
JOB_TMP="/tmp/ckontzias-p3-real-exec-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"

REQUIRED=(
  "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${LOCK}"
  "${CANDIDATE_DIR}/candidate-pools.h5" "${CANDIDATE_DIR}/manifest.json" "${CANDIDATE_DIR}/checksums.sha256"
  "${STATS_DIR}/stats.npz" "${STATS_DIR}/manifest.json" "${STATS_DIR}/checksums.sha256"
  "${DATASET}" "${CHECKPOINT}"
)
for required in "${REQUIRED[@]}"; do
  if [[ ! -s "${required}" ]]; then echo "Missing or empty required input: ${required}" >&2; exit 2; fi
done
echo "${LOCK_SHA256}  ${LOCK}" | sha256sum -c - >/dev/null
(cd "${CANDIDATE_DIR}" && sha256sum -c checksums.sha256 >/dev/null)
if [[ -e "${OUTPUT_DIR}" ]]; then echo "Refusing to overwrite P3 real-frame execution: ${OUTPUT_DIR}" >&2; exit 2; fi
mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT

export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
mkdir -p "${APPTAINER_TMPDIR}"

{
  echo "classification=p3_real_frame_candidate_attainment_execution"
  echo "job_id=${SLURM_ARRAY_JOB_ID}"
  echo "array_task_id=${SLURM_ARRAY_TASK_ID}"
  echo "stratum_index=${STRATUM_INDEX}"
  echo "pool_index=${POOL_INDEX}"
  echo "repeat_index=${REPEAT_INDEX}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${LOCK}" \
    "${CANDIDATE_DIR}/candidate-pools.h5" "${CANDIDATE_DIR}/manifest.json" \
    "${CANDIDATE_DIR}/checksums.sha256" "${STATS_DIR}/stats.npz" \
    "${STATS_DIR}/manifest.json" "${STATS_DIR}/checksums.sha256" "${CHECKPOINT}"
  nvidia-smi --query-gpu=name,uuid,driver_version,memory.total --format=csv,noheader
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --nv --cleanenv \
  --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONPATH="'"${CODE}"':'"${CODE}"'/third_party/lewm:'"${CODE}"'/scripts/diagnostics"
    export STABLEWM_HOME="'"${STABLEWM_HOME}"'"
    export PYTHONHASHSEED=42
    export CUBLAS_WORKSPACE_CONFIG=:4096:8
    export EVAL_DETERMINISM=strict
    export TMPDIR="'"${JOB_TMP}"'"
    export MPLBACKEND=Agg
    export MUJOCO_GL=egl
    cd "'"${CODE}"'"
    python "'"${SCRIPT}"'" \
      --partition P3 \
      --candidate-h5 "'"${CANDIDATE_DIR}"'/candidate-pools.h5" \
      --candidate-manifest "'"${CANDIDATE_DIR}"'/manifest.json" \
      --dataset "'"${DATASET}"'" \
      --stablewm-home "'"${STABLEWM_HOME}"'" \
      --eval-config "'"${CODE}"'/h_le_wm/config/eval/hi_pusht.yaml" \
      --policy runs/pusht_hierarchical_default/pusht_hierarchical_default_epoch_15 \
      --checkpoint-file "'"${CHECKPOINT}"'" \
      --stats-npz "'"${STATS_DIR}"'/stats.npz" \
      --stats-manifest "'"${STATS_DIR}"'/manifest.json" \
      --stratum-index "'"${STRATUM_INDEX}"'" \
      --pool-index "'"${POOL_INDEX}"'" \
      --repeat-index "'"${REPEAT_INDEX}"'" \
      --candidate-start 0 --candidate-count 64 \
      --low-num-samples 1200 --low-iters 30 --low-topk 150 \
      --cost-env-chunk-size 16 \
      --output-h5 "'"${OUTPUT_DIR}"'/executions.h5" \
      --output-json "'"${OUTPUT_DIR}"'/manifest.json"
  '

test -s "${OUTPUT_DIR}/executions.h5"
test -s "${OUTPUT_DIR}/manifest.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 | sort -z | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
