#!/usr/bin/env bash

#SBATCH --job-name=p2-score-select
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:45:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/p2-score-select-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/p2-score-select-%j.err

set -euo pipefail
: "${LABELED_JOB_ID:?submit with LABELED_JOB_ID set to the completed P2 labeling job}"

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
SCRIPT="${ROOT}/scripts/score_and_select_p2_true_scorers.py"
STABLEWM_HOME="${ROOT}/data/stablewm"
LABELED_DIR="${STABLEWM_HOME}/derived/candidate-labels/pusht-v1/p2-stratum3-job-${LABELED_JOB_ID}"
M1_ROOT="${STABLEWM_HOME}/runs/scorers/m1/pusht-v1"
M2_ROOT="${STABLEWM_HOME}/derived/scorers/m2-diffusion-pusht-v1"
M3_ROOT="${STABLEWM_HOME}/derived/scorers/m3-trm-pusht-v1"
NOISE_DIR="${ROOT}/manifests/scorers/pusht-v1/m2-score-noise-seed-20260728"
OUTPUT_DIR="${STABLEWM_HOME}/derived/scorer-audits/pusht-v1/p2-true-selection-job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-p2-score-select-${SLURM_JOB_ID}"

REQUIRED=(
  "${LABELED_DIR}/labeled-candidates.h5"
  "${LABELED_DIR}/manifest.json"
  "${LABELED_DIR}/checksums.sha256"
  "${NOISE_DIR}/noise.npy"
  "${NOISE_DIR}/manifest.json"
  "${NOISE_DIR}/checksums.sha256"
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
  echo "Refusing to overwrite P2 scorer-selection output: ${OUTPUT_DIR}" >&2
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
  echo "classification=p2_true_scorer_raw_score_selection"
  echo "labeled_job_id=${LABELED_JOB_ID}"
  echo "m1_training_job_id=294616"
  echo "m2_training_job_id=294599"
  echo "m3_training_job_id=294595"
  echo "job_id=${SLURM_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "$0" "${SCRIPT}" \
    "${LABELED_DIR}/manifest.json" "${LABELED_DIR}/checksums.sha256" \
    "${NOISE_DIR}/noise.npy" "${NOISE_DIR}/manifest.json" \
    "${NOISE_DIR}/checksums.sha256"
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
      --m1-root "'"${M1_ROOT}"'" \
      --m2-root "'"${M2_ROOT}"'" \
      --m3-root "'"${M3_ROOT}"'" \
      --noise-npy "'"${NOISE_DIR}"'/noise.npy" \
      --noise-manifest "'"${NOISE_DIR}"'/manifest.json" \
      --output-h5 "'"${OUTPUT_DIR}"'/scores.h5" \
      --output-json "'"${OUTPUT_DIR}"'/manifest.json" \
      --device cuda \
      --m2-batch-size 2048
  '

test -s "${OUTPUT_DIR}/scores.h5"
test -s "${OUTPUT_DIR}/manifest.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 \
  | sort -z \
  | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
