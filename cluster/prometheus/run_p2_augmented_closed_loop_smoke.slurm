#!/usr/bin/env bash

# Full-budget one-query release gate for the P2 augmented closed-loop array.

#SBATCH --job-name=p2-aug-smoke
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/p2-aug-smoke-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/p2-aug-smoke-%j.err

set -euo pipefail
: "${TRUE_SCORE_JOB_ID:?submit with TRUE_SCORE_JOB_ID set to the completed P2 true-scorer selection job}"
: "${CALIBRATION_JOB_ID:?submit with CALIBRATION_JOB_ID set to the completed P2 calibration job}"

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
SCRIPT="${ROOT}/scripts/run_p2_augmented_closed_loop_query.py"
WRAPPER="${ROOT}/scripts/feasibility_augmented_high_cost.py"
RUNNER="${ROOT}/scripts/run_p2_augmented_closed_loop_smoke.slurm"
AMENDMENTS="${ROOT}/protocol/PROTOCOL-IMPLEMENTATION-AMENDMENTS-2026-08-08.md"
STABLEWM_HOME="${ROOT}/data/stablewm"
CANDIDATE_DIR="${STABLEWM_HOME}/derived/candidate-pools/pusht-v1/p2-stratum3-b0-d75-h2-job-294604"
TRUE_DIR="${STABLEWM_HOME}/derived/scorer-audits/pusht-v1/p2-true-selection-job-${TRUE_SCORE_JOB_ID}"
CALIBRATION_DIR="${STABLEWM_HOME}/derived/scorer-audits/pusht-v1/p2-null-control-calibration-job-${CALIBRATION_JOB_ID}"
M1_ROOT="${STABLEWM_HOME}/runs/scorers/m1/pusht-v1"
M2_ROOT="${STABLEWM_HOME}/derived/scorers/m2-diffusion-pusht-v1"
M3_ROOT="${STABLEWM_HOME}/derived/scorers/m3-trm-pusht-v1"
NOISE_DIR="${ROOT}/manifests/scorers/pusht-v1/m2-score-noise-seed-20260728"
DATASET="${STABLEWM_HOME}/pusht_expert_train.h5"
CHECKPOINT="${STABLEWM_HOME}/runs/pusht_hierarchical_default/pusht_hierarchical_default_epoch_15_object.ckpt"
EVAL_CONFIG="${CODE}/h_le_wm/config/eval/hi_pusht.yaml"
OUTPUT_DIR="${STABLEWM_HOME}/derived/closed-loop-development/pusht-v1/augmented-smoke-job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-p2-aug-smoke-${SLURM_JOB_ID}"

REQUIRED=(
  "${IMAGE}" "${SCRIPT}" "${WRAPPER}" "${RUNNER}" "${AMENDMENTS}"
  "${CANDIDATE_DIR}/candidate-pools.h5" "${CANDIDATE_DIR}/manifest.json" "${CANDIDATE_DIR}/checksums.sha256"
  "${TRUE_DIR}/scores.h5" "${TRUE_DIR}/manifest.json" "${TRUE_DIR}/checksums.sha256"
  "${CALIBRATION_DIR}/audit-and-calibrators.h5" "${CALIBRATION_DIR}/manifest.json" "${CALIBRATION_DIR}/checksums.sha256"
  "${NOISE_DIR}/noise.npy" "${NOISE_DIR}/manifest.json" "${NOISE_DIR}/checksums.sha256"
  "${DATASET}" "${CHECKPOINT}" "${EVAL_CONFIG}"
)
for required in "${REQUIRED[@]}"; do
  if [[ ! -s "${required}" ]]; then
    echo "Missing or empty required input: ${required}" >&2
    exit 2
  fi
done
for required_dir in "${M1_ROOT}" "${M2_ROOT}" "${M3_ROOT}"; do
  if [[ ! -d "${required_dir}" ]]; then
    echo "Missing scorer root: ${required_dir}" >&2
    exit 2
  fi
done
if [[ -e "${OUTPUT_DIR}" ]]; then
  echo "Refusing to overwrite augmented smoke output: ${OUTPUT_DIR}" >&2
  exit 2
fi
mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() {
  rm -rf -- "${JOB_TMP}"
}
trap cleanup EXIT

export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
mkdir -p "${APPTAINER_TMPDIR}"

{
  echo "classification=p2_augmented_closed_loop_full_budget_smoke"
  echo "job_id=${SLURM_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "method=M2"
  echo "weight=1.0"
  echo "pool_index=0"
  echo "true_score_job_id=${TRUE_SCORE_JOB_ID}"
  echo "calibration_job_id=${CALIBRATION_JOB_ID}"
  sha256sum "${IMAGE}" "${SCRIPT}" "${WRAPPER}" "${RUNNER}" "${AMENDMENTS}" \
    "${ROOT}/scripts/score_and_select_p2_true_scorers.py" \
    "${ROOT}/scripts/train_m1_macro_cycle_head.py" \
    "${ROOT}/scripts/train_m2_diffusion_head.py" \
    "${ROOT}/scripts/train_m3_temporal_head.py" \
    "${ROOT}/scripts/execute_fixed_subgoal_candidates.py" \
    "${EVAL_CONFIG}" "${CHECKPOINT}" \
    "${CANDIDATE_DIR}/manifest.json" "${CANDIDATE_DIR}/checksums.sha256" \
    "${TRUE_DIR}/manifest.json" "${TRUE_DIR}/checksums.sha256" \
    "${CALIBRATION_DIR}/manifest.json" "${CALIBRATION_DIR}/checksums.sha256" \
    "${NOISE_DIR}/manifest.json" "${NOISE_DIR}/checksums.sha256"
  nvidia-smi --query-gpu=name,uuid,driver_version,memory.total --format=csv,noheader
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --nv --cleanenv \
  --bind "${ROOT}:${ROOT}" \
  --bind "${JOB_TMP}:${JOB_TMP}" \
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
      --candidate-dir "'"${CANDIDATE_DIR}"'" \
      --true-selection-dir "'"${TRUE_DIR}"'" \
      --calibration-dir "'"${CALIBRATION_DIR}"'" \
      --m1-root "'"${M1_ROOT}"'" \
      --m2-root "'"${M2_ROOT}"'" \
      --m3-root "'"${M3_ROOT}"'" \
      --noise-npy "'"${NOISE_DIR}"'/noise.npy" \
      --noise-manifest "'"${NOISE_DIR}"'/manifest.json" \
      --dataset "'"${DATASET}"'" \
      --checkpoint-file "'"${CHECKPOINT}"'" \
      --policy runs/pusht_hierarchical_default/pusht_hierarchical_default_epoch_15 \
      --stablewm-home "'"${STABLEWM_HOME}"'" \
      --eval-config "'"${EVAL_CONFIG}"'" \
      --method M2 --weight 1.0 --pool-index 0 \
      --output-h5 "'"${OUTPUT_DIR}"'/result.h5" \
      --output-json "'"${OUTPUT_DIR}"'/manifest.json" \
      --m2-batch-size 2048
  '

test -s "${OUTPUT_DIR}/result.h5"
test -s "${OUTPUT_DIR}/manifest.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 \
  | sort -z \
  | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
