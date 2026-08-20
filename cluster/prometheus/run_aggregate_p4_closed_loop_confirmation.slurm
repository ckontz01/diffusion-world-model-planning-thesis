#!/usr/bin/env bash

# Submit only after the P4 B0/B1 array and every promoted learned-arm array
# finish successfully. Required exports:
#   PROMOTION_JOB_ID=<P3 scorer-audit job>
#   BASELINE_ARRAY_JOB_ID=<P4 B0/B1 array job>
# Optional exports, supplied only for arms promoted by the P3 audit:
#   M1_ARRAY_JOB_ID=<P4 M1 array job>
#   M2_ARRAY_JOB_ID=<P4 M2 array job>
#   M3_ARRAY_JOB_ID=<P4 M3 array job>

#SBATCH --job-name=p4-confirm-agg
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/p4-confirm-agg-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/p4-confirm-agg-%j.err

set -euo pipefail
: "${PROMOTION_JOB_ID:?submit with PROMOTION_JOB_ID set to the locked P3 scorer-audit job}"
: "${BASELINE_ARRAY_JOB_ID:?submit with BASELINE_ARRAY_JOB_ID set to the P4 B0/B1 array job}"

for value_name in PROMOTION_JOB_ID BASELINE_ARRAY_JOB_ID; do
  value="${!value_name}"
  if [[ ! "${value}" =~ ^[0-9]+$ ]]; then
    echo "${value_name} must be an integer job ID; got ${value}" >&2
    exit 2
  fi
done
for value_name in M1_ARRAY_JOB_ID M2_ARRAY_JOB_ID M3_ARRAY_JOB_ID; do
  value="${!value_name:-}"
  if [[ -n "${value}" && ! "${value}" =~ ^[0-9]+$ ]]; then
    echo "${value_name} must be an integer job ID when supplied; got ${value}" >&2
    exit 2
  fi
done

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
SCRIPT="${ROOT}/scripts/aggregate_p4_closed_loop_confirmation.py"
RUNNER="${ROOT}/scripts/run_aggregate_p4_closed_loop_confirmation.slurm"
STABLEWM_HOME="${ROOT}/data/stablewm"
QUERY_DIR="${STABLEWM_HOME}/derived/closed-loop-confirmation/pusht-v1/p4-query-artifact-job-295120"
PROMOTION_DIR="${STABLEWM_HOME}/derived/scorer-audits/pusht-v1/p3-locked-audit-job-${PROMOTION_JOB_ID}"
BASELINE_ROOT="${STABLEWM_HOME}/derived/closed-loop-confirmation/pusht-v1/b0-b1-d75-job-${BASELINE_ARRAY_JOB_ID}"
OUTPUT_DIR="${STABLEWM_HOME}/derived/closed-loop-confirmation/pusht-v1/aggregate-job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-p4-confirm-agg-${SLURM_JOB_ID}"

for required in "${IMAGE}" "${SCRIPT}" "${RUNNER}" \
  "${QUERY_DIR}/queries.h5" "${QUERY_DIR}/manifest.json" "${QUERY_DIR}/checksums.sha256" \
  "${PROMOTION_DIR}/audit.h5" "${PROMOTION_DIR}/manifest.json" "${PROMOTION_DIR}/checksums.sha256"; do
  if [[ ! -s "${required}" ]]; then
    echo "Missing or empty required input: ${required}" >&2
    exit 2
  fi
done
if [[ ! -d "${BASELINE_ROOT}" ]]; then
  echo "Missing P4 baseline root: ${BASELINE_ROOT}" >&2
  exit 2
fi
(cd "${QUERY_DIR}" && sha256sum -c checksums.sha256 >/dev/null)
(cd "${PROMOTION_DIR}" && sha256sum -c checksums.sha256 >/dev/null)
if [[ -e "${OUTPUT_DIR}" ]]; then
  echo "Refusing to overwrite P4 aggregate: ${OUTPUT_DIR}" >&2
  exit 2
fi
mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT

ARGUMENTS=(
  "${SCRIPT}"
  --query-dir "${QUERY_DIR}"
  --promotion-dir "${PROMOTION_DIR}"
  --baseline-root "${BASELINE_ROOT}"
  --output-h5 "${OUTPUT_DIR}/confirmation.h5"
  --output-json "${OUTPUT_DIR}/manifest.json"
)
for method in M1 M2 M3; do
  value_name="${method}_ARRAY_JOB_ID"
  array_job_id="${!value_name:-}"
  if [[ -n "${array_job_id}" ]]; then
    method_lower="${method,,}"
    learned_root="${STABLEWM_HOME}/derived/closed-loop-confirmation/pusht-v1/augmented-${method}-job-${array_job_id}"
    if [[ ! -d "${learned_root}" ]]; then
      echo "Missing P4 ${method} root: ${learned_root}" >&2
      exit 2
    fi
    ARGUMENTS+=("--${method_lower}-root" "${learned_root}")
  fi
done

{
  echo "classification=p4_closed_loop_confirmation_aggregate"
  echo "job_id=${SLURM_JOB_ID}"
  echo "promotion_job_id=${PROMOTION_JOB_ID}"
  echo "baseline_array_job_id=${BASELINE_ARRAY_JOB_ID}"
  echo "m1_array_job_id=${M1_ARRAY_JOB_ID:-not_submitted}"
  echo "m2_array_job_id=${M2_ARRAY_JOB_ID:-not_submitted}"
  echo "m3_array_job_id=${M3_ARRAY_JOB_ID:-not_submitted}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "${SCRIPT}" "${RUNNER}" \
    "${QUERY_DIR}/queries.h5" "${QUERY_DIR}/manifest.json" \
    "${PROMOTION_DIR}/audit.h5" "${PROMOTION_DIR}/manifest.json"
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
    exec python "$@"
  ' bash "${ARGUMENTS[@]}"

test -s "${OUTPUT_DIR}/confirmation.h5"
test -s "${OUTPUT_DIR}/manifest.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 \
  | sort -z \
  | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
