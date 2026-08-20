#!/usr/bin/env bash

#SBATCH --job-name=tworoom-h5-inspect
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-h5-inspect-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-h5-inspect-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
SCRIPT="${ROOT}/scripts/inspect_hdf5_dataset.py"
RUNNER="${ROOT}/scripts/run_tworoom_dataset_inspection.slurm"
DATASET="${ROOT}/data/stablewm/tworoom.h5"
EXPECTED_DATASET_BYTES=12775849984
EXPECTED_DATASET_SHA256="129a36aa93ea0de488d2bcc876e396de9e3907bf66c6aae6394e542ef6a6d623"
OUTPUT_DIR="${ROOT}/manifests/datasets/tworoom-v1/inspection-job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-tworoom-inspect-${SLURM_JOB_ID}"

for required in "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${DATASET}"; do
  if [[ ! -s "${required}" ]]; then echo "Missing TwoRoom inspection input: ${required}" >&2; exit 2; fi
done
if [[ $(stat -c %s "${DATASET}") -ne ${EXPECTED_DATASET_BYTES} ]]; then echo "TwoRoom dataset byte-size mismatch" >&2; exit 2; fi
echo "${EXPECTED_DATASET_SHA256}  ${DATASET}" | sha256sum -c -
if [[ -e "${OUTPUT_DIR}" ]]; then echo "Refusing to overwrite TwoRoom inspection" >&2; exit 2; fi
mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT

{
  echo "classification=outcome_blind_tworoom_dataset_schema_inspection"
  echo "job_id=${SLURM_JOB_ID}"
  echo "dataset_expected_bytes=${EXPECTED_DATASET_BYTES}"
  echo "dataset_expected_sha256=${EXPECTED_DATASET_SHA256}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${SCRIPT}" "${RUNNER}"
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export TMPDIR="'"${JOB_TMP}"'"
    python "'"${SCRIPT}"'" "'"${DATASET}"'" --output-json "'"${OUTPUT_DIR}"'/inspection.json"
  '

test -s "${OUTPUT_DIR}/inspection.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 | sort -z | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
