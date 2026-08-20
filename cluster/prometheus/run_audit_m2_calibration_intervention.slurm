#!/usr/bin/env bash

# Read-only P2 audit of whether calibrated M2 could alter CEM ordering.

#SBATCH --job-name=m2-intervention-audit
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:15:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/m2-intervention-audit-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/m2-intervention-audit-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
SCRIPT="${ROOT}/scripts/audit_m2_calibration_intervention.py"
RUNNER="${ROOT}/scripts/run_audit_m2_calibration_intervention.slurm"
SPEC="${ROOT}/protocol/M2-P2-CALIBRATION-INTERVENTION-AUDIT-SPEC-2026-08-12.md"
ONLINE="${ROOT}/scripts/feasibility_augmented_high_cost.py"
: "${SPEC_SHA256:?submit with frozen SPEC_SHA256}"
DATA="${ROOT}/data/stablewm/derived"
PUSHT_CAL="${DATA}/scorer-audits/pusht-v1/p2-null-control-calibration-job-294843"
PUSHT_GRID="${DATA}/closed-loop-development/pusht-v1/augmented-grid-job-294846"
PUSHT_SEL="${DATA}/closed-loop-development/pusht-v1/augmented-selection-job-294847"
TWOROOM_CAL="${DATA}/scorer-audits/tworoom-v1/p2-null-control-calibration-job-296059"
TWOROOM_GRID="${DATA}/closed-loop-development/tworoom-v1/augmented-grid-job-296070"
TWOROOM_SEL="${DATA}/closed-loop-development/tworoom-v1/augmented-selection-job-296071"
OUTPUT_DIR="${DATA}/scorer-audits/cross-environment/m2-intervention-audit-job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-m2-intervention-audit-${SLURM_JOB_ID}"

REQUIRED=("${IMAGE}" "${SCRIPT}" "${RUNNER}" "${SPEC}" "${ONLINE}"
  "${PUSHT_CAL}/manifest.json" "${PUSHT_CAL}/audit-and-calibrators.h5"
  "${PUSHT_SEL}/manifest.json" "${PUSHT_SEL}/selection.h5"
  "${TWOROOM_CAL}/manifest.json" "${TWOROOM_CAL}/audit-and-calibrators.h5"
  "${TWOROOM_SEL}/manifest.json" "${TWOROOM_SEL}/selection.h5")
for required in "${REQUIRED[@]}"; do
  if [[ ! -s "${required}" ]]; then echo "Missing or empty input: ${required}" >&2; exit 2; fi
done
echo "${SPEC_SHA256}  ${SPEC}" | sha256sum -c - >/dev/null
if [[ -e "${OUTPUT_DIR}" ]]; then echo "Refusing to overwrite: ${OUTPUT_DIR}" >&2; exit 2; fi
mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT

{
  echo "classification=m2_p2_calibration_and_intervention_audit"
  echo "job_id=${SLURM_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${SPEC}" "${ONLINE}" \
    "${PUSHT_CAL}/manifest.json" "${PUSHT_CAL}/audit-and-calibrators.h5" \
    "${PUSHT_SEL}/manifest.json" "${PUSHT_SEL}/selection.h5" \
    "${TWOROOM_CAL}/manifest.json" "${TWOROOM_CAL}/audit-and-calibrators.h5" \
    "${TWOROOM_SEL}/manifest.json" "${TWOROOM_SEL}/selection.h5"
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONHASHSEED=20260812
    export TMPDIR="'"${JOB_TMP}"'"
    python "'"${SCRIPT}"'" \
      --pusht-calibration-dir "'"${PUSHT_CAL}"'" \
      --pusht-grid-root "'"${PUSHT_GRID}"'" \
      --pusht-selection-dir "'"${PUSHT_SEL}"'" \
      --tworoom-calibration-dir "'"${TWOROOM_CAL}"'" \
      --tworoom-grid-root "'"${TWOROOM_GRID}"'" \
      --tworoom-selection-dir "'"${TWOROOM_SEL}"'" \
      --online-implementation "'"${ONLINE}"'" \
      --spec "'"${SPEC}"'" \
      --output-json "'"${OUTPUT_DIR}"'/manifest.json"
  '

test -s "${OUTPUT_DIR}/manifest.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 | sort -z | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
