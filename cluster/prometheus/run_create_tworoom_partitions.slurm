#!/usr/bin/env bash

#SBATCH --job-name=tworoom-partitions
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-partitions-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-partitions-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
SCRIPT="${ROOT}/scripts/create_episode_partitions.py"
RUNNER="${ROOT}/scripts/run_create_tworoom_partitions.slurm"
DATASET="${ROOT}/data/stablewm/tworoom.h5"
EXPECTED_DATASET_BYTES=12775849984
EXPECTED_DATASET_SHA256="129a36aa93ea0de488d2bcc876e396de9e3907bf66c6aae6394e542ef6a6d623"
OUTPUT_DIR="${ROOT}/manifests/partitions/tworoom-v1"
OUTPUT_TSV="${OUTPUT_DIR}/episodes-seed-20260728.tsv"
OUTPUT_JSON="${OUTPUT_DIR}/episodes-seed-20260728-summary.json"
JOB_TMP="/tmp/ckontzias-tworoom-partitions-${SLURM_JOB_ID}"

for required in "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${DATASET}"; do
  if [[ ! -s "${required}" ]]; then echo "Missing TwoRoom partition input: ${required}" >&2; exit 2; fi
done
if [[ $(stat -c %s "${DATASET}") -ne ${EXPECTED_DATASET_BYTES} ]]; then echo "TwoRoom dataset byte-size mismatch" >&2; exit 2; fi
echo "${EXPECTED_DATASET_SHA256}  ${DATASET}" | sha256sum -c -
if [[ -e "${OUTPUT_TSV}" || -e "${OUTPUT_JSON}" ]]; then echo "Refusing to overwrite frozen TwoRoom partitions" >&2; exit 2; fi
mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT

{
  echo "classification=tworoom_episode_partitions"
  echo "job_id=${SLURM_JOB_ID}"
  echo "dataset_expected_bytes=${EXPECTED_DATASET_BYTES}"
  echo "dataset_expected_sha256=${EXPECTED_DATASET_SHA256}"
  echo "p0_exclusions=none_no_tworoom_episode_outcome_previously_exposed"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${SCRIPT}" "${RUNNER}"
} > "${OUTPUT_DIR}/partition-provenance.txt"

apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export TMPDIR="'"${JOB_TMP}"'"
    python "'"${SCRIPT}"'" "'"${DATASET}"'" \
      --dataset-name tworoom --seed 20260728 \
      --output-tsv "'"${OUTPUT_TSV}"'" --output-json "'"${OUTPUT_JSON}"'"
  '

test -s "${OUTPUT_TSV}"
test -s "${OUTPUT_JSON}"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/partition-provenance.txt"
sha256sum "${OUTPUT_TSV}" "${OUTPUT_JSON}" "${OUTPUT_DIR}/partition-provenance.txt" > "${OUTPUT_DIR}/partition-checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/partition-checksums.sha256"
