#!/usr/bin/env bash

# One promoted scorer arm x 40 immutable P4 PushT D75 queries.

#SBATCH --job-name=p4-aug-arm
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --array=0-39%4
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/p4-aug-arm-%A_%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/p4-aug-arm-%A_%a.err

set -euo pipefail
: "${METHOD:?submit with METHOD set to one of M1, M2, or M3}"
: "${PROMOTION_JOB_ID:?submit with PROMOTION_JOB_ID set to the locked P3 scorer-audit job}"

case "${METHOD}" in
  M1) WEIGHT="2.0" ;;
  M2) WEIGHT="1.0" ;;
  M3) WEIGHT="0.25" ;;
  *) echo "METHOD must be M1, M2, or M3; got ${METHOD}" >&2; exit 2 ;;
esac

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
SCRIPT="${ROOT}/scripts/run_p2_augmented_closed_loop_query.py"
WRAPPER="${ROOT}/scripts/feasibility_augmented_high_cost.py"
RUNNER="${ROOT}/scripts/run_p4_augmented_closed_loop_arm_array.slurm"
LOCK="${ROOT}/protocol/P3-PRE-EXECUTION-LOCK-2026-08-09.md"
LOCK_SHA256="a9f5c93bea7562c9f83c97c74f1cbf6041772626f3abd4d20fcd236a0b385d35"
STABLEWM_HOME="${ROOT}/data/stablewm"
QUERY_DIR="${STABLEWM_HOME}/derived/closed-loop-confirmation/pusht-v1/p4-query-artifact-job-295120"
PROMOTION_DIR="${STABLEWM_HOME}/derived/scorer-audits/pusht-v1/p3-locked-audit-job-${PROMOTION_JOB_ID}"
TRUE_DIR="${STABLEWM_HOME}/derived/scorer-audits/pusht-v1/p2-true-selection-job-294839"
CALIBRATION_DIR="${STABLEWM_HOME}/derived/scorer-audits/pusht-v1/p2-null-control-calibration-job-294843"
M1_ROOT="${STABLEWM_HOME}/runs/scorers/m1/pusht-v1"
M2_ROOT="${STABLEWM_HOME}/derived/scorers/m2-diffusion-pusht-v1"
M3_ROOT="${STABLEWM_HOME}/derived/scorers/m3-trm-pusht-v1"
NOISE_DIR="${ROOT}/manifests/scorers/pusht-v1/m2-score-noise-seed-20260728"
DATASET="${STABLEWM_HOME}/pusht_expert_train.h5"
CHECKPOINT="${STABLEWM_HOME}/runs/pusht_hierarchical_default/pusht_hierarchical_default_epoch_15_object.ckpt"
EVAL_CONFIG="${CODE}/h_le_wm/config/eval/hi_pusht.yaml"
QUERY_INDEX="${SLURM_ARRAY_TASK_ID}"
printf -v QUERY_PAD "%02d" "${QUERY_INDEX}"
OUTPUT_ROOT="${STABLEWM_HOME}/derived/closed-loop-confirmation/pusht-v1/augmented-${METHOD}-job-${SLURM_ARRAY_JOB_ID}"
OUTPUT_DIR="${OUTPUT_ROOT}/query-${QUERY_PAD}"
JOB_TMP="/tmp/ckontzias-p4-aug-${METHOD}-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"

REQUIRED=(
  "${IMAGE}" "${SCRIPT}" "${WRAPPER}" "${RUNNER}" "${LOCK}"
  "${QUERY_DIR}/queries.h5" "${QUERY_DIR}/manifest.json" "${QUERY_DIR}/checksums.sha256"
  "${PROMOTION_DIR}/audit.h5" "${PROMOTION_DIR}/manifest.json" "${PROMOTION_DIR}/checksums.sha256"
  "${TRUE_DIR}/scores.h5" "${TRUE_DIR}/manifest.json" "${TRUE_DIR}/checksums.sha256"
  "${CALIBRATION_DIR}/audit-and-calibrators.h5" "${CALIBRATION_DIR}/manifest.json" "${CALIBRATION_DIR}/checksums.sha256"
  "${NOISE_DIR}/noise.npy" "${NOISE_DIR}/manifest.json" "${NOISE_DIR}/checksums.sha256"
  "${DATASET}" "${CHECKPOINT}" "${EVAL_CONFIG}"
)
for required in "${REQUIRED[@]}"; do
  if [[ ! -s "${required}" ]]; then echo "Missing or empty required input: ${required}" >&2; exit 2; fi
done
for required_dir in "${M1_ROOT}" "${M2_ROOT}" "${M3_ROOT}"; do
  if [[ ! -d "${required_dir}" ]]; then echo "Missing scorer root: ${required_dir}" >&2; exit 2; fi
done
echo "${LOCK_SHA256}  ${LOCK}" | sha256sum -c - >/dev/null
(cd "${QUERY_DIR}" && sha256sum -c checksums.sha256 >/dev/null)
(cd "${PROMOTION_DIR}" && sha256sum -c checksums.sha256 >/dev/null)
(cd "${TRUE_DIR}" && sha256sum -c checksums.sha256 >/dev/null)
(cd "${CALIBRATION_DIR}" && sha256sum -c checksums.sha256 >/dev/null)
(cd "${NOISE_DIR}" && sha256sum -c checksums.sha256 >/dev/null)
if [[ -e "${OUTPUT_DIR}" ]]; then echo "Refusing to overwrite P4 result: ${OUTPUT_DIR}" >&2; exit 2; fi
mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT
export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
mkdir -p "${APPTAINER_TMPDIR}"

{
  echo "classification=p4_augmented_closed_loop_confirmation"
  echo "array_job_id=${SLURM_ARRAY_JOB_ID}"
  echo "array_task_id=${SLURM_ARRAY_TASK_ID}"
  echo "method=${METHOD}"
  echo "weight=${WEIGHT}"
  echo "query_index=${QUERY_INDEX}"
  echo "promotion_job_id=${PROMOTION_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "${SCRIPT}" "${WRAPPER}" "${RUNNER}" "${LOCK}" \
    "${ROOT}/scripts/score_and_select_p2_true_scorers.py" \
    "${ROOT}/scripts/train_m1_macro_cycle_head.py" \
    "${ROOT}/scripts/train_m2_diffusion_head.py" \
    "${ROOT}/scripts/train_m3_temporal_head.py" \
    "${ROOT}/scripts/execute_fixed_subgoal_candidates.py" \
    "${EVAL_CONFIG}" "${CHECKPOINT}" "${QUERY_DIR}/queries.h5" \
    "${QUERY_DIR}/manifest.json" "${PROMOTION_DIR}/audit.h5" \
    "${PROMOTION_DIR}/manifest.json" "${TRUE_DIR}/manifest.json" \
    "${CALIBRATION_DIR}/manifest.json" "${NOISE_DIR}/manifest.json"
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
      --partition P4 --promotion-dir "'"${PROMOTION_DIR}"'" \
      --candidate-dir "'"${QUERY_DIR}"'" \
      --true-selection-dir "'"${TRUE_DIR}"'" \
      --calibration-dir "'"${CALIBRATION_DIR}"'" \
      --m1-root "'"${M1_ROOT}"'" --m2-root "'"${M2_ROOT}"'" --m3-root "'"${M3_ROOT}"'" \
      --noise-npy "'"${NOISE_DIR}"'/noise.npy" --noise-manifest "'"${NOISE_DIR}"'/manifest.json" \
      --dataset "'"${DATASET}"'" --checkpoint-file "'"${CHECKPOINT}"'" \
      --policy runs/pusht_hierarchical_default/pusht_hierarchical_default_epoch_15 \
      --stablewm-home "'"${STABLEWM_HOME}"'" --eval-config "'"${EVAL_CONFIG}"'" \
      --method "'"${METHOD}"'" --weight "'"${WEIGHT}"'" --pool-index "'"${QUERY_INDEX}"'" \
      --output-h5 "'"${OUTPUT_DIR}"'/result.h5" --output-json "'"${OUTPUT_DIR}"'/manifest.json" \
      --m2-batch-size 2048
  '

test -s "${OUTPUT_DIR}/result.h5"; test -s "${OUTPUT_DIR}/manifest.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 | sort -z | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
