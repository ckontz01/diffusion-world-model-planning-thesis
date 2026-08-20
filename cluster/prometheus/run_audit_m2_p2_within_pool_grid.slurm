#!/usr/bin/env bash

# P2-only reanalysis of all existing M2 width/sigma score grids.

#SBATCH --job-name=m2-p2-pool-grid
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/m2-p2-pool-grid-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/m2-p2-pool-grid-%j.err

set -euo pipefail
ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
SCRIPT="${ROOT}/scripts/audit_m2_p2_within_pool_grid.py"
SHARED="${ROOT}/scripts/audit_candidate_pool_ranking.py"
RUNNER="${ROOT}/scripts/run_audit_m2_p2_within_pool_grid.slurm"
SPEC="${ROOT}/protocol/M2-P2-WITHIN-POOL-GRID-AUDIT-SPEC-2026-08-12.md"
: "${SPEC_SHA256:?submit with frozen SPEC_SHA256}"
DATA="${ROOT}/data/stablewm/derived"
PUSHT="${DATA}/scorer-audits/pusht-v1/p2-true-selection-job-294839"
TWOROOM="${DATA}/scorer-audits/tworoom-v1/p2-true-selection-job-295869"
OUTPUT_DIR="${DATA}/scorer-audits/cross-environment/m2-p2-within-pool-grid-job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-m2-p2-pool-grid-${SLURM_JOB_ID}"

REQUIRED=("${IMAGE}" "${SCRIPT}" "${SHARED}" "${RUNNER}" "${SPEC}"
  "${PUSHT}/scores.h5" "${PUSHT}/manifest.json"
  "${TWOROOM}/scores.h5" "${TWOROOM}/manifest.json")
for required in "${REQUIRED[@]}"; do
  if [[ ! -s "${required}" ]]; then echo "Missing or empty input: ${required}" >&2; exit 2; fi
done
echo "${SPEC_SHA256}  ${SPEC}" | sha256sum -c - >/dev/null
if [[ -e "${OUTPUT_DIR}" ]]; then echo "Refusing to overwrite: ${OUTPUT_DIR}" >&2; exit 2; fi
mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT

{
  echo "classification=m2_p2_within_pool_grid_reanalysis"
  echo "job_id=${SLURM_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "${SCRIPT}" "${SHARED}" "${RUNNER}" "${SPEC}" \
    "${PUSHT}/scores.h5" "${PUSHT}/manifest.json" \
    "${TWOROOM}/scores.h5" "${TWOROOM}/manifest.json"
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONPATH="'"${ROOT}"'/scripts"
    export PYTHONHASHSEED=20260812
    export TMPDIR="'"${JOB_TMP}"'"
    python "'"${SCRIPT}"'" \
      --pusht-dir "'"${PUSHT}"'" --tworoom-dir "'"${TWOROOM}"'" \
      --spec "'"${SPEC}"'" --output-json "'"${OUTPUT_DIR}"'/manifest.json"
  '

test -s "${OUTPUT_DIR}/manifest.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 | sort -z | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
