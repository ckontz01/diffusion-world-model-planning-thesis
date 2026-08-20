#!/usr/bin/env bash

# Read-only within-pool ranking audit for completed TwoRoom P2 artifacts.

#SBATCH --job-name=tworoom-p2-pool-audit
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=12G
#SBATCH --time=00:30:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-p2-pool-audit-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-p2-pool-audit-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
SCRIPT="${ROOT}/scripts/audit_p2_candidate_pool_ranking.py"
SHARED="${ROOT}/scripts/audit_candidate_pool_ranking.py"
RUNNER="${ROOT}/scripts/run_audit_tworoom_p2_candidate_pool_ranking.slurm"
SPEC="${ROOT}/protocol/TWOROOM-P2-POOL-RANKING-AUDIT-SPEC-2026-08-12.md"
: "${SPEC_SHA256:?submit with frozen SPEC_SHA256}"
DATA="${ROOT}/data/stablewm"
P2_DIR="${DATA}/derived/scorer-audits/tworoom-v1/p2-null-control-calibration-job-296059"
OUTPUT_DIR="${DATA}/derived/scorer-audits/tworoom-v1/p2-pool-ranking-audit-job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-tworoom-p2-pool-audit-${SLURM_JOB_ID}"

REQUIRED=(
  "${IMAGE}" "${SCRIPT}" "${SHARED}" "${RUNNER}" "${SPEC}"
  "${P2_DIR}/audit-and-calibrators.h5" "${P2_DIR}/manifest.json"
)
for required in "${REQUIRED[@]}"; do
  if [[ ! -s "${required}" ]]; then echo "Missing or empty input: ${required}" >&2; exit 2; fi
done
echo "${SPEC_SHA256}  ${SPEC}" | sha256sum -c - >/dev/null
if [[ -e "${OUTPUT_DIR}" ]]; then echo "Refusing to overwrite: ${OUTPUT_DIR}" >&2; exit 2; fi
mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT

{
  echo "classification=tworoom_p2_candidate_pool_ranking_audit"
  echo "job_id=${SLURM_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "${SCRIPT}" "${SHARED}" "${RUNNER}" "${SPEC}" \
    "${P2_DIR}/audit-and-calibrators.h5" "${P2_DIR}/manifest.json"
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
      --environment tworoom \
      --p2-h5 "'"${P2_DIR}"'/audit-and-calibrators.h5" \
      --p2-manifest "'"${P2_DIR}"'/manifest.json" \
      --spec "'"${SPEC}"'" \
      --output-h5 "'"${OUTPUT_DIR}"'/pool-ranking-audit.h5" \
      --output-json "'"${OUTPUT_DIR}"'/manifest.json"
  '

test -s "${OUTPUT_DIR}/pool-ranking-audit.h5"
test -s "${OUTPUT_DIR}/manifest.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 | sort -z | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
