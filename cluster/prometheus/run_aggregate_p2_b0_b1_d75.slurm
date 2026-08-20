#!/usr/bin/env bash

# Submit with --export=ALL,INPUT_ARRAY_JOB_ID=<completed B0/B1 array job>.

#SBATCH --job-name=p2-b0-b1-decide
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/p2-b0-b1-decide-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/p2-b0-b1-decide-%j.err

set -euo pipefail
: "${INPUT_ARRAY_JOB_ID:?submit with INPUT_ARRAY_JOB_ID set to the B0/B1 array job}"

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
SCRIPT="${ROOT}/scripts/aggregate_p2_b0_b1_d75.py"
RUNNER="${ROOT}/scripts/run_aggregate_p2_b0_b1_d75.slurm"
STABLEWM_HOME="${ROOT}/data/stablewm"
INPUT_ROOT="${STABLEWM_HOME}/derived/closed-loop-development/pusht-v1/b0-b1-d75-grid-job-${INPUT_ARRAY_JOB_ID}"
OUTPUT_DIR="${STABLEWM_HOME}/derived/closed-loop-development/pusht-v1/b0-b1-d75-decision-job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-p2-b0-b1-decide-${SLURM_JOB_ID}"

for required in "${IMAGE}" "${SCRIPT}" "${RUNNER}"; do
  if [[ ! -s "${required}" ]]; then
    echo "Missing required file: ${required}" >&2
    exit 2
  fi
done
if [[ ! -d "${INPUT_ROOT}" ]]; then
  echo "Missing B0/B1 grid root: ${INPUT_ROOT}" >&2
  exit 2
fi
if [[ -e "${OUTPUT_DIR}" ]]; then
  echo "Refusing to overwrite B0/B1 decision output: ${OUTPUT_DIR}" >&2
  exit 2
fi
mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() {
  rm -rf -- "${JOB_TMP}"
}
trap cleanup EXIT

{
  echo "classification=p2_b0_b1_d75_difficulty_decision"
  echo "job_id=${SLURM_JOB_ID}"
  echo "input_array_job_id=${INPUT_ARRAY_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "${SCRIPT}" "${RUNNER}"
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --cleanenv \
  --bind "${ROOT}:${ROOT}" \
  --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONPATH="'"${ROOT}"'/scripts"
    export PYTHONHASHSEED=20260728
    export TMPDIR="'"${JOB_TMP}"'"
    python "'"${SCRIPT}"'" \
      --input-root "'"${INPUT_ROOT}"'" \
      --array-job-id "'"${INPUT_ARRAY_JOB_ID}"'" \
      --output-h5 "'"${OUTPUT_DIR}"'/decision.h5" \
      --output-json "'"${OUTPUT_DIR}"'/manifest.json"
  '

test -s "${OUTPUT_DIR}/decision.h5"
test -s "${OUTPUT_DIR}/manifest.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 \
  | sort -z \
  | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"

