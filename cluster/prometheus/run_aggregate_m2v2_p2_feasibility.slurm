#!/usr/bin/env bash

# CPU aggregation of the frozen M2v2 P2 evidence.

#SBATCH --job-name=m2v2-p2-decision
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/m2v2-p2-decision-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/m2v2-p2-decision-%j.err

set -euo pipefail
ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
SCRIPT="${ROOT}/scripts/aggregate_m2v2_p2_feasibility.py"
RUNNER="${ROOT}/scripts/run_aggregate_m2v2_p2_feasibility.slurm"
SPEC="${ROOT}/protocol/M2V2-P1-P2-FEASIBILITY-SPEC-2026-08-12.md"
STABLEWM_HOME="${ROOT}/data/stablewm"
: "${SPEC_SHA256:?submit with frozen SPEC_SHA256}"
: "${GRID_JOB_ID:?submit with completed M2v2 grid job ID}"
: "${OFFLINE_JOB_ID:?submit with completed M2v2 offline job ID}"

PUSHT_OFFLINE="${STABLEWM_HOME}/derived/scorer-audits/pusht-v1/m2v2-p2-offline-job-${OFFLINE_JOB_ID}"
TWOROOM_OFFLINE="${STABLEWM_HOME}/derived/scorer-audits/tworoom-v1/m2v2-p2-offline-job-${OFFLINE_JOB_ID}"
PUSHT_B0="${STABLEWM_HOME}/derived/closed-loop-development/pusht-v1/b0-b1-d75-grid-job-294793"
TWOROOM_OLD_M2="${STABLEWM_HOME}/derived/closed-loop-development/tworoom-v1/augmented-grid-job-296070"
PUSHT_CONTEXT="${STABLEWM_HOME}/derived/closed-loop-development/pusht-v1/augmented-selection-job-294847/manifest.json"
TWOROOM_CONTEXT="${STABLEWM_HOME}/derived/closed-loop-development/tworoom-v1/augmented-selection-job-296071/manifest.json"
OUTPUT_DIR="${STABLEWM_HOME}/derived/closed-loop-development/cross-environment/m2v2-p2-decision-job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-m2v2-p2-decision-${SLURM_JOB_ID}"

for required in "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${SPEC}" \
  "${PUSHT_OFFLINE}/audit.h5" "${PUSHT_OFFLINE}/manifest.json" \
  "${TWOROOM_OFFLINE}/audit.h5" "${TWOROOM_OFFLINE}/manifest.json" \
  "${PUSHT_CONTEXT}" "${TWOROOM_CONTEXT}"; do
  if [[ ! -s "${required}" ]]; then echo "Missing M2v2 decision input: ${required}" >&2; exit 2; fi
done
echo "${SPEC_SHA256}  ${SPEC}" | sha256sum -c - >/dev/null
if [[ -e "${OUTPUT_DIR}" ]]; then echo "Refusing to overwrite M2v2 decision output" >&2; exit 2; fi
mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT
{
  echo "classification=m2v2_p2_prefrozen_feasibility_decision"
  echo "partition=P1/P2-development-only"
  echo "job_id=${SLURM_JOB_ID}"
  echo "grid_job_id=${GRID_JOB_ID}"
  echo "offline_job_id=${OFFLINE_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${SPEC}" \
    "${PUSHT_OFFLINE}/manifest.json" "${TWOROOM_OFFLINE}/manifest.json" \
    "${PUSHT_CONTEXT}" "${TWOROOM_CONTEXT}"
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONPATH="'"${ROOT}"'/scripts"
    export PYTHONHASHSEED=20260812
    export TMPDIR="'"${JOB_TMP}"'"
    python "'"${SCRIPT}"'" --grid-job-id "'"${GRID_JOB_ID}"'" \
      --stablewm-home "'"${STABLEWM_HOME}"'" \
      --pusht-offline-dir "'"${PUSHT_OFFLINE}"'" --tworoom-offline-dir "'"${TWOROOM_OFFLINE}"'" \
      --pusht-b0-root "'"${PUSHT_B0}"'" --tworoom-old-m2-root "'"${TWOROOM_OLD_M2}"'" \
      --pusht-context-manifest "'"${PUSHT_CONTEXT}"'" \
      --tworoom-context-manifest "'"${TWOROOM_CONTEXT}"'" \
      --spec "'"${SPEC}"'" --output-dir "'"${OUTPUT_DIR}"'"
  '

test -s "${OUTPUT_DIR}/manifest.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 | sort -z | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
