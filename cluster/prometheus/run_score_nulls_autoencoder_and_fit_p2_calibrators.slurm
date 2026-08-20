#!/usr/bin/env bash

#SBATCH --job-name=p2-null-calibrate
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:45:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/p2-null-calibrate-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/p2-null-calibrate-%j.err

set -euo pipefail
: "${LABELED_JOB_ID:?submit with LABELED_JOB_ID set to the completed P2 labeling job}"
: "${TRUE_SCORE_JOB_ID:?submit with TRUE_SCORE_JOB_ID set to the completed P2 true-scorer selection job}"
: "${NULL_TRAINING_JOB_ID:?submit with NULL_TRAINING_JOB_ID set to the completed null-training array job}"
: "${AUTOENCODER_TRAINING_JOB_ID:?submit with AUTOENCODER_TRAINING_JOB_ID set to the completed autoencoder-training array job}"

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
SCRIPT="${ROOT}/scripts/score_nulls_autoencoder_and_fit_p2_calibrators.py"
STABLEWM_HOME="${ROOT}/data/stablewm"
LABELED_DIR="${STABLEWM_HOME}/derived/candidate-labels/pusht-v1/p2-stratum3-job-${LABELED_JOB_ID}"
TRUE_SCORE_DIR="${STABLEWM_HOME}/derived/scorer-audits/pusht-v1/p2-true-selection-job-${TRUE_SCORE_JOB_ID}"
M1_ROOT="${STABLEWM_HOME}/runs/scorers/m1/pusht-v1"
M2_ROOT="${STABLEWM_HOME}/derived/scorers/m2-diffusion-pusht-v1"
AUTOENCODER_ROOT="${STABLEWM_HOME}/derived/scorers/m2-autoencoder-pusht-v1"
NOISE_DIR="${ROOT}/manifests/scorers/pusht-v1/m2-score-noise-seed-20260728"
OUTPUT_DIR="${STABLEWM_HOME}/derived/scorer-audits/pusht-v1/p2-null-control-calibration-job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-p2-null-calibrate-${SLURM_JOB_ID}"

for required in \
  "${LABELED_DIR}/labeled-candidates.h5" \
  "${LABELED_DIR}/manifest.json" \
  "${LABELED_DIR}/checksums.sha256" \
  "${TRUE_SCORE_DIR}/scores.h5" \
  "${TRUE_SCORE_DIR}/manifest.json" \
  "${TRUE_SCORE_DIR}/checksums.sha256" \
  "${NOISE_DIR}/noise.npy" \
  "${NOISE_DIR}/manifest.json"; do
  if [[ ! -s "${required}" ]]; then
    echo "Missing or empty required input: ${required}" >&2
    exit 2
  fi
done
for required_dir in "${M1_ROOT}" "${M2_ROOT}" "${AUTOENCODER_ROOT}"; do
  if [[ ! -d "${required_dir}" ]]; then
    echo "Missing scorer root: ${required_dir}" >&2
    exit 2
  fi
done
if [[ -e "${OUTPUT_DIR}" ]]; then
  echo "Refusing to overwrite P2 null/control/calibration output: ${OUTPUT_DIR}" >&2
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
  echo "classification=p2_null_control_scores_and_calibrators"
  echo "labeled_job_id=${LABELED_JOB_ID}"
  echo "true_score_job_id=${TRUE_SCORE_JOB_ID}"
  echo "null_training_job_id=${NULL_TRAINING_JOB_ID}"
  echo "autoencoder_training_job_id=${AUTOENCODER_TRAINING_JOB_ID}"
  echo "job_id=${SLURM_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "$0" "${SCRIPT}" \
    "${LABELED_DIR}/manifest.json" "${LABELED_DIR}/checksums.sha256" \
    "${TRUE_SCORE_DIR}/manifest.json" "${TRUE_SCORE_DIR}/checksums.sha256" \
    "${NOISE_DIR}/noise.npy" "${NOISE_DIR}/manifest.json"
  nvidia-smi --query-gpu=name,uuid,driver_version,memory.total --format=csv,noheader
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --nv --cleanenv \
  --bind "${ROOT}:${ROOT}" \
  --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONPATH="'"${ROOT}"'/scripts"
    export PYTHONHASHSEED=20260728
    export CUBLAS_WORKSPACE_CONFIG=:4096:8
    export TMPDIR="'"${JOB_TMP}"'"
    python "'"${SCRIPT}"'" \
      --labeled-dir "'"${LABELED_DIR}"'" \
      --true-score-dir "'"${TRUE_SCORE_DIR}"'" \
      --m1-root "'"${M1_ROOT}"'" \
      --m2-root "'"${M2_ROOT}"'" \
      --autoencoder-root "'"${AUTOENCODER_ROOT}"'" \
      --noise-npy "'"${NOISE_DIR}"'/noise.npy" \
      --noise-manifest "'"${NOISE_DIR}"'/manifest.json" \
      --output-h5 "'"${OUTPUT_DIR}"'/audit-and-calibrators.h5" \
      --output-json "'"${OUTPUT_DIR}"'/manifest.json" \
      --null-job-id "'"${NULL_TRAINING_JOB_ID}"'" \
      --autoencoder-job-id "'"${AUTOENCODER_TRAINING_JOB_ID}"'" \
      --device cuda \
      --m2-batch-size 2048
  '

test -s "${OUTPUT_DIR}/audit-and-calibrators.h5"
test -s "${OUTPUT_DIR}/manifest.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 \
  | sort -z \
  | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
