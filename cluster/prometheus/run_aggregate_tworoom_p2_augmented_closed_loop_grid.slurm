#!/usr/bin/env bash

# Submit with --export=ALL,INPUT_ARRAY_JOB_ID=<completed TwoRoom grid array job>.

#SBATCH --job-name=tworoom-p2-aug-select
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-p2-aug-select-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-p2-aug-select-%j.err

set -euo pipefail
: "${INPUT_ARRAY_JOB_ID:?submit with INPUT_ARRAY_JOB_ID set to the completed TwoRoom augmented-grid array job}"

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
SCRIPT="${ROOT}/scripts/aggregate_p2_augmented_closed_loop_grid.py"
RUNNER="${ROOT}/scripts/run_aggregate_tworoom_p2_augmented_closed_loop_grid.slurm"
AMENDMENTS="${ROOT}/protocol/PROTOCOL-IMPLEMENTATION-AMENDMENTS-2026-08-08.md"
STABLEWM_HOME="${ROOT}/data/stablewm"
INPUT_ROOT="${STABLEWM_HOME}/derived/closed-loop-development/tworoom-v1/augmented-grid-job-${INPUT_ARRAY_JOB_ID}"
OUTPUT_DIR="${STABLEWM_HOME}/derived/closed-loop-development/tworoom-v1/augmented-selection-job-${SLURM_JOB_ID}"
CANONICAL="${STABLEWM_HOME}/derived/closed-loop-development/tworoom-v1/augmented-selection"
JOB_TMP="/tmp/ckontzias-tworoom-p2-aug-select-${SLURM_JOB_ID}"

EXPECTED_SCRIPT_SHA256="e934eee73ad7ac23f36f1c7a70cdd88482648c0976d000a85e3603cdb367f72c"

for required in "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${AMENDMENTS}"; do
  if [[ ! -s "${required}" ]]; then
    echo "Missing TwoRoom augmented-selection input: ${required}" >&2
    exit 2
  fi
done
printf '%s  %s\n' "${EXPECTED_SCRIPT_SHA256}" "${SCRIPT}" | sha256sum -c -
if [[ ! -d "${INPUT_ROOT}" ]]; then
  echo "Missing TwoRoom augmented-grid root: ${INPUT_ROOT}" >&2
  exit 2
fi
if [[ -e "${OUTPUT_DIR}" ]]; then
  echo "Refusing to overwrite TwoRoom augmented-selection output: ${OUTPUT_DIR}" >&2
  exit 2
fi
mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT

{
  echo "classification=tworoom_p2_augmented_closed_loop_weight_selection"
  echo "job_id=${SLURM_JOB_ID}"
  echo "input_array_job_id=${INPUT_ARRAY_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${AMENDMENTS}"
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
      --environment tworoom \
      --input-root "'"${INPUT_ROOT}"'" \
      --array-job-id "'"${INPUT_ARRAY_JOB_ID}"'" \
      --output-h5 "'"${OUTPUT_DIR}"'/selection.h5" \
      --output-json "'"${OUTPUT_DIR}"'/manifest.json"
  '

test -s "${OUTPUT_DIR}/selection.h5"
test -s "${OUTPUT_DIR}/manifest.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 \
  | sort -z \
  | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"

if [[ -e "${CANONICAL}" && ! -L "${CANONICAL}" ]]; then
  echo "Refusing to replace non-symlink canonical path: ${CANONICAL}" >&2
  exit 2
fi
ln -sfn "${OUTPUT_DIR}" "${CANONICAL}"
