#!/usr/bin/env bash

# Outcome-blind materialization of the 40 frozen P4 D75 queries and seeds.

#SBATCH --job-name=p4-query-freeze
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=12G
#SBATCH --time=00:30:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/p4-query-freeze-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/p4-query-freeze-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
SCRIPT="${ROOT}/scripts/create_p4_closed_loop_queries.py"
RUNNER="${ROOT}/scripts/run_create_p4_closed_loop_queries.slurm"
LOCK="${ROOT}/protocol/P3-PRE-EXECUTION-LOCK-2026-08-09.md"
LOCK_SHA256="a9f5c93bea7562c9f83c97c74f1cbf6041772626f3abd4d20fcd236a0b385d35"
LATENT_DIR="${ROOT}/data/stablewm/derived/latents/hi-lewm-pusht-epoch15/p4-job-294788"
PARTITION_MANIFEST="${ROOT}/manifests/partitions/pusht-v1/episodes-seed-20260728.tsv"
OUTPUT_DIR="${ROOT}/data/stablewm/derived/closed-loop-confirmation/pusht-v1/p4-query-artifact-job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-p4-query-freeze-${SLURM_JOB_ID}"

REQUIRED=(
  "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${LOCK}" "${PARTITION_MANIFEST}"
  "${LATENT_DIR}/latents.h5" "${LATENT_DIR}/manifest.json" "${LATENT_DIR}/checksums.sha256"
)
for required in "${REQUIRED[@]}"; do
  if [[ ! -s "${required}" ]]; then echo "Missing or empty required input: ${required}" >&2; exit 2; fi
done
echo "${LOCK_SHA256}  ${LOCK}" | sha256sum -c - >/dev/null
(cd "${LATENT_DIR}" && sha256sum -c checksums.sha256 >/dev/null)
if [[ -e "${OUTPUT_DIR}" ]]; then echo "Refusing to overwrite P4 query artifact: ${OUTPUT_DIR}" >&2; exit 2; fi
mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT

{
  echo "classification=p4_closed_loop_d75_queries"
  echo "p4_latent_job_id=294788"
  echo "job_id=${SLURM_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${LOCK}" \
    "${LATENT_DIR}/latents.h5" "${LATENT_DIR}/manifest.json" \
    "${LATENT_DIR}/checksums.sha256" "${PARTITION_MANIFEST}"
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONHASHSEED=20260728
    export TMPDIR="'"${JOB_TMP}"'"
    python "'"${SCRIPT}"'" \
      --latent-dir "'"${LATENT_DIR}"'" \
      --partition-manifest "'"${PARTITION_MANIFEST}"'" \
      --output-h5 "'"${OUTPUT_DIR}"'/queries.h5" \
      --output-json "'"${OUTPUT_DIR}"'/manifest.json"
  '

test -s "${OUTPUT_DIR}/queries.h5"; test -s "${OUTPUT_DIR}/manifest.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 | sort -z | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
