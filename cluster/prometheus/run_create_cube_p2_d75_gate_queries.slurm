#!/usr/bin/env bash

#SBATCH --job-name=cube-p2-gate-q
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/cube-p2-gate-q-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/cube-p2-gate-q-%j.err

set -euo pipefail
ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
SCRIPT="${ROOT}/scripts/create_cube_p2_d75_gate_queries.py"
RUNNER="${ROOT}/scripts/run_create_cube_p2_d75_gate_queries.slurm"
DATASET="${ROOT}/data/stablewm/cube_single_expert.h5"
PARTITIONS="${ROOT}/manifests/partitions/cube-v1/episodes-seed-20260728.tsv"
OUTPUT_DIR="${ROOT}/data/stablewm/derived/environment-selection/cube-v1/p2-d75-query-job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-cube-p2-gate-q-${SLURM_JOB_ID}"

for required in "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${DATASET}" "${PARTITIONS}"; do
  if [[ ! -s "${required}" ]]; then echo "Missing Cube query input: ${required}" >&2; exit 2; fi
done
if [[ -e "${OUTPUT_DIR}" ]]; then echo "Refusing to overwrite Cube gate queries" >&2; exit 2; fi
mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT

{
  echo "classification=cube_p2_d75_environment_gate_queries"
  echo "job_id=${SLURM_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${SCRIPT}" "${RUNNER}" "${PARTITIONS}"
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export TMPDIR="'"${JOB_TMP}"'"
    python "'"${SCRIPT}"'" --dataset "'"${DATASET}"'" \
      --partition-manifest "'"${PARTITIONS}"'" \
      --output-h5 "'"${OUTPUT_DIR}"'/queries.h5" \
      --output-json "'"${OUTPUT_DIR}"'/manifest.json"
  '

test -s "${OUTPUT_DIR}/queries.h5"; test -s "${OUTPUT_DIR}/manifest.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 | sort -z | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
