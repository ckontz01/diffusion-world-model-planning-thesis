#!/usr/bin/env bash

# Mechanical, outcome-gated continuation of the frozen TwoRoom P2 pipeline.

#SBATCH --job-name=tworoom-p2-dispatch
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:10:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-p2-dispatch-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-p2-dispatch-%j.err

set -euo pipefail
: "${PIPELINE_STAGE:?submit with PIPELINE_STAGE set to a frozen dispatcher stage}"
: "${TRUE_SCORE_JOB_ID:?submit with TRUE_SCORE_JOB_ID set to 295869}"

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
SCRIPT="${ROOT}/scripts/dispatch_tworoom_p2_pipeline_a085.py"
RUNNER="${ROOT}/scripts/run_dispatch_tworoom_p2_pipeline_a085.slurm"
AMENDMENTS="${ROOT}/protocol/PROTOCOL-IMPLEMENTATION-AMENDMENTS-2026-08-08.md"
OUTPUT_DIR="${ROOT}/data/stablewm/repro/tworoom-p2-pipeline-dispatch/${PIPELINE_STAGE}-scheduler-job-${SLURM_JOB_ID}"
EXPECTED_SCRIPT_SHA256="260789c6a22d8259450b00f89937d2cde8adef3cdbd5d3bae0dba0da04300d21"

for required in "${SCRIPT}" "${RUNNER}" "${AMENDMENTS}"; do
  if [[ ! -s "${required}" ]]; then
    echo "Missing TwoRoom P2 dispatcher input: ${required}" >&2
    exit 2
  fi
done
printf '%s  %s\n' "${EXPECTED_SCRIPT_SHA256}" "${SCRIPT}" | sha256sum -c -
if [[ "${TRUE_SCORE_JOB_ID}" != "295869" ]]; then
  echo "Unexpected true-score selection job ID: ${TRUE_SCORE_JOB_ID}" >&2
  exit 2
fi
if [[ -e "${OUTPUT_DIR}" ]]; then
  echo "Refusing duplicate TwoRoom P2 dispatch stage: ${OUTPUT_DIR}" >&2
  exit 2
fi

ARGS=(
  --stage "${PIPELINE_STAGE}"
  --true-score-job-id "${TRUE_SCORE_JOB_ID}"
  --output-json "${OUTPUT_DIR}/dispatch.json"
)
case "${PIPELINE_STAGE}" in
  after-selection)
    ;;
  after-calibration)
    : "${CALIBRATION_JOB_ID:?after-calibration requires CALIBRATION_JOB_ID}"
    ARGS+=(--calibration-job-id "${CALIBRATION_JOB_ID}")
    ;;
  after-smoke)
    : "${CALIBRATION_JOB_ID:?after-smoke requires CALIBRATION_JOB_ID}"
    : "${SMOKE_JOB_ID:?after-smoke requires SMOKE_JOB_ID}"
    ARGS+=(--calibration-job-id "${CALIBRATION_JOB_ID}" --smoke-job-id "${SMOKE_JOB_ID}")
    ;;
  after-aggregate)
    : "${CALIBRATION_JOB_ID:?after-aggregate requires CALIBRATION_JOB_ID}"
    : "${SMOKE_JOB_ID:?after-aggregate requires SMOKE_JOB_ID}"
    : "${GRID_JOB_ID:?after-aggregate requires GRID_JOB_ID}"
    : "${AGGREGATE_JOB_ID:?after-aggregate requires AGGREGATE_JOB_ID}"
    ARGS+=(
      --calibration-job-id "${CALIBRATION_JOB_ID}"
      --smoke-job-id "${SMOKE_JOB_ID}"
      --grid-job-id "${GRID_JOB_ID}"
      --aggregate-job-id "${AGGREGATE_JOB_ID}"
    )
    ;;
  *)
    echo "Unsupported TwoRoom P2 pipeline stage: ${PIPELINE_STAGE}" >&2
    exit 2
    ;;
esac

mkdir -p "${OUTPUT_DIR}"
{
  echo "classification=tworoom_p2_pipeline_dispatch_${PIPELINE_STAGE}"
  echo "scheduler_job_id=${SLURM_JOB_ID}"
  echo "true_score_job_id=${TRUE_SCORE_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${SCRIPT}" "${RUNNER}" "${AMENDMENTS}"
} > "${OUTPUT_DIR}/provenance.txt"

/usr/bin/python3 "${SCRIPT}" "${ARGS[@]}"

test -s "${OUTPUT_DIR}/dispatch.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 \
  | sort -z \
  | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
