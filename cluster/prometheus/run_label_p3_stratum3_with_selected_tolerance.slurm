#!/usr/bin/env bash

# Apply the immutable P2-selected tolerance to locked P3 outcomes.

#SBATCH --job-name=p3-label-stratum3
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/p3-label-stratum3-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/p3-label-stratum3-%j.err

set -euo pipefail
: "${FIXED_AGGREGATE_JOB_ID:?submit with FIXED_AGGREGATE_JOB_ID set to the P3 fixed-subgoal aggregate job}"

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
SCRIPT="${ROOT}/scripts/label_p2_stratum3_with_selected_tolerance.py"
RUNNER="${ROOT}/scripts/run_label_p3_stratum3_with_selected_tolerance.slurm"
LOCK="${ROOT}/protocol/P3-PRE-EXECUTION-LOCK-2026-08-09.md"
LOCK_SHA256="a9f5c93bea7562c9f83c97c74f1cbf6041772626f3abd4d20fcd236a0b385d35"
STABLEWM_HOME="${ROOT}/data/stablewm"
FIXED_DIR="${STABLEWM_HOME}/derived/candidate-executions/pusht-v1/p3-stratum3-aggregate-job-${FIXED_AGGREGATE_JOB_ID}"
REAL_DIR="${STABLEWM_HOME}/derived/candidate-executions/pusht-v1/p2-real-frame-aggregate-job-294668"
CANDIDATE_DIR="${STABLEWM_HOME}/derived/candidate-pools/pusht-v1/p3-stratum3-b0-d75-h2-job-294828"
OUTPUT_DIR="${STABLEWM_HOME}/derived/candidate-labels/pusht-v1/p3-stratum3-job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-p3-label-stratum3-${SLURM_JOB_ID}"

REQUIRED=(
  "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${LOCK}"
  "${FIXED_DIR}/aggregate.h5" "${FIXED_DIR}/manifest.json" "${FIXED_DIR}/checksums.sha256"
  "${REAL_DIR}/aggregate.h5" "${REAL_DIR}/manifest.json" "${REAL_DIR}/checksums.sha256"
  "${CANDIDATE_DIR}/candidate-pools.h5" "${CANDIDATE_DIR}/manifest.json" "${CANDIDATE_DIR}/checksums.sha256"
)
for required in "${REQUIRED[@]}"; do
  if [[ ! -s "${required}" ]]; then echo "Missing or empty required input: ${required}" >&2; exit 2; fi
done
echo "${LOCK_SHA256}  ${LOCK}" | sha256sum -c - >/dev/null
(cd "${FIXED_DIR}" && sha256sum -c checksums.sha256 >/dev/null)
(cd "${REAL_DIR}" && sha256sum -c checksums.sha256 >/dev/null)
(cd "${CANDIDATE_DIR}" && sha256sum -c checksums.sha256 >/dev/null)
if [[ -e "${OUTPUT_DIR}" ]]; then echo "Refusing to overwrite P3 labels: ${OUTPUT_DIR}" >&2; exit 2; fi
mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT

{
  echo "classification=p3_stratum3_labeled_candidate_audit"
  echo "fixed_aggregate_job_id=${FIXED_AGGREGATE_JOB_ID}"
  echo "real_aggregate_job_id=294668"
  echo "job_id=${SLURM_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${LOCK}" \
    "${FIXED_DIR}/aggregate.h5" "${FIXED_DIR}/manifest.json" \
    "${REAL_DIR}/aggregate.h5" "${REAL_DIR}/manifest.json" \
    "${CANDIDATE_DIR}/candidate-pools.h5" "${CANDIDATE_DIR}/manifest.json"
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONHASHSEED=20260728
    export TMPDIR="'"${JOB_TMP}"'"
    python "'"${SCRIPT}"'" \
      --partition P3 \
      --fixed-aggregate-dir "'"${FIXED_DIR}"'" \
      --real-aggregate-dir "'"${REAL_DIR}"'" \
      --candidate-h5 "'"${CANDIDATE_DIR}"'/candidate-pools.h5" \
      --candidate-manifest "'"${CANDIDATE_DIR}"'/manifest.json" \
      --output-h5 "'"${OUTPUT_DIR}"'/labeled-candidates.h5" \
      --output-json "'"${OUTPUT_DIR}"'/manifest.json"
  '

test -s "${OUTPUT_DIR}/labeled-candidates.h5"; test -s "${OUTPUT_DIR}/manifest.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 | sort -z | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
